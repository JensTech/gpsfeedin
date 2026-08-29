"""
gpsgui.py, GUI for the spoofed GPS feed.

Fields: [deg]°N [minutes.mmmm]  /  [deg]°E [minutes.mmmm]
Editing a field updates the position at 1Hz to whatever serial target you launched it with.

Run the script and connect it to the serial port:
    python gpsgui.py --port \\.\pipe\gps1
"""
import argparse
import threading

import PySimpleGUI as sg

import gps_server as gs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help=r"COM5 or \\.\pipe\gps1")
    args = ap.parse_args()

    state = gs.GpsState(50, 0.0, "N", 0, 0.0, "E")
    stop_event = threading.Event()
    target = gs.open_target(args.port)
    feed_t = threading.Thread(target=gs.feed_loop, args=(target, state, stop_event), daemon=True)
    feed_t.start()

    sg.theme("SystemDefault")
    layout = [
        [sg.Text("Latitude")],
        [sg.Input("50", size=(4, 1), key="-LATDEG-"), sg.Text("°N"),
         sg.Input("00.0000", size=(10, 1), key="-LATMIN-")],
        [sg.Text("Longitude")],
        [sg.Input("00", size=(4, 1), key="-LONDEG-"), sg.Text("°E"),
         sg.Input("00.0000", size=(10, 1), key="-LONMIN-")],
        [sg.Combo(["N", "S"], default_value="N", key="-LATHEMI-"),
         sg.Combo(["E", "W"], default_value="E", key="-LONHEMI-")],
        [sg.Button("Apply"), sg.Button("Quit")],
        [sg.Text("Streaming to " + args.port, key="-STATUS-")],
    ]
    window = sg.Window("Fake GPS Feed", layout)

    while True:
        event, values = window.read(timeout=200)
        if event in (sg.WIN_CLOSED, "Quit"):
            break
        if event == "Apply":
            try:
                deg_lat = int(values["-LATDEG-"])
                min_lat = float(values["-LATMIN-"])
                deg_lon = int(values["-LONDEG-"])
                min_lon = float(values["-LONMIN-"])
                state.update(deg_lat, min_lat, values["-LATHEMI-"],
                             deg_lon, min_lon, values["-LONHEMI-"])
                window["-STATUS-"].update(f"Updated: {deg_lat}°{values['-LATHEMI-']} "
                                           f"{deg_lon}°{values['-LONHEMI-']}")
            except ValueError:
                window["-STATUS-"].update("Invalid number in a field")

    stop_event.set()
    target.close()
    window.close()


if __name__ == "__main__":
    main()
