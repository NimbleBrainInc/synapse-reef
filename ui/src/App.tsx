import { useEffect, useState, type CSSProperties } from "react";
import {
  AppProvider,
  useApp,
  useConnectTheme,
  useToolResult,
} from "@nimblebrain/synapse/react";
import {
  celsiusToFahrenheit,
  degreesToCompass,
  fmt,
  metersToFeet,
  mpsToKnots,
  relativeTime,
} from "./units";

// --- Types matching server's get_conditions structuredContent ---

interface Station {
  id: string;
  name: string;
  lat: number;
  lng: number;
  capabilities?: string[];
}

interface Observation {
  observed_at: string | null;
  wind: {
    direction_deg: number | null;
    speed_mps: number | null;
    gust_mps: number | null;
  };
  waves: {
    height_m: number | null;
    dominant_period_s: number | null;
    average_period_s: number | null;
    mean_direction_deg: number | null;
  };
  atmosphere: {
    pressure_hpa: number | null;
    pressure_tendency_hpa: number | null;
    air_temp_c: number | null;
    dewpoint_c: number | null;
    visibility_nmi: number | null;
  };
  water: {
    temperature_c: number | null;
    tide_ft: number | null;
  };
}

interface ConditionsResult {
  station?: Station;
  observation?: Observation | null;
  error?: string;
}

// --- Conditions card ---

function ConditionsCard({ data }: { data: ConditionsResult }) {
  const app = useApp();
  const theme = useConnectTheme();
  const c = (token: string, fallback: string) => theme.tokens[token] || fallback;

  if (data.error || !data.station) {
    return (
      <div style={errorBoxStyle(c)}>
        <strong style={{ fontWeight: "var(--font-weight-semibold, 600)" }}>
          Couldn't load conditions.
        </strong>
        <div style={{ marginTop: 4, fontSize: "var(--font-text-sm-size, 0.875rem)" }}>
          {data.error ?? "Unknown error"}
        </div>
      </div>
    );
  }

  const { station, observation: obs } = data;

  if (!obs) {
    return (
      <div style={errorBoxStyle(c)}>
        <strong style={{ fontWeight: "var(--font-weight-semibold, 600)" }}>
          No recent observation.
        </strong>
        <div style={{ marginTop: 4, fontSize: "var(--font-text-sm-size, 0.875rem)" }}>
          Buoy {station.id} ({station.name}) is offline or hasn't reported recently.
        </div>
      </div>
    );
  }

  const waveFt = obs.waves.height_m == null ? null : metersToFeet(obs.waves.height_m);
  const swellDir =
    obs.waves.mean_direction_deg == null ? null : degreesToCompass(obs.waves.mean_direction_deg);
  const windKt = obs.wind.speed_mps == null ? null : mpsToKnots(obs.wind.speed_mps);
  const gustKt = obs.wind.gust_mps == null ? null : mpsToKnots(obs.wind.gust_mps);
  const windDir =
    obs.wind.direction_deg == null ? null : degreesToCompass(obs.wind.direction_deg);
  const waterF =
    obs.water.temperature_c == null ? null : celsiusToFahrenheit(obs.water.temperature_c);
  const tendency = obs.atmosphere.pressure_tendency_hpa;
  const tendencyArrow = tendency == null ? "" : tendency > 0 ? " ↗" : tendency < 0 ? " ↘" : " →";

  const observed = obs.observed_at ? relativeTime(obs.observed_at) : "";

  function shareToChat() {
    const lead = `Conditions at Buoy ${station.id} (${station.name}):`;
    const values: string[] = [];
    if (waveFt != null) {
      const period = fmt(obs.waves.dominant_period_s, 0);
      values.push(`${fmt(waveFt, 1)}ft @ ${period}s${swellDir ? ` ${swellDir}` : ""} swell`);
    }
    if (windKt != null) {
      values.push(`${fmt(windKt, 0)}kt${windDir ? ` ${windDir}` : ""} wind`);
    }
    if (waterF != null) values.push(`${fmt(waterF, 0)}°F water`);
    const tail = observed ? ` (observed ${observed})` : "";
    app.sendMessage(`${lead} ${values.join(", ")}${tail}`);
  }

  function openStationPage() {
    app.openLink(`https://www.ndbc.noaa.gov/station_page.php?station=${station.id}`);
  }

  return (
    <div style={cardStyle(c)}>
      {/* Header */}
      <div style={headerStyle(c)}>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: "var(--font-text-xs-size, 0.78rem)",
              color: c("--color-text-secondary", "#6b7280"),
            }}
          >
            Buoy {station.id}
          </div>
          <div
            style={{
              fontWeight: "var(--font-weight-semibold, 600)",
              fontSize: "var(--font-heading-sm-size, 1.05rem)",
              fontFamily: "var(--nb-font-heading, var(--font-sans))",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {station.name}
          </div>
        </div>
        <button
          type="button"
          onClick={openStationPage}
          style={iconBtnStyle(c)}
          title="Open NOAA station page"
          aria-label="Open NOAA station page"
        >
          ↗
        </button>
      </div>

      {/* Primary metrics */}
      <div style={metricsRowStyle}>
        <Metric label="Wave height" big={fmt(waveFt, 1)} unit="ft" sub={
          obs.waves.dominant_period_s == null
            ? "—"
            : `@ ${fmt(obs.waves.dominant_period_s, 0)}s${swellDir ? ` ${swellDir}` : ""}`
        } c={c} />
        <Metric label="Wind" big={fmt(windKt, 0)} unit="kt" sub={
          windDir == null ? "—" : `${windDir}${gustKt != null ? ` · G ${fmt(gustKt, 0)}` : ""}`
        } c={c} />
        <Metric label="Water" big={fmt(waterF, 0)} unit="°F" sub={
          obs.atmosphere.pressure_hpa == null
            ? ""
            : `${fmt(obs.atmosphere.pressure_hpa, 0)} hPa${tendencyArrow}`
        } c={c} />
      </div>

      {/* Footer */}
      <div style={footerStyle(c)}>
        <span>{observed || "no timestamp"}</span>
        <span style={{ flex: 1 }} />
        <button type="button" onClick={shareToChat} style={textBtnStyle(c)}>
          📤 Share to chat
        </button>
      </div>
    </div>
  );
}

function Metric({
  label,
  big,
  unit,
  sub,
  c,
}: {
  label: string;
  big: string;
  unit: string;
  sub: string;
  c: (k: string, f: string) => string;
}) {
  return (
    <div style={{ minWidth: 0 }}>
      <div
        style={{
          fontSize: "var(--font-text-xs-size, 0.72rem)",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: c("--color-text-secondary", "#6b7280"),
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span
          style={{
            fontSize: "var(--font-heading-lg-size, 1.65rem)",
            fontWeight: "var(--font-weight-semibold, 600)",
            fontFamily: "var(--nb-font-heading, var(--font-sans))",
            lineHeight: 1,
          }}
        >
          {big}
        </span>
        <span
          style={{
            fontSize: "var(--font-text-sm-size, 0.9rem)",
            color: c("--color-text-secondary", "#6b7280"),
          }}
        >
          {unit}
        </span>
      </div>
      <div
        style={{
          fontSize: "var(--font-text-sm-size, 0.85rem)",
          color: c("--color-text-secondary", "#6b7280"),
        }}
      >
        {sub || "—"}
      </div>
    </div>
  );
}

// --- Empty / lookup state for dev preview ---

function LookupForm({ onSubmit }: { onSubmit: (id: string) => void }) {
  const theme = useConnectTheme();
  const c = (k: string, f: string) => theme.tokens[k] || f;
  const [id, setId] = useState("");

  return (
    <div style={{ ...cardStyle(c), padding: "1.5rem 1.25rem" }}>
      <div
        style={{
          fontWeight: "var(--font-weight-semibold, 600)",
          fontSize: "var(--font-heading-sm-size, 1.05rem)",
          fontFamily: "var(--nb-font-heading, var(--font-sans))",
          marginBottom: 4,
        }}
      >
        🌊 Reef
      </div>
      <div
        style={{
          fontSize: "var(--font-text-sm-size, 0.9rem)",
          color: c("--color-text-secondary", "#6b7280"),
          marginBottom: 12,
        }}
      >
        Live ocean conditions from NOAA buoys. Enter a station ID or wait for the model to call <code>get_conditions</code>.
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (id.trim()) onSubmit(id.trim());
        }}
        style={{ display: "flex", gap: 8 }}
      >
        <input
          name="station_id"
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="e.g. 46042"
          style={{
            flex: 1,
            padding: "0.5rem 0.75rem",
            border: `1px solid ${c("--color-border-primary", "#e5e7eb")}`,
            borderRadius: "var(--border-radius-sm, 0.375rem)",
            background: c("--color-background-secondary", "#f9fafb"),
            color: "inherit",
            fontFamily: "inherit",
            fontSize: "var(--font-text-md-size, 0.95rem)",
            outline: "none",
          }}
        />
        <button
          type="submit"
          style={{
            padding: "0.5rem 1rem",
            background: c("--color-text-accent", "#2563eb"),
            color: c("--nb-color-accent-foreground", c("--color-text-inverse", "#fff")),
            border: "none",
            borderRadius: "var(--border-radius-sm, 0.375rem)",
            fontSize: "var(--font-text-md-size, 0.9rem)",
            fontWeight: "var(--font-weight-medium, 500)",
            cursor: "pointer",
          }}
        >
          Look up
        </button>
      </form>
    </div>
  );
}

// --- Top-level dispatch ---

function ReefApp() {
  const app = useApp();
  const result = useToolResult();
  const [data, setData] = useState<ConditionsResult | null>(null);
  const [loading, setLoading] = useState(false);

  // Initial render: pull from toolInfo (if widget opened in response to a tool call).
  useEffect(() => {
    const tool = app.toolInfo?.tool as
      | { name?: string; structuredContent?: ConditionsResult; result?: { structuredContent?: ConditionsResult; data?: ConditionsResult } }
      | undefined;
    if (!tool) return;
    const payload =
      tool.structuredContent ??
      tool.result?.structuredContent ??
      tool.result?.data ??
      undefined;
    if (payload) setData(payload);
  }, [app]);

  // Live: when the model calls a tool while widget is open. Synapse SDK's
  // parseToolResult parses content[0].text JSON into `data` and ignores the
  // spec's structuredContent field — read both for forward compatibility.
  useEffect(() => {
    if (!result) return;
    const payload =
      (result.structuredContent as ConditionsResult | undefined) ??
      (result as unknown as { data?: ConditionsResult }).data;
    if (payload) setData(payload);
  }, [result]);

  async function lookup(stationId: string) {
    setLoading(true);
    try {
      const r = (await app.callTool("get_conditions", { station_id: stationId })) as {
        data?: ConditionsResult;
        structuredContent?: ConditionsResult;
      };
      const payload = r.data ?? r.structuredContent;
      if (payload) setData(payload);
    } finally {
      setLoading(false);
    }
  }

  if (loading && !data) {
    return <div style={{ padding: "1rem", color: "var(--color-text-secondary)" }}>Loading…</div>;
  }
  if (!data) return <LookupForm onSubmit={lookup} />;
  return <ConditionsCard data={data} />;
}

export function App() {
  return (
    <AppProvider name="reef" version="0.1.0" autoResize>
      <ReefApp />
    </AppProvider>
  );
}

// --- Style helpers ---

const cardStyle = (c: (k: string, f: string) => string): CSSProperties => ({
  background: c("--color-background-primary", "#fff"),
  color: c("--color-text-primary", "#1a1a1a"),
  border: `1px solid ${c("--color-border-primary", "#e5e7eb")}`,
  borderRadius: "var(--border-radius-lg, 0.75rem)",
  boxShadow: "var(--shadow-sm, 0 1px 2px rgba(0,0,0,0.05))",
  padding: "1rem 1.25rem",
  fontFamily:
    "var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
  fontSize: "var(--font-text-md-size, 1rem)",
  maxWidth: 480,
  width: "100%",
  margin: "0 auto",
  boxSizing: "border-box",
});

const headerStyle = (c: (k: string, f: string) => string): CSSProperties => ({
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  gap: 12,
  marginBottom: 14,
  paddingBottom: 10,
  borderBottom: `1px solid ${c("--color-border-primary", "#e5e7eb")}`,
});

const metricsRowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
  gap: 16,
  marginBottom: 14,
};

const footerStyle = (c: (k: string, f: string) => string): CSSProperties => ({
  display: "flex",
  alignItems: "center",
  gap: 12,
  fontSize: "var(--font-text-xs-size, 0.78rem)",
  color: c("--color-text-secondary", "#6b7280"),
  paddingTop: 10,
  borderTop: `1px solid ${c("--color-border-primary", "#e5e7eb")}`,
});

const iconBtnStyle = (c: (k: string, f: string) => string): CSSProperties => ({
  background: "transparent",
  color: c("--color-text-secondary", "#6b7280"),
  border: `1px solid ${c("--color-border-primary", "#e5e7eb")}`,
  borderRadius: "var(--border-radius-sm, 0.375rem)",
  width: 28,
  height: 28,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  cursor: "pointer",
  fontSize: "var(--font-text-sm-size, 0.85rem)",
  flexShrink: 0,
});

const textBtnStyle = (c: (k: string, f: string) => string): CSSProperties => ({
  background: "transparent",
  color: c("--color-text-accent", "#2563eb"),
  border: "none",
  cursor: "pointer",
  fontSize: "var(--font-text-sm-size, 0.85rem)",
  fontWeight: "var(--font-weight-medium, 500)",
  padding: "2px 6px",
  fontFamily: "inherit",
});

const errorBoxStyle = (c: (k: string, f: string) => string): CSSProperties => ({
  ...cardStyle(c),
  background: c("--color-background-danger", c("--color-background-secondary", "#fef2f2")),
  borderColor: c("--color-border-danger", c("--color-border-primary", "#fecaca")),
  color: c("--color-text-danger", c("--color-text-primary", "#991b1b")),
});
