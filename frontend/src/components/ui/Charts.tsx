"use client";

import { useRef, type ReactNode } from "react";
import { Tooltip } from "./Feedback";
import { downloadCSV, svgToPng } from "@/lib/chartExport";

interface Ratio {
  numerator: number;
  denominator: number;
  rate: number | null;
}

const SERIES = ["var(--cv-series-1)", "var(--cv-series-2)", "var(--cv-series-3)", "var(--cv-series-4)"];

function niceMax(m: number): number {
  if (m <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(m)));
  const n = m / pow;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return step * pow;
}

// A metric with its rate AND its denominator + completeness — never a bare
// percentage (rule #5). A thin meter visualises the rate.
export function MetricMeter({ label, ratio, tooltip }: { label: string; ratio: Ratio; tooltip?: string }) {
  const pct = ratio.rate != null ? Math.round(ratio.rate * 100) : null;
  return (
    <div style={{ padding: "12px 0", borderBottom: "1px solid var(--cv-hairline)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <span style={{ fontSize: 12.5, color: "var(--cv-text-secondary)", display: "inline-flex", alignItems: "center", gap: 5 }}>
          {label}
          {tooltip && <Tooltip text={tooltip} />}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--cv-text-primary)" }} className="cv-num">
          {pct != null ? `${pct}%` : "—"}
          <span style={{ fontSize: 11, color: "var(--cv-text-muted)", fontWeight: 400 }}>
            {" "}
            ({ratio.numerator}/{ratio.denominator})
          </span>
        </span>
      </div>
      <div style={{ height: 6, borderRadius: 4, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${pct ?? 0}%`,
            background: "var(--cv-accent-gradient)",
            borderRadius: 4,
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.35)",
          }}
        />
      </div>
    </div>
  );
}

// Horizontal care-journey funnel — stages darken left-to-right to show
// progression (cureva-docs/09 "Chart card").
export function Funnel({ stages }: { stages: { label: string; value: number }[] }) {
  const max = Math.max(1, ...stages.map((s) => s.value));
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {stages.map((s, i) => {
        const pct = Math.round((s.value / max) * 100);
        const darken = 1 - i * 0.14;
        return (
          <div key={s.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, marginBottom: 4 }}>
              <span style={{ color: "var(--cv-text-secondary)" }}>{s.label}</span>
              <span className="cv-num" style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{s.value}</span>
            </div>
            <div style={{ height: 22, borderRadius: 6, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${Math.max(pct, 3)}%`,
                  background: `linear-gradient(90deg, rgba(47,95,214,${0.95 * darken}), rgba(47,95,214,${0.6 * darken}))`,
                  borderRadius: 6,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Simple vertical bar group (counts).
export function BarGroup({ data }: { data: { label: string; value: number; status?: string }[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const color = (s?: string) =>
    s === "danger" ? "var(--cv-danger-icon)" : s === "warning" ? "var(--cv-warning-icon)" : "var(--cv-accent-solid)";
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 14, height: 160, paddingTop: 10 }}>
      {data.map((d) => (
        <div key={d.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
          <span className="cv-num" style={{ fontSize: 11.5, color: "var(--cv-text-primary)", fontWeight: 600 }}>{d.value}</span>
          <div
            style={{
              width: "70%",
              height: `${Math.max((d.value / max) * 120, 3)}px`,
              background: color(d.status),
              borderRadius: "4px 4px 0 0",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.35)",
            }}
          />
          <span style={{ fontSize: 10.5, color: "var(--cv-text-muted)", textAlign: "center" }}>{d.label}</span>
        </div>
      ))}
    </div>
  );
}

export function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      style={{
        background: "var(--cv-card-bg)",
        border: "1px solid var(--cv-card-border)",
        boxShadow: "var(--cv-card-shadow)",
        borderRadius: "var(--cv-radius-card)",
        padding: "18px 20px",
      }}
    >
      <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: "0 0 14px" }}>{title}</h2>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// WS8 — chart kit: SVG line chart, stacked bars, league table, delta badge, and
// an export-capable card. Every chart reads design-system CSS vars so light/dark
// is automatic; ChartCard offers CSV (data) and PNG (image) export.
// ---------------------------------------------------------------------------

export interface LinePoint { x: string; y: number | null }
export interface LineSeries { name: string; points: LinePoint[] }

// Trend line(s). `unit="percent"` fixes the axis to 0–100; otherwise it scales
// to a nice maximum. Null points break the line (a gap = no data, never zero).
export function LineChart({
  series,
  unit = "count",
  yMax: yMaxProp,
}: {
  series: LineSeries[];
  unit?: "percent" | "count";
  yMax?: number;
}) {
  const W = 680;
  const H = 260;
  const L = 46, R = 14, T = 14, B = 30;
  const x0 = L, x1 = W - R, y0 = T, y1 = H - B;
  const plotW = x1 - x0, plotH = y1 - y0;

  const xs = series[0]?.points.map((p) => p.x) ?? [];
  const n = xs.length;
  const allY = series.flatMap((s) => s.points.map((p) => p.y)).filter((v): v is number => v != null);
  const dataMax = allY.length ? Math.max(...allY) : 1;
  const yMax = yMaxProp ?? (unit === "percent" ? 100 : niceMax(dataMax));

  const px = (i: number) => (n <= 1 ? (x0 + x1) / 2 : x0 + (i / (n - 1)) * plotW);
  const py = (v: number) => y1 - (v / yMax) * plotH;

  const gridVals = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(yMax * f));
  const labelEvery = n <= 8 ? 1 : Math.ceil(n / 7);

  function pathFor(pts: LinePoint[]): string {
    let d = "";
    let pen = false;
    pts.forEach((p, i) => {
      if (p.y == null) { pen = false; return; }
      const cmd = pen ? "L" : "M";
      d += `${cmd}${px(i).toFixed(1)},${py(p.y).toFixed(1)} `;
      pen = true;
    });
    return d.trim();
  }

  const single = series.length === 1;
  const fmt = (v: number) => (unit === "percent" ? `${v}%` : `${v}`);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }} role="img">
        {gridVals.map((v) => (
          <g key={v}>
            <line x1={x0} x2={x1} y1={py(v)} y2={py(v)} stroke="var(--cv-hairline)" strokeWidth={1} />
            <text x={x0 - 6} y={py(v) + 3} textAnchor="end" fontSize={10} fill="var(--cv-text-muted)">{fmt(v)}</text>
          </g>
        ))}
        {xs.map((x, i) =>
          i % labelEvery === 0 ? (
            <text key={x + i} x={px(i)} y={H - 10} textAnchor="middle" fontSize={10} fill="var(--cv-text-muted)">{x}</text>
          ) : null,
        )}
        {series.map((s, si) => {
          const color = SERIES[si % SERIES.length];
          return (
            <g key={s.name}>
              {single && (
                <path
                  d={`${pathFor(s.points)} L${px(lastIdx(s.points))},${y1} L${px(firstIdx(s.points))},${y1} Z`}
                  fill="var(--cv-accent-soft)"
                  stroke="none"
                />
              )}
              <path d={pathFor(s.points)} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
              {s.points.map((p, i) =>
                p.y == null ? null : (
                  <circle key={i} cx={px(i)} cy={py(p.y)} r={2.6} fill={color}>
                    <title>{`${p.x}: ${fmt(p.y)}`}</title>
                  </circle>
                ),
              )}
            </g>
          );
        })}
      </svg>
      {series.length > 1 && (
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 8 }}>
          {series.map((s, si) => (
            <span key={s.name} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--cv-text-secondary)" }}>
              <span style={{ width: 10, height: 3, borderRadius: 2, background: SERIES[si % SERIES.length] }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function firstIdx(pts: LinePoint[]) { return Math.max(0, pts.findIndex((p) => p.y != null)); }
function lastIdx(pts: LinePoint[]) { for (let i = pts.length - 1; i >= 0; i--) if (pts[i].y != null) return i; return 0; }

export interface StackSegment { label: string; value: number; color?: string }
export function StackedBars({ rows }: { rows: { label: string; segments: StackSegment[] }[] }) {
  const totals = rows.map((r) => r.segments.reduce((n, s) => n + s.value, 0));
  const max = Math.max(1, ...totals);
  const legend = rows[0]?.segments.map((s, i) => ({ label: s.label, color: s.color ?? SERIES[i % SERIES.length] })) ?? [];
  return (
    <div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {rows.map((r, ri) => (
          <div key={r.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, marginBottom: 4 }}>
              <span style={{ color: "var(--cv-text-secondary)" }}>{r.label}</span>
              <span className="cv-num" style={{ color: "var(--cv-text-primary)", fontWeight: 600 }}>{totals[ri]}</span>
            </div>
            <div style={{ display: "flex", height: 20, borderRadius: 6, overflow: "hidden", background: "var(--cv-button-disabled-bg)", width: `${Math.max((totals[ri] / max) * 100, 2)}%` }}>
              {r.segments.map((s, si) => (
                <div key={s.label} title={`${s.label}: ${s.value}`} style={{ flex: s.value, background: s.color ?? SERIES[si % SERIES.length] }} />
              ))}
            </div>
          </div>
        ))}
      </div>
      {legend.length > 1 && (
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 10 }}>
          {legend.map((l) => (
            <span key={l.label} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, color: "var(--cv-text-secondary)" }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: l.color }} />
              {l.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export interface LeagueRow { label: string; value: number; display?: string; sublabel?: string }
export function LeagueTable({ rows, maxRows = 12 }: { rows: LeagueRow[]; maxRows?: number }) {
  const sorted = [...rows].sort((a, b) => b.value - a.value).slice(0, maxRows);
  const max = Math.max(1, ...sorted.map((r) => r.value));
  if (sorted.length === 0) return <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>No facilities in scope yet.</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {sorted.map((r, i) => (
        <div key={r.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span className="cv-num" style={{ width: 20, textAlign: "right", fontSize: 11, color: "var(--cv-text-muted)" }}>{i + 1}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 3 }}>
              <span style={{ fontSize: 12, color: "var(--cv-text-primary)", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.label}</span>
              <span className="cv-num" style={{ fontSize: 12, color: "var(--cv-text-primary)", flexShrink: 0 }}>{r.display ?? r.value}</span>
            </div>
            <div style={{ height: 6, borderRadius: 4, background: "var(--cv-button-disabled-bg)", overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${Math.max((r.value / max) * 100, 2)}%`, background: "var(--cv-accent-gradient)", borderRadius: 4 }} />
            </div>
            {r.sublabel && <div style={{ fontSize: 10.5, color: "var(--cv-text-muted)", marginTop: 2 }}>{r.sublabel}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

// Period-over-period change. Up is good by default; set invert for metrics where
// down is good (e.g. maternal deaths, open referrals).
export function DeltaBadge({ delta, unit = "pts", invert = false }: { delta: number | null; unit?: "pts" | "%" | ""; invert?: boolean }) {
  if (delta == null || delta === 0) {
    return <span style={{ fontSize: 10.5, color: "var(--cv-text-muted)" }}>{delta === 0 ? "no change" : "—"}</span>;
  }
  const up = delta > 0;
  const good = invert ? !up : up;
  const color = good ? "var(--cv-success-text)" : "var(--cv-danger-text)";
  return (
    <span className="cv-num" style={{ fontSize: 10.5, fontWeight: 600, color }}>
      {up ? "▲" : "▼"} {Math.abs(delta)}{unit} vs prev
    </span>
  );
}

// Card wrapper with optional CSV/PNG export. PNG exports the first <svg> inside.
export function ChartCard({
  title,
  subtitle,
  note,
  action,
  exportCsv,
  children,
}: {
  title: string;
  subtitle?: string;
  note?: string;
  action?: ReactNode;
  exportCsv?: { name: string; header: string[]; rows: (string | number | null)[][] };
  children: ReactNode;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const btn: React.CSSProperties = {
    background: "none", border: "1px solid var(--cv-card-border)", borderRadius: 6,
    padding: "3px 8px", fontSize: 10.5, color: "var(--cv-text-secondary)", cursor: "pointer",
  };
  return (
    <div style={{ background: "var(--cv-card-bg)", border: "1px solid var(--cv-card-border)", boxShadow: "var(--cv-card-shadow)", borderRadius: "var(--cv-radius-card)", padding: "18px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, marginBottom: 2 }}>
        <div>
          <h2 style={{ fontSize: 13.5, color: "var(--cv-text-primary)", margin: 0 }}>{title}</h2>
          {subtitle && <div style={{ fontSize: 11, color: "var(--cv-text-muted)", marginTop: 2 }}>{subtitle}</div>}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0 }}>
          {action}
          {exportCsv && (
            <button style={btn} onClick={() => downloadCSV(exportCsv.name, exportCsv.header, exportCsv.rows)} title="Download data as CSV">CSV</button>
          )}
          <button
            style={btn}
            title="Download as PNG"
            onClick={() => {
              const svg = bodyRef.current?.querySelector("svg");
              if (svg) svgToPng(svg as SVGSVGElement, (exportCsv?.name ?? title).replace(/\s+/g, "-").toLowerCase());
            }}
          >
            PNG
          </button>
        </div>
      </div>
      <div ref={bodyRef} style={{ marginTop: 14 }}>{children}</div>
      {note && <p style={{ fontSize: 10.5, color: "var(--cv-text-muted)", margin: "12px 0 0", fontStyle: "italic" }}>{note}</p>}
    </div>
  );
}
