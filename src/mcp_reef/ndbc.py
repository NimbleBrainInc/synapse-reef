"""HTTP fetchers for NDBC endpoints.

NDBC serves ISO-8859-1 (not UTF-8) — explicitly setting the encoding avoids
mojibake on owner names with diacritics. CloudFront caches most files for
60 seconds; we don't add our own client-side caching here.
"""

from __future__ import annotations

import httpx

USER_AGENT = "synapse-reef/0.1 (+https://github.com/NimbleBrainInc/synapse-reef)"

REALTIME2_BASE = "https://www.ndbc.noaa.gov/data/realtime2"

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def fetch_realtime_stdmet(station_id: str) -> str | None:
    """Fetch a station's realtime2 standard-meteorological text file.

    Returns the raw text (newest observations first), or None on 404 / error.
    """
    url = f"{REALTIME2_BASE}/{station_id.upper()}.txt"
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=_TIMEOUT,
        follow_redirects=True,
    ) as client:
        try:
            r = await client.get(url)
        except httpx.HTTPError:
            return None
    if r.status_code != 200:
        return None
    r.encoding = "iso-8859-1"
    return r.text
