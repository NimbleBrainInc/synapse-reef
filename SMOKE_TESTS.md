# Smoke Tests — Reef

Manual verification queries for Reef. Run before every release; add new entries as features land. Each test is **independently runnable** and **deterministic** within the noted tolerances (NDBC data is live, so exact values shift hourly).

## How to run

### Local preview (fastest)
```bash
cd ui && npm run dev
# Open http://localhost:5173/__preview (or 5174/5175 if other Vite servers are up)
```

The Synapse preview iframes the widget with a host shell that publishes theme tokens and a "Toggle Theme" button. Use this for every test marked **[preview]** below.

### Direct MCP server (for tool-only verification)
```bash
uv run python -c "
import asyncio
from mcp_reef import server
from mcp_reef.ndbc import fetch_realtime_stdmet
from mcp_reef.parsing import parse_realtime2_stdmet
# Run any tool you want to probe here
"
```

Or hit `/__mcp` directly via the preview's proxy:
```bash
curl -s -X POST http://localhost:5175/__mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"get_conditions","arguments":{"station_id":"46042"}}}'
```

### NimbleBrain platform (when deployed)
Open the app in NimbleBrain, type the user-facing prompt, verify the inline card matches expectations.

### ChatGPT Developer Mode (when public HTTPS URL is up)
`Settings → Apps & Connectors → Advanced settings → Add custom connector`. Paste the prompt, verify the widget renders.

## Reference stations

Use these station IDs throughout — they are reliably reporting and exercise different code paths:

| Station | Location | Why |
|---|---|---|
| `46042` | Monterey, CA (NDBC) | Standard wave + wind buoy. Has camera. The default "everything works" test. |
| `41001` | East Hatteras, NC | Atlantic-side equivalent. Different time zone display. |
| `42001` | Mid Gulf | Gulf of Mexico. Has camera. |
| `45001` | Mid Lake Superior | Great Lakes (no waves in winter). Tests "missing field" rendering. |
| `prhh1` | Pearl Harbor tide gauge | Met-flagged but no wave sensor. Tests `has_met=true` overpromise (returns nulls for waves). |
| `99999` | invalid | Tests "Unknown station" error path. |

---

## Test catalog

### T1 — find_buoys: gazetteer place lookup **[server]**
**Prompt:** "Find buoys near Pipeline within 100nm with met capability"
**Tool call:** `find_buoys(place="Pipeline", radius_nm=100, capabilities=["met"])`
**Expect:** ≥10 matches; closest is on Oahu (`prhh1`, `hrrh1`, or `51210`); `match_count >= 10`; first match `distance_nm < 25`; no `error` field.

### T2 — find_buoys: coordinate lookup **[server]**
**Tool call:** `find_buoys(lat=36.6, lng=-122.0, radius_nm=50, capabilities=["met"])`
**Expect:** Returns `46042` (Monterey, ~30nm) as closest met-capable.

### T3 — find_buoys: unknown place **[server]**
**Tool call:** `find_buoys(place="Atlantis")`
**Expect:** `error: "Unknown place: 'Atlantis'"`, `matches: []`. No crash.

### T4 — find_buoys: missing args **[server]**
**Tool call:** `find_buoys()` (no args)
**Expect:** `error: "Provide either 'place' or both 'lat' and 'lng'."`, `matches: []`.

### T5 — get_conditions: known good station **[preview + server]**
**Prompt:** "What are the conditions at buoy 46042?"
**Tool call:** `get_conditions(station_id="46042")`
**Server expect:** `station.id == "46042"`, `station.name` contains "MONTEREY", `observation.observed_at` parseable as ISO 8601 UTC, `observation.wind.speed_mps` is a number, `observation.atmosphere.pressure_hpa` between 980–1040, no `error` field.
**Preview expect:** Inline card renders with:
- Header "Buoy 46042" + station name
- Three metrics: WAVE HEIGHT (in ft), WIND (in kt), WATER (in °F)
- 1019 hPa-ish pressure shown under WATER
- "N min ago" timestamp where N is small (≤120)
- 📤 Share to chat button visible
- ↗ open-link button visible

### T6 — get_conditions: invalid station **[preview + server]**
**Tool call:** `get_conditions(station_id="99999")`
**Server expect:** Returns `{error: "Unknown station: '99999'", station_id: "99999"}`.
**Preview expect:** Error card renders with red/danger styling, "Couldn't load conditions." headline, "Unknown station: '99999'" body. Card uses danger tokens (`--color-text-danger`), not default colors.

### T7 — get_conditions: station with no recent obs **[preview + server]**
**Tool call:** `get_conditions(station_id="prhh1")` (Pearl Harbor tide gauge, met-flagged but minimal data)
**Server expect:** `station.id == "prhh1"`, `observation` is non-null but wave fields are null. No `error`.
**Preview expect:** Card renders with `—` shown for missing waves; wind/water/pressure may also be `—` depending on time of day. Should NOT show error card; should show normal card with em-dashes for missing values.

### T8 — Theme switching: dark → light **[preview]**
1. Default load is dark mode (Synapse preview default).
2. Click "Toggle Theme" in the host shell header.
3. **Expect:** Card switches to light mode without re-mounting; values stay; no flash of unstyled content. All text remains readable; borders stay visible; share-to-chat link readable.

### T9 — Theme switching: light → dark **[preview]**
Toggle back to dark. Same expectations.

### T10 — `ui/message` bridge (Share to chat) **[preview]**
1. Render conditions card (T5).
2. Click "📤 Share to chat".
3. **Expect via captured postMessage:** A `ui/message` JSON-RPC notification with:
   - `params.role == "user"`
   - `params.content[0].type == "text"`
   - Text starts with `"Conditions at Buoy 46042 (MONTEREY"` and contains `"ft @"`, `"kt"`, `"°F water"`, `"(observed"`.

### T11 — `ui/open-link` bridge (NOAA station page) **[preview]**
1. Render conditions card (T5).
2. Click the ↗ icon in the header (top-right of card).
3. **Expect via captured postMessage:** A `ui/open-link` JSON-RPC request with `params.url == "https://www.ndbc.noaa.gov/station_page.php?station=46042"`.

### T12 — Synapse handshake completes **[preview]**
On widget load, browser console should show:
- `[bridge] ui/notifications/size-changed` (one or more — `autoResize` working)
- No JavaScript errors (404 favicon is harmless and OK)
**Expect:** Console messages include `[bridge]` events, no red errors.

### T13 — CSS variable token coverage **[preview]**
Inspect `document.documentElement.style` inside the iframe via DevTools.
**Expect:** At least these tokens have non-empty values:
- `--color-background-primary`
- `--color-background-secondary`
- `--color-text-primary`
- `--color-text-secondary`
- `--color-text-accent`
- `--color-border-primary`
- `--font-sans`

Card visual should use these (not hardcoded defaults).

### T14 — Server module imports cleanly **[server]**
```bash
uv run python -c "from mcp_reef import server; print(server.mcp.name)"
```
**Expect:** Prints `Reef`, no warnings, no exceptions.

### T15 — Catalog & gazetteer load **[server]**
```bash
uv run python -c "
from mcp_reef.catalog import StationCatalog
from mcp_reef.gazetteer import Gazetteer
print('stations:', len(StationCatalog.load().stations))
print('places:', len(Gazetteer.load().places))
"
```
**Expect:** ≥1,000 stations (full NDBC catalog), ≥30 places.

### T16 — Refresh script **[server, network]**
```bash
uv run python scripts/refresh_data.py
```
**Expect:** "Parsed N stations" where N ≥ 1,200; "M cam-equipped stations" where M ≥ 70; writes `data/stations.json` without error.

### T17 — Parser handles missing-value sentinels **[server]**
Synthesized text with `MM`, `99.0`, `999`, `9999.0`:
```python
from mcp_reef.parsing import parse_realtime2_stdmet
text = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2026 04 28 17 50 999 99.0 99.0    MM    MM    MM 999 9999.0  99.0  99.0  99.0   MM   MM    MM"""
obs = parse_realtime2_stdmet(text)
assert obs["wind"]["direction_deg"] is None
assert obs["wind"]["speed_mps"] is None
assert obs["waves"]["height_m"] is None
assert obs["atmosphere"]["pressure_hpa"] is None
print("OK")
```
**Expect:** Prints `OK`. All sentinels collapse to `None`.

---

## Future tests (slices not yet built)

When these features ship, add tests here.

### Slice 2 — map + trend chart
- T18: `get_trend(station_id, hours=24)` returns time-series array; chart renders in fullscreen mode
- T19: Map view in fullscreen — pan / zoom / pin click → conditions card swap
- T20: `geolocation` permission flow — click "Near me" → browser prompts → buoys returned
- T21: ERDDAP fallback when `hours > 120` (history beyond realtime2's 45-day window)

### Slice 3 — wave spectrum, DART, alerts, export, buoy cam
- T22: `get_wave_spectrum(station_id)` returns directional energy; spectrum widget animates and pauses off-screen
- T23: `list_dart_events()` in PIP mode — ticker pinned, polling every 60s
- T24: `subscribe_alert` + `cancel_alert` — round-trip with `destructive_hint=true` confirmation surfaces correctly
- T25: `export_csv` — file download in ChatGPT (via `window.openai.getFileDownloadUrl`), NimbleBrain (via `synapse/download-file`), and blob URL fallback in other hosts
- T26: Buoy cam carousel — 6-pane swipe, "📤 Save snapshot" via `window.openai.uploadFile`, refresh every 15min when fullscreen

### Cross-host
- T27: Same widget renders correctly in NimbleBrain platform (full token set, NimbleBrain extensions active)
- T28: Same widget renders correctly in ChatGPT Developer Mode (only spec primitives, NB extensions degrade silently)
- T29: Same widget renders correctly in Claude (paid plans only, custom connector)

---

## Known issues to track

- **Synapse SDK ignores `structuredContent`.** `parseToolResult` in `packages/synapse/src/result-parser.ts` parses `content[0].text` as JSON into `data` and never reads the spec's `structuredContent` field. Reef works around this by reading `r.data ?? r.structuredContent`. File: track for a future Synapse PR.
- **`activestations.xml` overpromises `met="y"`.** Tide gauges like `prhh1` carry the met flag but report 0 wind / no waves. T7 covers this; future "has waves" capability would need to be derived (probe for `<id>.spec` at refresh time).
