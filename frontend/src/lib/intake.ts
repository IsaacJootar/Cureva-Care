// Intake API helpers for the Data officer screens (cureva-docs/03, 05).
import { API_BASE, apiGet, apiPost, tokenStore } from "./api";
import type { Facility } from "./types";

export type RegisterFamily = "ANC" | "Delivery" | "PNC";

export interface Intake {
  id: string;
  facility: string;
  facility_name: string;
  register_family: RegisterFamily;
  status: string;
  suspected_register_family: string | null;
  register_mismatch_status: string;
  batch_period_from: string;
  batch_period_to: string;
  received_at: string;
  published_at: string | null;
  row_count: number;
  page_count: number;
}

export interface SourceRow {
  id: string;
  row_number: number;
  raw_payload: Record<string, unknown>;
  normalized: Record<string, unknown> | null;
  service_date: string | null;
  status: string;
  flags: Record<string, { kind: string; message: string; raw: unknown }> | null;
  extraction_confidence: Record<string, number>;
  confirmed_fields: string[];
  unmatched_labels: string[];
  needs_confirmation: string[];
  always_confirm: string[];
}

export interface IntakePage {
  page_number: number;
  url: string | null;
}

export type ProgressEvent =
  | { type: "start"; total_fields: number; register_family: string }
  | { type: "field"; field: string; label: string; state: "reading" | "matched" | "pending" }
  | { type: "mismatch"; declared: string; suspected: string }
  | { type: "done"; row_count: number; matched: number; needs_mapping: string[] }
  | { type: "extraction_failed" };

export async function listFacilities(): Promise<Facility[]> {
  const data = await apiGet<{ results?: Facility[] } | Facility[]>("/facilities");
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function createIntake(form: {
  facility: string;
  register_family: RegisterFamily;
  batch_period_from: string;
  batch_period_to: string;
  source_label: string;
  files: File[];
}): Promise<Intake & { detail?: string }> {
  const fd = new FormData();
  fd.append("facility", form.facility);
  fd.append("register_family", form.register_family);
  fd.append("batch_period_from", form.batch_period_from);
  fd.append("batch_period_to", form.batch_period_to);
  fd.append("source_label", form.source_label);
  form.files.forEach((f) => fd.append("images", f));

  const res = await fetch(`${API_BASE}/intakes`, {
    method: "POST",
    headers: { Authorization: `Bearer ${tokenStore.access}` },
    body: fd,
  });
  const data = await res.json();
  if (!res.ok && res.status !== 200) throw new Error(data.detail ?? "Upload failed");
  return data;
}

// Consume the SSE progress stream with fetch (so the JWT is in the header).
export async function streamProgress(intakeId: string, onEvent: (e: ProgressEvent) => void): Promise<void> {
  const res = await fetch(`${API_BASE}/intakes/${intakeId}/progress`, {
    headers: { Authorization: `Bearer ${tokenStore.access}` },
  });
  if (!res.body) throw new Error("No stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)) as ProgressEvent);
    }
  }
}

export const getRows = (intakeId: string) => apiGet<SourceRow[]>(`/intakes/${intakeId}/rows`);
export const getPages = (intakeId: string) => apiGet<IntakePage[]>(`/intakes/${intakeId}/pages`);
export const confirmField = (intakeId: string, rowId: string, field: string, correct: boolean, value?: unknown) =>
  apiPost<SourceRow>(`/intakes/${intakeId}/rows/${rowId}/confirm-field`, { field, correct, value });
export const publishIntake = (intakeId: string) => apiPost(`/intakes/${intakeId}/publish`);
export const resolveMismatch = (intakeId: string, action: "confirm_declared" | "switch") =>
  apiPost(`/intakes/${intakeId}/resolve-register-mismatch`, { action });
export const flagIntake = (intakeId: string, note: string) => apiPost(`/intakes/${intakeId}/flag`, { note });
export const myIntakes = (facilityId: string) => apiGet<Intake[]>(`/my-intakes?facility=${facilityId}`);
