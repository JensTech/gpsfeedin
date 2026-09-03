r"""
GPSFeedin, a fake GPS feeder for serial apps.

Usage:
    python server.py -s --port \\.\pipe\gps1
    python server.py -s --port COM5

"""
import argparse
import json
import socket
import sys
import threading
import time

import nmea_utils as nmea

CTRL_HOST = "127.0.0.1"
DEFAULT_CTRL_PORT = 5005


def open_target(port_path: str):
    if port_path.startswith(r"\\.\pipe"):
        try:
            import win32file
            import win32pipe
            import win32security
            import pywintypes
        except ImportError:
            sys.exit("Named pipe targets need pywin32: pip install pywin32")

        sa = pywintypes.SECURITY_ATTRIBUTES()
        sd = win32security.SECURITY_DESCRIPTOR()
        sd.Initialize()
        sd.SetSecurityDescriptorDacl(1, None, 0)  # type: ignore | Full access permissions
        sa.SECURITY_DESCRIPTOR = sd
        sa.bInheritHandle = True

        handle = win32pipe.CreateNamedPipe(
            port_path,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT,
            1,
            4096,
            4096,
            0,
            sa,
        )

        print(f"Waiting for connection to {port_path}...")
        win32pipe.ConnectNamedPipe(handle, None)
        print("Pipe connected.")

        class PipeWriter:
            def write(self, data):
                win32file.WriteFile(handle, data)

            def close(self):
                win32file.CloseHandle(handle)

        return PipeWriter()
    else:
        import serial
        return serial.Serial(port_path, baudrate=4800, timeout=1)

class GpsState:

    def __init__(self, deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon):
        self.lock = threading.Lock()
        self.deg_lat, self.min_lat, self.hemi_lat = deg_lat, min_lat, hemi_lat
        self.deg_lon, self.min_lon, self.hemi_lon = deg_lon, min_lon, hemi_lon

    def update(self, deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon):
        with self.lock:
            self.deg_lat, self.min_lat, self.hemi_lat = deg_lat, min_lat, hemi_lat
            self.deg_lon, self.min_lon, self.hemi_lon = deg_lon, min_lon, hemi_lon

    def snapshot(self):
        with self.lock:
            return (self.deg_lat, self.min_lat, self.hemi_lat,
                    self.deg_lon, self.min_lon, self.hemi_lon)


def feed_loop(target, state: GpsState, stop_event: threading.Event):
    while not stop_event.is_set():
        deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon = state.snapshot()
        rmc = nmea.gprmc(deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon)
        gga = nmea.gpgga(deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon)
        try:
            target.write(rmc.encode("ascii"))
            target.write(gga.encode("ascii"))
        except Exception as e:
            print(f"[!] write error: {e}", file=sys.stderr)
        stop_event.wait(1.0)


def control_loop(state: GpsState, stop_event: threading.Event, ctrl_port: int):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((CTRL_HOST, ctrl_port))
    srv.listen(1)
    srv.settimeout(0.5)

    while not stop_event.is_set():
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue

        with conn:
            data = conn.recv(4096)
            if not data:
                continue

            try:
                msg = json.loads(data.decode("utf-8"))

                state.update(
                    msg["deg_lat"],
                    msg["min_lat"],
                    msg["hemi_lat"],
                    msg["deg_lon"],
                    msg["min_lon"],
                    msg["hemi_lon"],
                )

                conn.sendall(b"OK")

                print(
                    f"[+] position updated: "
                    f"{msg['deg_lat']:02d}° {msg['min_lat']:07.4f}{msg['hemi_lat']} "
                    f"{msg['deg_lon']:03d}° {msg['min_lon']:07.4f}{msg['hemi_lon']}"
                )

            except Exception as e:
                conn.sendall(f"ERR {e}".encode("utf-8"))

    srv.close()



def wait_for_quit(stop_event: threading.Event):
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if line.strip().lower() == "q":
            stop_event.set()
            return


def main():
    ap = argparse.ArgumentParser(prog="gpsfeedin")
    ap.add_argument("-s", "--serve", action="store_true", required=True,
                     help="run the feed server")
    ap.add_argument("--port", required=True,
                     help=r"serial target, e.g. COM5 or \\.\pipe\gps1")
    ap.add_argument("--ctrl-port", type=int, default=DEFAULT_CTRL_PORT,
                     help="local control socket port for gpsgui (default 5005)")
    ap.add_argument("--lat", default="50N 00.000",
                     help="initial lat, e.g. '05N 01.234'")
    ap.add_argument("--lon", default="000E 00.000",
                     help="initial lon, e.g. '30E 07.654'")
    args = ap.parse_args()

    from cli import parse_lat, parse_lon

    deg_lat, min_lat, hemi_lat = parse_lat(args.lat)
    deg_lon, min_lon, hemi_lon = parse_lon(args.lon)

    state = GpsState(
        deg_lat, min_lat, hemi_lat,
        deg_lon, min_lon, hemi_lon
    )

    print(f"Starting server on {args.port}")

    stop_event = threading.Event()

    # Start the control socket.
    ctrl_t = threading.Thread(
        target=control_loop,
        args=(state, stop_event, args.ctrl_port),
        daemon=True
    )
    ctrl_t.start()

    # Open the GPS target in a background thread
    target_holder = {}

    def open_target_thread():
        try:
            target_holder["target"] = open_target(args.port)
            print("GPS target connected.")

            feed_t = threading.Thread(
                target=feed_loop,
                args=(target_holder["target"], state, stop_event),
                daemon=True
            )
            feed_t.start()
            target_holder["feed"] = feed_t

        except Exception as e:
            print(f"[!] Failed to open GPS target: {e}", file=sys.stderr)
            stop_event.set()

    target_t = threading.Thread(
        target=open_target_thread,
        daemon=True
    )
    target_t.start()

    print(f"Control server listening on 127.0.0.1:{args.ctrl_port}")
    print("    > Press [Ctrl] + [C] or [Q] + Enter to quit")

    quit_t = threading.Thread(
        target=wait_for_quit,
        args=(stop_event,),
        daemon=True
    )
    quit_t.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()

        target = target_holder.get("target")
        if target is not None:
            try:
                target.close()
            except Exception:
                pass

        print("\nServer stopped.")

if __name__ == "__main__":
    main()
