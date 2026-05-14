"""Reef MCP App — NOAA NDBC buoy data with rich UI.

Two model-callable tools (find_buoys, get_conditions) plus a single
ui:// resource. Designed to exercise the MCP Apps spec's server-side
metadata primitives: ToolAnnotations, AppConfig.resource_uri, AppConfig.csp,
AppConfig.domain, AppConfig.prefers_border.
"""

from __future__ import annotations

import sys
from typing import Any

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from mcp.types import ToolAnnotations

from .catalog import StationCatalog
from .gazetteer import Gazetteer
from .ndbc import fetch_realtime_stdmet
from .parsing import parse_realtime2_stdmet
from .ui import load_ui

mcp = FastMCP(
    "Reef",
    instructions=(
        "Live ocean and weather conditions from 1,300+ NOAA buoys worldwide. "
        "Use find_buoys to look up stations by place name (Pipeline, Half Moon Bay, "
        "Mavericks) or coordinates. Use get_conditions to fetch the latest wave, "
        "wind, and water readings — this renders an inline conditions card."
    ),
)

# Static reference data loaded once at startup.
_catalog = StationCatalog.load()
_gazetteer = Gazetteer.load()

_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    open_world_hint=True,
    idempotent_hint=True,
)


@mcp.tool(annotations=_READ_ONLY)
async def find_buoys(
    place: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    radius_nm: float = 50.0,
    capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Find NOAA buoys near a place name or coordinate.

    Provide either ``place`` (resolved via local gazetteer) or both
    ``lat``/``lng``. Filter by capabilities: "met" (weather), "currents",
    "water_quality", "dart" (tsunami), "camera".

    Args:
        place: Named place ("Pipeline", "Half Moon Bay", "Mavericks").
        lat: Latitude in decimal degrees (negative = south).
        lng: Longitude in decimal degrees (negative = west).
        radius_nm: Search radius in nautical miles. Default 50.
        capabilities: Filter to stations with these capabilities.
    """
    if place is not None:
        resolved = _gazetteer.lookup(place)
        if resolved is None:
            return {"error": f"Unknown place: {place!r}", "matches": []}
        lat, lng = resolved.lat, resolved.lng

    if lat is None or lng is None:
        return {
            "error": "Provide either `place` or both `lat` and `lng`.",
            "matches": [],
        }

    matches = _catalog.find_nearby(
        lat=lat, lng=lng, radius_nm=radius_nm, capabilities=capabilities
    )
    return {
        "search": {"lat": lat, "lng": lng, "radius_nm": radius_nm},
        "match_count": len(matches),
        "matches": [m.to_dict() for m in matches[:20]],
    }


@mcp.tool(
    annotations=_READ_ONLY,
    app=AppConfig(resource_uri="ui://reef/main"),
)
async def get_conditions(station_id: str) -> dict[str, Any]:
    """Get current ocean and weather conditions at a NOAA buoy.

    Returns wave height, swell period/direction, wind, water temp, and
    pressure from the latest observation. The result renders as an inline
    conditions card via the linked ui:// resource.

    Args:
        station_id: NDBC station ID (e.g. "46042", "41001", "SAUF1").
    """
    station = _catalog.get(station_id)
    if station is None:
        return {"error": f"Unknown station: {station_id!r}", "station_id": station_id}

    raw = await fetch_realtime_stdmet(station_id)
    if raw is None:
        return {
            "station": station.to_dict(),
            "observation": None,
            "error": "No recent observation available from NDBC.",
        }

    obs = parse_realtime2_stdmet(raw)
    return {"station": station.to_dict(), "observation": obs}


@mcp.resource(
    "ui://reef/main",
    app=AppConfig(
        csp=ResourceCSP(
            connect_domains=[
                "https://www.ndbc.noaa.gov",
                "https://coastwatch.pfeg.noaa.gov",
            ],
            resource_domains=["https://www.ndbc.noaa.gov"],
        ),
        domain="reef.nimblebrain.ai",
        prefers_border=False,
    ),
)
def reef_ui() -> str:
    """The Reef widget — conditions card now, map / charts / buoy cam later."""
    return load_ui()


# ASGI entrypoint for HTTP deployment (uvicorn mcp_reef.server:app)
app = mcp.http_app()


# Stdio entrypoint for mpak / Claude Desktop
if __name__ == "__main__":
    print("Reef MCP App starting in stdio mode…", file=sys.stderr)
    mcp.run()
