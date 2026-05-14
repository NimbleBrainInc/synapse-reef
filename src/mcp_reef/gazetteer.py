"""Place-name → coordinate lookup.

Backed by a hand-curated JSON file in ``data/gazetteer.json``. Lookup is
case-insensitive on both the canonical name and any aliases. Falls back to
substring match so "pipeline" matches "Banzai Pipeline".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class Place:
    name: str
    lat: float
    lng: float
    region: str | None = None
    aliases: list[str] = field(default_factory=list)


@dataclass
class Gazetteer:
    places: list[Place]
    _index: dict[str, Place] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        idx: dict[str, Place] = {}
        for p in self.places:
            idx[p.name.lower()] = p
            for alias in p.aliases:
                idx[alias.lower()] = p
        self._index = idx

    @classmethod
    def load(cls, path: Path | None = None) -> Gazetteer:
        path = path or (_DATA_DIR / "gazetteer.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        places = [Place(**p) for p in raw["places"]]
        return cls(places=places)

    def lookup(self, query: str) -> Place | None:
        q = query.strip().lower()
        if not q:
            return None
        if q in self._index:
            return self._index[q]
        # Substring fallback — favors exact matches first, but lets "pipeline"
        # find "Banzai Pipeline" and "half moon" find "Half Moon Bay".
        for key, place in self._index.items():
            if q in key:
                return place
        return None
