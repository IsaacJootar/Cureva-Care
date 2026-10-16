"use client";

import { useEffect, useMemo, useState } from "react";

// WS2 choropleth — Nigeria state map shaded by a metric. Boundaries are a
// simplified public GeoJSON (geoBoundaries gbOpen NGA ADM1, CC-BY) served as a
// static asset and fetched once. Colour encodes the value; states with no data
// stay neutral grey (a blank is never shaded as zero-performance).

type Feature = { properties: { name: string }; geometry: { type: string; coordinates: number[][][] | number[][][][] } };
type Geo = { features: Feature[] };

export interface MapDatum { name: string; value: number | null; display: string }

function normName(n: string): string {
  const s = (n || "").toLowerCase().trim();
  if (s.includes("abuja") || s.includes("federal capital") || s === "fct") return "fct";
  return s;
}

const W = 680, H = 560, PAD = 10;

export function NigeriaMap({ data, accent = "var(--cv-accent-solid)" }: { data: MapDatum[]; accent?: string }) {
  const [geo, setGeo] = useState<Geo | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/geo/nigeria-states.geojson")
      .then((r) => r.json())
      .then((g) => { if (alive) setGeo(g); })
      .catch(() => setGeo(null));
    return () => { alive = false; };
  }, []);

  const byName = useMemo(() => {
    const m = new Map<string, MapDatum>();
    for (const d of data) m.set(normName(d.name), d);
    return m;
  }, [data]);

  const maxVal = useMemo(() => Math.max(1, ...data.map((d) => d.value ?? 0)), [data]);

  const { paths, bbox } = useMemo(() => {
    if (!geo) return { paths: [], bbox: [0, 0, 1, 1] as number[] };
    let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity;
    const walk = (c: unknown) => {
      if (typeof (c as number[])[0] === "number") {
        const [lng, lat] = c as number[];
        minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng);
        minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
      } else (c as unknown[]).forEach(walk);
    };
    geo.features.forEach((f) => walk(f.geometry.coordinates));
    return { paths: geo.features, bbox: [minLng, minLat, maxLng, maxLat] };
  }, [geo]);

  const project = useMemo(() => {
    const [minLng, minLat, maxLng, maxLat] = bbox;
    const lngR = maxLng - minLng || 1, latR = maxLat - minLat || 1;
    const s = Math.min((W - 2 * PAD) / lngR, (H - 2 * PAD) / latR);
    const ox = (W - lngR * s) / 2, oy = (H - latR * s) / 2;
    return (lng: number, lat: number): [number, number] => [ox + (lng - minLng) * s, oy + (maxLat - lat) * s];
  }, [bbox]);

  function toPath(geom: Feature["geometry"]): string {
    const rings: number[][][] = geom.type === "Polygon" ? (geom.coordinates as number[][][]) : ([] as number[][][]).concat(...(geom.coordinates as number[][][][]));
    let d = "";
    for (const ring of rings) {
      ring.forEach(([lng, lat], i) => {
        const [x, y] = project(lng, lat);
        d += `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)} `;
      });
      d += "Z ";
    }
    return d.trim();
  }

  if (!geo) return <p style={{ fontSize: 12, color: "var(--cv-text-muted)" }}>Loading map…</p>;

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }} role="img">
        {paths.map((f, i) => {
          const d = byName.get(normName(f.properties.name));
          const v = d?.value ?? null;
          const norm = v == null ? null : v / maxVal;
          const fill = norm == null ? "var(--cv-button-disabled-bg)" : accent;
          const opacity = norm == null ? 0.5 : 0.2 + 0.8 * norm;
          return (
            <path key={`${f.properties.name}${i}`} d={toPath(f.geometry)} fill={fill} fillOpacity={opacity} stroke="var(--cv-card-bg)" strokeWidth={0.8}>
              <title>{`${f.properties.name}: ${d ? d.display : "no data"}`}</title>
            </path>
          );
        })}
      </svg>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, fontSize: 10.5, color: "var(--cv-text-muted)" }}>
        <span>low</span>
        <span style={{ flex: 1, maxWidth: 160, height: 8, borderRadius: 4, background: `linear-gradient(90deg, ${accent} 10%, ${accent})`, opacity: 1 }} />
        <span>high</span>
        <span style={{ marginLeft: 10, display: "inline-flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 10, borderRadius: 2, background: "var(--cv-button-disabled-bg)" }} /> no data
        </span>
      </div>
    </div>
  );
}
