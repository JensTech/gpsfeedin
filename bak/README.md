# gpsfeedin

Fake GPS feed for SeaClear (or any NMEA nav app)
fed in through a serial pipe.

## Files

- `nmea_utils.py` — checksum + GPRMC/GPGGA builders
- `server.py` — the server: opens the serial target, streams sentences at
  1Hz*, listens on a local socket (127.0.0.1:5005) for live updates
- `cli.py` — CLI interface that sends a new position to a running server
- `gpsgui.py` — standalone PySimpleGUI version of the cli

## pip prerequisites

```
pip install pyserial pywin32
pip install PySimpleGUI     # optional, only needed if you want the gui
```

## VMware setup
If you want to pipe the serial into a vmware virtual machine,
vmware already supports this natively

Add a serial port to the VM guest:
- Type: Output to named pipe
- Pipe name: `\\.\pipe\gps1`
- This end is the: server
- The other end is: an application

In a VM, this shows up as a normal COM port (check Device Manager). Point
your app's GPS settings at that COM port, baud **4800**, and select
NMEA/GPRMC as the sentence type.

## CLI usage

Start the server:

```
python server.py -s --port \\.\pipe\gps1
> Starting server on \\.\pipe\gps1
> Server started
    > Press [Ctrl] + [C] or [Q] + Enter to quit
```

From another terminal, push a new position any time:

```
python cli.py --lat 05N 01.234 --lon 30E 07.654
Updated -> 05N01.234 030E07.654
```

Format is `DD H MM.MMMM` — degrees, hemisphere letter, decimal minutes —
same layout NMEA itself uses, no decimal-degree conversion needed.

## GUI usage

```
python gpsgui.py --port \\.\pipe\gps1
```

Type degrees + minutes into the boxes, hit Apply.

## Get it as an EXE
Exe's will soon be downloadable from the releases tab, but to build your own,
we can just use plain and standard pyinstaller
```
pip install pyinstaller
pyinstaller --onefile --name gpsfeedin gps_server.py
pyinstaller --onefile --name gpscli gps_cli.py
pyinstaller --onefile --name gpsgui --windowed gps_gui.py
```

## Notes

- COM ports work too: pass `--port COM5` instead of a pipe path, same on
  both server and GUI.
- Sentence rate is fixed at 1Hz to match real GPS antennas; change the
  `stop_event.wait(1.0)` in `feed_loop` if you want faster/slower ticks.
- The control socket is unauthenticated localhost-only, don't open it up out
  of localhost or outside of your lan.