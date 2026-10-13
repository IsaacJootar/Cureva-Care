// Reports API (Facility lead + Organisation user). cureva-docs/05, 06.
import { API_BASE, apiGet, apiPost, tokenStore } from "./api";

export interface ReportSummary {
  id: string;
  title: string;
  period_from: string | null;
  period_to: string | null;
  has_narrative: boolean;
  created_at: string;
}

export interface ReportDetail extends ReportSummary {
  sections: Record<string, unknown>;
  narrative: string | null;
}

export const listReports = () => apiGet<ReportSummary[]>("/reports");
export const generateReport = (body: { title?: string; with_narrative?: boolean }) =>
  apiPost<ReportDetail>("/reports", body);
export const getReport = (id: string) => apiGet<ReportDetail>(`/reports/${id}`);

// CSV export — fetch with the auth header, then save as a file.
export async function downloadRecordsCsv(): Promise<"ok" | "forbidden" | "error"> {
  const res = await fetch(`${API_BASE}/records/export`, {
    headers: { Authorization: `Bearer ${tokenStore.access}` },
  });
  if (res.status === 403) return "forbidden";
  if (!res.ok) return "error";
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "cureva-records.csv";
  a.click();
  URL.revokeObjectURL(url);
  return "ok";
}
