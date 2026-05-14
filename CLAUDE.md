# Reef MCP App

Live NOAA NDBC buoy data, queryable by place name. Reference implementation for spec-compliant Synapse apps targeting any MCP Apps host.

## Why this app exists

This is the **first synapse-app to exercise the MCP Apps spec primitives end-to-end** (`AppConfig`, `ResourceCSP`, `ToolAnnotations`, `_meta.ui.resourceUri`) and ship to non-NimbleBrain hosts (ChatGPT, Claude). When patterns prove out here, they get promoted to `synapse-apps/CLAUDE.md` as the canonical reference.

## Architecture

```
synapse-reef/
├── src/mcp_reef/          Python FastMCP server
│   ├── server.py          Tools + ui:// resource (with AppConfig)
│   ├── ndbc.py            HTTP fetchers (httpx)
│   ├── parsing.py         Fixed-width text + sentinel cleaning
│   ├── catalog.py         Station catalog (loaded from data/)
│   └── gazetteer.py       Place name → coords (loaded from data/)
├── data/                  Bundled JSON snapshots
│   ├── stations.json      Snapshot of activestations.xml + camera flags
│   └── gazetteer.json     Place → coord mapping
├── ui/                    React + Vite + Synapse SDK
└── scripts/refresh_data.py  Refreshes data/ snapshots from NDBC
```

## Why bundled data files

The runtime is fully read-through to NDBC for live observations. Static reference data (station catalog, gazetteer, camera roster) is **shipped as JSON in `data/`** and refreshed periodically by CI. This keeps the server stateless, sub-millisecond for catalog lookups, and zero-database.

## Key NDBC quirks (encoded in `parsing.py`)

Missing-value sentinels are inconsistent across files: `MM`, `99.0`, `999`, `9999.0`, `999.00`. All collapsed to `None` in one place (`parsing.clean_value`). Don't replicate this logic elsewhere.

Site is ISO-8859-1, not UTF-8. `httpx` handles this correctly when we set `r.encoding = "iso-8859-1"`.

Station IDs mix 5-digit numerics, 5-char alphanumerics (C-MAN), and 7-digit USV IDs. Treat as opaque strings, never parse.

## Verified gotchas (lessons from local POC)

- **FastMCP import path:** use `from fastmcp.apps import AppConfig, ResourceCSP` — `fastmcp.server.apps` is deprecated and emits a warning.
- **Synapse SDK ignores `structuredContent`:** `parseToolResult` in `packages/synapse/src/result-parser.ts` parses `content[0].text` as JSON into `data` and **never reads** the spec's `structuredContent`. Read both: `r.data ?? r.structuredContent`. Worth a future Synapse PR.
- **`activestations.xml` overpromises `met="y"`:** tide gauges like `prhh1` carry the met flag but report 0 wind / no waves. Future "has waves" capability would need to be derived (probe for `<id>.spec` at refresh time).
- **NimbleBrain canonical tokens (81 total):** prefer `--border-radius-{sm,md,lg,xl}`, `--font-text-{xs,sm,md,lg}-size`, `--font-heading-{xs,sm,md,lg,xl}-size`, `--font-weight-{normal,medium,semibold,bold}`, `--shadow-{sm,md,lg}`, `--color-{text,background,border,ring}-{primary,secondary,danger,success,warning,info}`, `--nb-color-{accent-foreground,danger,success,warning}`, `--nb-font-heading`. Never hardcode px values for radii or font sizes — they look wrong in NimbleBrain's brand chrome.

## Spec primitives exercised

(Tracked here so we know what's tested vs aspirational. See `synapse-apps/CLAUDE.md` for the broader compliance story.)

| Primitive | Where |
|---|---|
| `ToolAnnotations` (read-only, open-world, idempotent) | All tools in `server.py` |
| `AppConfig.resource_uri` linking tool → UI | `get_conditions` |
| `AppConfig.csp` declaring NDBC + ERDDAP origins | `ui://reef/main` resource |
| `AppConfig.domain` (unique app id for ChatGPT) | `ui://reef/main` resource |
| `AppConfig.prefers_border` | `ui://reef/main` resource |
| `text/html;profile=mcp-app` MIME | Auto via FastMCP `resolve_ui_mime_type` for `ui://` URIs |
| `ui/message` (Share to chat) | `App.sendMessage` in conditions card |
| `ui/open-link` (NOAA station page) | `App.openLink` in conditions card header |
| Live theme reactivity via `ui/notifications/host-context-changed` | Synapse SDK auto-handled |
| Standard CSS variables on `:root` | All styles use canonical NB tokens |

Yet to add (later slices): tool `visibility: ["app"]` for polling, `_meta.ui.permissions.geolocation`, `idempotent_hint=true` on cam tools, prompts, fullscreen/pip display modes, `ui/update-model-context`.

## Commands

```bash
# Dev (UI + auto-starts MCP server in stdio)
cd ui && npm run dev
# http://localhost:5173/__preview (or next free port)

# Run server standalone (HTTP — for ChatGPT testing via cloudflared/ngrok)
uv run uvicorn mcp_reef.server:app --port 8001

# Run server stdio (for Claude Desktop / mpak)
uv run python -m mcp_reef.server

# Refresh bundled data snapshots
uv run python scripts/refresh_data.py

# Lint / typecheck
uv run ruff check src/
uv run ty check src/
```

See [SMOKE_TESTS.md](./SMOKE_TESTS.md) for the verification query catalog.
