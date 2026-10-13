// Needs-attention worklist API (Facility lead only). cureva-docs/05, 06.
import { apiGet, apiPost } from "./api";

export interface WorklistItem {
  item_id: string;
  rule_key: string;
  label: string;
  severity: "high" | "medium" | "low";
  clinical_owner: string;
  subject_type: string;
  subject_id: string;
  woman: { internal_id: string; name: string | null } | null;
  reason: string;
  days_open: number | null;
  last_actioned: { by: string; at: string; note: string | null } | null;
}

export const getWorklist = () => apiGet<{ items: WorklistItem[] }>("/worklists");
export const actionItem = (itemId: string, note: string, subjectType: string) =>
  apiPost(`/worklists/${encodeURIComponent(itemId)}/action`, { note, subject_type: subjectType });
