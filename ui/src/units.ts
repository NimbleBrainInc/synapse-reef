// Unit conversions and human-readable formatters.
// All inputs assume NDBC native units (SI: m/s, m, °C, hPa).

export function metersToFeet(m: number): number {
  return m * 3.28084;
}

export function mpsToKnots(mps: number): number {
  return mps * 1.94384;
}

export function celsiusToFahrenheit(c: number): number {
  return c * 9 / 5 + 32;
}

const COMPASS_16 = [
  "N", "NNE", "NE", "ENE",
  "E", "ESE", "SE", "SSE",
  "S", "SSW", "SW", "WSW",
  "W", "WNW", "NW", "NNW",
];

export function degreesToCompass(deg: number): string {
  // Wind/wave direction is "from" — display as where it's coming from.
  const idx = Math.round((deg % 360) / 22.5) % 16;
  return COMPASS_16[idx];
}

export function relativeTime(isoTimestamp: string): string {
  const then = Date.parse(isoTimestamp);
  if (Number.isNaN(then)) return "";
  const diffSec = Math.max(0, (Date.now() - then) / 1000);
  if (diffSec < 60) return "just now";
  const minutes = Math.floor(diffSec / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function fmt(value: number | null | undefined, digits = 1): string {
  return value == null ? "—" : value.toFixed(digits);
}
