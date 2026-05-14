"""Station catalog — loaded from a bundled snapshot of activestations.xml.

Stations are kept in memory; lookup-by-id is a dict, find-nearby is a linear
scan with haversine distance. ~1,300 stations × O(1) per scan = sub-ms.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Earth's mean radius in nautical miles (1 nm = 1852 m)
_EARTH_RADIUS_NM = 3440.065


@dataclass
class Station:
    id: str
    name: str
    lat: float
    lng: float
    owner: str | None = None
    pgm: str | None = None
    type: str | None = None
    has_met: bool = False
    has_currents: bool = False
    has_water_quality: bool = False
    has_dart: bool = False
    has_camera: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "owner": self.owner,
            "type": self.type,
            "capabilities": [
                cap
                for cap, has in (
                    ("met", self.has_met),
                    ("currents", self.has_currents),
                    ("water_quality", self.has_water_quality),
                    ("dart", self.has_dart),
                    ("camera", self.has_camera),
                )
                if has
            ],
        }


@dataclass
class StationMatch:
    station: Station
    distance_nm: float

    def to_dict(self) -> dict:
        return {**self.station.to_dict(), "distance_nm": round(self.distance_nm, 1)}


def haversine_nm(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two coordinates in nautical miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_NM * math.asin(math.sqrt(a))


@dataclass
class StationCatalog:
    stations: list[Station]
    _by_id: dict[str, Station] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._by_id = {s.id.upper(): s for s in self.stations}

    @classmethod
    def load(cls, path: Path | None = None) -> StationCatalog:
        path = path or (_DATA_DIR / "stations.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        stations = [Station(**s) for s in raw["stations"]]
        return cls(stations=stations)

    def get(self, station_id: str) -> Station | None:
        return self._by_id.get(station_id.upper())

    def find_nearby(
        self,
        lat: float,
        lng: float,
        radius_nm: float = 50.0,
        capabilities: list[str] | None = None,
    ) -> list[StationMatch]:
        cap_set = set(capabilities or [])
        matches: list[StationMatch] = []
        for s in self.stations:
            if cap_set:
                station_caps = {
                    "met": s.has_met,
                    "currents": s.has_currents,
                    "water_quality": s.has_water_quality,
                    "dart": s.has_dart,
                    "camera": s.has_camera,
                }
                if not any(station_caps.get(c, False) for c in cap_set):
                    continue
            d = haversine_nm(lat, lng, s.lat, s.lng)
            if d <= radius_nm:
                matches.append(StationMatch(station=s, distance_nm=d))
        matches.sort(key=lambda m: m.distance_nm)
        return matches
