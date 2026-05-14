"""UI resource loader for Reef.

In development: ``cd ui && npm run dev`` for HMR via Vite.
In production: ``cd ui && npm run build`` produces a single-file HTML bundle
at ``ui/dist/index.html`` that we read and serve as the ``ui://`` resource.
"""

from pathlib import Path

_UI_DIR = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"


def load_ui() -> str:
    """Load the built single-file HTML, or fall back to inline HTML."""
    built = _UI_DIR / "index.html"
    if built.exists():
        return built.read_text(encoding="utf-8")
    return FALLBACK_HTML


FALLBACK_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<style>
  body {
    font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, sans-serif);
    background: var(--color-background-primary, #fff);
    color: var(--color-text-primary, #1a1a1a);
    padding: 2rem;
    margin: 0;
  }
  .notice { color: var(--color-text-secondary, #6b7280); }
  code {
    background: var(--color-background-secondary, #f3f4f6);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--font-mono, ui-monospace, monospace);
  }
</style>
</head>
<body>
  <h1>\N{WATER WAVE} Reef</h1>
  <p class="notice">UI bundle not built. Run <code>cd ui && npm install && npm run build</code>.</p>
</body>
</html>
"""
