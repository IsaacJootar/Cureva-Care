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
  scope_breakdown?: { facilities: number; wards: number; lgas: number; states: number };
  facilities: { id: string; name: string; region: string; ward?: string; lga?: string; state?: string }[];
  summary: Summary;
}

export interface FacilityRow {
  id: string;
  name: string;
  region: string;
  ward?: string;
  lga?: string;
  state?: string;
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
export interface GeoRollup { metric: string; level: "ward" | "lga" | "state"; kind: "count" | "rate"; label: string; areas: GeoArea[] }
export interface EquityBand { band: string; contacts: number; screening_coverage: Ratio; intervention_coverage: Ratio }
export interface Equity { dimension: string; bands: EquityBand[] }

export const getBenchmarking = (metric = "deliveries") => apiGet<Benchmarking>(`/benchmarking?metric=${metric}`);
export const getGeo = (metric = "deliveries", level: "ward" | "lga" | "state" = "state") =>
  apiGet<GeoRollup>(`/geo?metric=${metric}&level=${level}`);
export const getEquity = () => apiGet<Equity>("/equity");

// --- WS3: Continuum & cohorts ---
export interface FunnelStep { label: string; value: number; drop_from_previous: number; share_of_booked: number | null }
export interface CareFunnel { steps: FunnelStep[]; total: number; access_level: string }
export interface DropoffRow {
  episode_id: string; woman: { internal_id: string; name: string } | null; woman_internal_id: string;
  booking_date: string | null; anc_contacts: number; delivered_on: string | null; days_since: number | null;
}
export interface Dropoff { kind: string; label: string; count: number; rows: DropoffRow[]; available_kinds: { key: string; label: string }[]; access_level: string }
export interface CohortSeries { label: string; points: TrendRatePoint[] }
export interface Cohorts { cohorts: string[]; series: Record<string, CohortSeries>; access_level: string }

export const getContinuumFunnel = () => apiGet<CareFunnel>("/continuum/funnel");
export const getDropoff = (kind: string) => apiGet<Dropoff>(`/continuum/dropoff?kind=${kind}`);
export const getCohorts = () => apiGet<Cohorts>("/continuum/cohorts");

// --- WS4: MPDSR severe-outcome surveillance ---
export interface SevereCase {
  episode_id: string | null; birth_event_id: string; woman: { internal_id: string; name: string } | null;
  woman_internal_id: string; facility: string; region: string; delivery_date: string | null;
  outcomes: string[]; antenatal_risk: string[]; mode_of_delivery: string | null; attendant: string | null;
}
export interface SevereCases { count: number; by_type: Record<string, number>; cases: SevereCase[]; access_level: string }
export interface TimelineEvent { date: string | null; type: string; summary: string; severe?: string[] }
export interface CaseTimeline { episode_id: string; events: TimelineEvent[] }
export interface SevereTrend { buckets: string[]; series: Record<string, TrendCountPoint[]> }
export interface ClusterRow { facility_id: string; name: string; region: string; severe: number; deliveries: number; rate: number | null }
export interface Clusters { facilities: ClusterRow[] }

export const getSevereCases = () => apiGet<SevereCases>("/surveillance/cases");
export const getCaseTimeline = (episodeId: string) => apiGet<CaseTimeline>(`/surveillance/cases/${episodeId}`);
export const getSevereTrend = () => apiGet<SevereTrend>("/surveillance/trend");
export const getClusters = () => apiGet<Clusters>("/surveillance/clusters");

// --- WS5: Risk intelligence & early-warning ---
export interface RiskPyramid { tiers: Record<string, number>; total: number; ruleset_version?: number; clinical_owner?: string }
export interface RiskRow {
  episode_id: string; tier: string; markers: string[]; woman: { internal_id: string; name: string } | null;
  woman_internal_id: string; booking_date: string | null; last_anc: string | null; days_since_anc: number | null;
}
export interface RiskRegistry { rows: RiskRow[]; count: number; access_level: string; ruleset_version?: number; clinical_owner?: string }
export interface AlertItem { kind: string; severity: "high" | "medium" | "low"; title: string; detail: string; facility_id: string | null; threshold: number }
export interface Alerts { alerts: AlertItem[] }

export const getRiskPyramid = () => apiGet<RiskPyramid>("/risk/pyramid");
export const getRiskRegistry = (tier?: string) => apiGet<RiskRegistry>(`/risk/registry${tier ? `?tier=${tier}` : ""}`);
export const getAlerts = () => apiGet<Alerts>("/alerts");

// --- WS6: RDQA-as-a-service ---
export interface RdqaCard {
  facility_id: string; name: string; region: string; rows: number;
  avg_extraction_confidence: number | null; completeness: number | null; implausible_rate: number | null;
  open_template_flags: number; avg_days_to_publish: number | null; score: number | null;
}
export interface RdqaScorecard {
  facilities: RdqaCard[];
  overall: { facilities_assessed?: number; mean_score?: number | null; mean_confidence?: number | null; total_open_flags?: number };
}
export interface RdqaTrend { points: TrendRatePoint[] }

export const getRdqaScorecard = () => apiGet<RdqaScorecard>("/rdqa/scorecard");
export const getRdqaTrend = () => apiGet<RdqaTrend>("/rdqa/trend");

export const getWorkspace = () => apiGet<Workspace>("/workspace");
export const getSummary = (from?: string, to?: string) =>
  apiGet<Summary>(`/maternal-summary${from || to ? `?from=${from ?? ""}&to=${to ?? ""}` : ""}`);
export const getFacilitiesOverview = () =>
  apiGet<{ facilities: FacilityRow[]; stale_days: number }>("/facilities-overview");
export const getRecords = (page = 1) =>
  apiGet<{ results: RecordRow[]; count: number; page: number; page_size: number; access_level: string }>(
    `/records?page=${page}`,
  );
