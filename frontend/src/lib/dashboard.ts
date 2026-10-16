// Dashboard/reporting API helpers (Facility lead + Organisation user).
import { apiGet } from "./api";

export interface Ratio {
  numerator: number;
  denominator: number;
  rate: number | null;
}

export interface Summary {
  access_level: string;
  scope: { facility_count: number };
  operational: {
    anc_contacts: number;
    deliveries: number;
    pnc_contacts: number;
    verified_records: number;
    open_referrals: number;
    closed_referrals: number;
  };
  care_journey: {
    booked_episodes: number;
    anc_contacts: number;
    deliveries: number;
    pnc_contacts: number;
    delivery_linkage: Ratio;
    postnatal_linkage: Ratio;
  };
  metrics: Record<string, Ratio>;
  outcomes: { live_births: number; still_births: number; maternal_deaths: number; low_birth_weight: number };
}

export interface Workspace {
  role: string;
  access_level: string;
  facility_count: number;
  facilities: { id: string; name: string; region: string }[];
  summary: Summary;
}

export interface FacilityRow {
  id: string;
  name: string;
  region: string;
  last_intake: string | null;
  is_stale: boolean;
  verified_records: number;
  open_referrals: number;
  deliveries: number;
}

export interface RecordRow {
  id: string;
  register_family: string;
  service_date: string | null;
  facility_id: string;
  values: Record<string, unknown>;
  flags: Record<string, { kind: string; message: string }> | null;
}

// --- WS1: Time & Trends ---
export interface TrendRatePoint { x: string; numerator: number; denominator: number; rate: number | null }
export interface TrendCountPoint { x: string; value: number }
export interface TrendMetric {
  kind: "count" | "rate";
  label: string;
  invert?: boolean;
  points: (TrendRatePoint | TrendCountPoint)[];
}
export interface Trends {
  bucket: "month" | "week";
  buckets: string[];
  metrics: Record<string, TrendMetric>;
  deltas: Record<string, number | null>;
  access_level: string;
}
export const getTrends = (bucket: "month" | "week" = "month", from?: string, to?: string) =>
  apiGet<Trends>(`/trends?bucket=${bucket}${from ? `&from=${from}` : ""}${to ? `&to=${to}` : ""}`);

// --- WS2: Benchmarking & Equity ---
export interface MetricDef { key: string; kind: "count" | "rate"; label: string; invert?: boolean }
export interface LeagueRowData {
  facility_id: string; name: string; region: string;
  value: number | null; numerator: number; denominator: number | null; rate: number | null; low_confidence: boolean;
}
export interface Benchmarking {
  metric: string; kind: "count" | "rate"; label: string;
  rows: LeagueRowData[]; available_metrics: MetricDef[]; access_level: string;
}
export interface GeoArea {
  area_id: string; name: string; value: number | null; numerator: number; denominator: number | null; rate: number | null; low_confidence: boolean;
}
export interface GeoRollup { metric: string; level: "state" | "lga"; kind: "count" | "rate"; label: string; areas: GeoArea[] }
export interface EquityBand { band: string; contacts: number; screening_coverage: Ratio; intervention_coverage: Ratio }
export interface Equity { dimension: string; bands: EquityBand[] }

export const getBenchmarking = (metric = "deliveries") => apiGet<Benchmarking>(`/benchmarking?metric=${metric}`);
export const getGeo = (metric = "deliveries", level: "state" | "lga" = "state") =>
  apiGet<GeoRollup>(`/geo?metric=${metric}&level=${level}`);
export const getEquity = () => apiGet<Equity>("/equity");

export const getWorkspace = () => apiGet<Workspace>("/workspace");
export const getSummary = (from?: string, to?: string) =>
  apiGet<Summary>(`/maternal-summary${from || to ? `?from=${from ?? ""}&to=${to ?? ""}` : ""}`);
export const getFacilitiesOverview = () =>
  apiGet<{ facilities: FacilityRow[]; stale_days: number }>("/facilities-overview");
export const getRecords = (page = 1) =>
  apiGet<{ results: RecordRow[]; count: number; page: number; page_size: number; access_level: string }>(
    `/records?page=${page}`,
  );
