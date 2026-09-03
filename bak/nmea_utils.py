# This script converts co-ordinates to NMEA codes

# NMEA 0183 sentence helpers: checksum + GGA/RMC builders.
from datetime import datetime, timezone


def checksum(sentence_body: str) -> str:
    # XOR checksum of everything between '$' and '*' (exclusive).
    cs = 0
    for c in sentence_body:
        cs ^= ord(c)
    return f"{cs:02X}"


def build_sentence(body: str) -> str:
    return f"${body}*{checksum(body)}\r\n"


def fmt_lat(deg: int, minutes: float, hemi: str) -> str:
    # NMEA wants DDMM.MMMM
    return f"{deg:02d}{minutes:07.4f},{hemi}"


def fmt_lon(deg: int, minutes: float, hemi: str) -> str:
    # NMEA wants DDDMM.MMMM
    return f"{deg:03d}{minutes:07.4f},{hemi}"


def gprmc(deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon,
          speed_kts=0.0, course_deg=0.0, now=None) -> str:
    now = now or datetime.now(timezone.utc)
    t = now.strftime("%H%M%S")
    d = now.strftime("%d%m%y")
    lat = fmt_lat(deg_lat, min_lat, hemi_lat)
    lon = fmt_lon(deg_lon, min_lon, hemi_lon)
    body = f"GPRMC,{t},A,{lat},{lon},{speed_kts:05.1f},{course_deg:05.1f},{d},000.0,W"
    return build_sentence(body)


def gpgga(deg_lat, min_lat, hemi_lat, deg_lon, min_lon, hemi_lon,
          num_sats=8, hdop=0.9, altitude_m=10.0, now=None) -> str:
    now = now or datetime.now(timezone.utc)
    t = now.strftime("%H%M%S")
    lat = fmt_lat(deg_lat, min_lat, hemi_lat)
    lon = fmt_lon(deg_lon, min_lon, hemi_lon)
    body = (f"GPGGA,{t},{lat},{lon},1,{num_sats:02d},{hdop:.1f},"
            f"{altitude_m:.1f},M,0.0,M,,")
    return build_sentence(body)
