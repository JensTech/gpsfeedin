"""

Example Usage:
    python cli.py --lat 05N 01.234 --lon 30E 07.654
    python cli.py --lat 05N 01.234 --lon 30E 07.654 --ctrl-port 5005
"""
import argparse
import json
import re
import socket
import sys

CTRL_HOST = "127.0.0.1"
DEFAULT_CTRL_PORT = 5005

_COORD_RE = re.compile(r"^\s*(\d{1,3})\s*([NSEWnsew])\s+(\d{1,2}\.\d+)\s*$")


def _parse(raw: str, valid_hemis: str):
    m = _COORD_RE.match(raw)
    if not m:
        raise ValueError(f"can't parse coordinate '{raw}', expected e.g. '05N 01.234'")
    deg, hemi, minutes = int(m.group(1)), m.group(2).upper(), float(m.group(3))
    if hemi not in valid_hemis:
        raise ValueError(f"expected hemisphere in {valid_hemis}, got '{hemi}'")
    return deg, minutes, hemi


def parse_lat(raw: str):
    return _parse(raw, "NS")


def parse_lon(raw: str):
    return _parse(raw, "EW")


def send_update(deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon, ctrl_port):
    msg = json.dumps({
        "deg_lat": deg_lat, "min_lat": min_lat, "hemi_lat": hemi_lat,
        "deg_lon": deg_lon, "min_lon": min_lon, "hemi_lon": hemi_lon,
    }).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        try:
            s.connect((CTRL_HOST, ctrl_port))
        except ConnectionRefusedError:
            sys.exit(f"No gpsfeedin server listening on port {ctrl_port} - is it running?")
        s.sendall(msg)
        reply = s.recv(4096).decode("utf-8")
        return reply


def main():
    ap = argparse.ArgumentParser(prog="gpscli")
    ap.add_argument("--lat", required=True, nargs="+", help="e.g. --lat 05N 01.234")
    ap.add_argument("--lon", required=True, nargs="+", help="e.g. --lon 30E 07.654")
    ap.add_argument("--ctrl-port", type=int, default=DEFAULT_CTRL_PORT)
    args = ap.parse_args()

    lat_raw = " ".join(args.lat)
    lon_raw = " ".join(args.lon)
    deg_lat, min_lat, hemi_lat = parse_lat(lat_raw)
    deg_lon, min_lon, hemi_lon = parse_lon(lon_raw)

    reply = send_update(deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon, args.ctrl_port)
    if reply.startswith("OK"):
        print(f"Updated -> {deg_lat:02d}{min_lat:.4f}{hemi_lat} {deg_lon:03d}{min_lon:.4f}{hemi_lon}")
    else:
        sys.exit(f"Server rejected update: {reply}")


if __name__ == "__main__":
    main()
