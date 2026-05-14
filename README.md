# Reef

Live ocean conditions from NOAA buoys, queryable by place name.

Reef wraps the NOAA National Data Buoy Center (NDBC) network of 1,300+ stations behind a natural-language interface. Ask about wave height, swell, wind, water temp, or live cam panoramas at any named ocean location — the gazetteer maps places like "Pipeline" or "Half Moon Bay" to the closest reporting buoy.

Built as the canonical reference for spec-compliant Synapse apps targeting any [MCP Apps](https://apps.extensions.modelcontextprotocol.io/) host (ChatGPT, Claude, NimbleBrain).

## Quick start

```bash
# Install Python deps
uv sync

# Refresh the bundled station catalog from NDBC (~1,350 stations)
uv run python scripts/refresh_data.py

# Install UI deps + start dev server (also auto-starts the MCP server)
cd ui && npm install && npm run dev
# Open http://localhost:5173/__preview (or 5174/5175 if other Vite servers are up)
```

## Structure

```
synapse-reef/
├── src/mcp_reef/      Python MCP server (FastMCP)
│   ├── server.py      Tools + ui:// resource (with AppConfig)
│   ├── ndbc.py        NDBC HTTP fetchers
│   ├── parsing.py     Fixed-width text + missing-value handling
│   ├── catalog.py     Station catalog (haversine search)
│   └── gazetteer.py   Place name → station lookup
├── data/              Bundled snapshots (refreshed via scripts/)
├── ui/                React + Vite + Synapse SDK
└── scripts/           Data refresh utilities
```

## Tools

| Tool | Purpose |
|------|---------|
| `find_buoys` | Resolve place name or lat/lng → nearby stations |
| `get_conditions` | Latest wave/wind/water observation at a station; renders inline UI card |

## Data sources

All data from NOAA NDBC (public domain):
- Real-time observations: `https://www.ndbc.noaa.gov/data/realtime2/`
- Station catalog: `https://www.ndbc.noaa.gov/activestations.xml`
- Buoy cameras: `https://www.ndbc.noaa.gov/buoycams.php`
- Historical: ERDDAP `cwwcNDBCMet` at `coastwatch.pfeg.noaa.gov/erddap`

See [SMOKE_TESTS.md](./SMOKE_TESTS.md) for verification queries.
