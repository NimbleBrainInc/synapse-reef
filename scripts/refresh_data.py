"""Refresh data/stations.json from NDBC's activestations.xml.

Fetches the canonical XML, parses, and writes the full station catalog
(~1,350 stations) to data/stations.json. Also flags camera-equipped
stations from buoycams.php. Run periodically (weekly is fine — the
catalog changes slowly).

Usage:
    uv run python scripts/refresh_data.py

Network: hits https://www.ndbc.noaa.gov/activestations.xml and
         https://www.ndbc.noaa.gov/buoycams.php only.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import httpx

ACTIVE_STATIONS_URL = "https://www.ndbc.noaa.gov/activestations.xml"
BUOYCAMS_URL = "https://www.ndbc.noaa.gov/buoycams.php"
USER_AGENT = "synapse-reef-refresh/0.1"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _fetch_camera_station_ids() -> set[str]:
    """Return the set of station IDs with cameras (from buoycams.php JSON)."""
    r = httpx.get(BUOYCAMS_URL, headers={"User-Agent": USER_AGENT}, timeout=15.0)
    r.raise_for_status()
    return {entry["id"] for entry in r.json() if entry.get("id")}


def _parse_stations(xml_text: str, camera_ids: set[str]) -> list[dict]:
    root = ET.fromstring(xml_text)
    stations = []
    for s in root.findall("station"):
        sid = s.get("id")
        if not sid:
            continue
        try:
            lat = float(s.get("lat", ""))
            lng = float(s.get("lon", ""))
        except ValueError:
            continue
        stations.append(
            {
                "id": sid,
                "name": s.get("name", "").strip(),
                "lat": lat,
                "lng": lng,
                "owner": (s.get("owner") or "").strip() or None,
                "pgm": (s.get("pgm") or "").strip() or None,
                "type": (s.get("type") or "").strip() or None,
                "has_met": s.get("met", "n").lower() == "y",
                "has_currents": s.get("currents", "n").lower() == "y",
                "has_water_quality": s.get("waterquality", "n").lower() == "y",
                "has_dart": s.get("dart", "n").lower() == "y",
                "has_camera": sid in camera_ids,
            }
        )
    return stations


def main() -> int:
    print(f"Fetching {ACTIVE_STATIONS_URL} …", file=sys.stderr)
    r = httpx.get(ACTIVE_STATIONS_URL, headers={"User-Agent": USER_AGENT}, timeout=30.0)
    r.raise_for_status()
    r.encoding = "iso-8859-1"

    print(f"Fetching {BUOYCAMS_URL} …", file=sys.stderr)
    camera_ids = _fetch_camera_station_ids()
    print(f"  {len(camera_ids)} cam-equipped stations", file=sys.stderr)

    stations = _parse_stations(r.text, camera_ids)
    print(f"Parsed {len(stations)} stations", file=sys.stderr)

    out = DATA_DIR / "stations.json"
    payload = {
        "_comment": (
            "Snapshot of NDBC active stations from "
            "https://www.ndbc.noaa.gov/activestations.xml — "
            "refresh via scripts/refresh_data.py."
        ),
        "snapshot_at": datetime.now(UTC).isoformat(),
        "stations": stations,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out} ({len(stations)} stations)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
