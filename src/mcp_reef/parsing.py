"""Parsers for NDBC fixed-width text files.

Centralizes the missing-value sentinel handling that's inconsistent across
NDBC's file formats: ``MM`` in plain-text realtime files, ``999`` for ints,
``99.0`` / ``999.0`` / ``9999.0`` / ``999.00`` for floats. Any all-9s value
in its expected width should be treated as missing — but ``999`` is also a
legitimate wind direction (≈ north), so we have to know the field width.
"""

from __future__ import annotations

from datetime import UTC, datetime

# Column order for realtime2/<station>.txt (standard meteorological — 19 cols)
STDMET_COLUMNS: tuple[str, ...] = (
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "wind_dir_deg",
    "wind_speed_mps",
    "gust_mps",
    "wave_height_m",
    "dominant_wave_period_s",
    "average_wave_period_s",
    "mean_wave_dir_deg",
    "pressure_hpa",
    "air_temp_c",
    "water_temp_c",
    "dewpoint_c",
    "visibility_nmi",
    "pressure_tendency_hpa",
    "tide_ft",
)

_INT_COLUMNS = {
    "year", "month", "day", "hour", "minute",
    "wind_dir_deg", "mean_wave_dir_deg",
}

_INT_MISSING = {999, 9999}
_FLOAT_MISSING = {99.0, 999.0, 9999.0}


def clean_value(raw: str, column: str) -> float | int | None:
    """Convert an NDBC string token to a typed value, or None for missing."""
    if raw == "MM" or raw == "":
        return None
    try:
        if column in _INT_COLUMNS:
            v = int(raw)
            return None if v in _INT_MISSING else v
        v = float(raw)
        return None if v in _FLOAT_MISSING else v
    except ValueError:
        return None


def parse_realtime2_stdmet(text: str) -> dict | None:
    """Parse the most recent observation from a realtime2 stdmet file.

    Realtime2 files have two header lines (column names + units) followed
    by data lines in newest-first order. We take the first data row.
    Returns None if there are no data rows.
    """
    data_lines = [
        ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")
    ]
    if not data_lines:
        return None

    fields = data_lines[0].split()
    if len(fields) < len(STDMET_COLUMNS):
        return None

    parsed: dict[str, float | int | None] = {}
    for col, raw in zip(STDMET_COLUMNS, fields, strict=False):
        parsed[col] = clean_value(raw, col)

    observed_at: str | None = None
    try:
        observed_at = datetime(
            int(parsed["year"]),  # type: ignore[arg-type]
            int(parsed["month"]),  # type: ignore[arg-type]
            int(parsed["day"]),  # type: ignore[arg-type]
            int(parsed["hour"]),  # type: ignore[arg-type]
            int(parsed["minute"]),  # type: ignore[arg-type]
            tzinfo=UTC,
        ).isoformat()
    except (TypeError, ValueError):
        pass

    return {
        "observed_at": observed_at,
        "wind": {
            "direction_deg": parsed["wind_dir_deg"],
            "speed_mps": parsed["wind_speed_mps"],
            "gust_mps": parsed["gust_mps"],
        },
        "waves": {
            "height_m": parsed["wave_height_m"],
            "dominant_period_s": parsed["dominant_wave_period_s"],
            "average_period_s": parsed["average_wave_period_s"],
            "mean_direction_deg": parsed["mean_wave_dir_deg"],
        },
        "atmosphere": {
            "pressure_hpa": parsed["pressure_hpa"],
            "pressure_tendency_hpa": parsed["pressure_tendency_hpa"],
            "air_temp_c": parsed["air_temp_c"],
            "dewpoint_c": parsed["dewpoint_c"],
            "visibility_nmi": parsed["visibility_nmi"],
        },
        "water": {
            "temperature_c": parsed["water_temp_c"],
            "tide_ft": parsed["tide_ft"],
        },
    }
