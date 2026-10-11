// Identity-review API helpers (Facility lead). cureva-docs/02, 05.
import { apiGet, apiPost } from "./api";

export interface IdentityCandidate {
  id: string;
  confidence: string; // decimal as string
  matched_fields: Record<string, number | boolean>;
  status: string;
  created_at: string;
  new_record: {
    source_row_id: string;
    intake_id: string;
    register_family: string;
    row_number: number;
    values: Record<string, unknown>;
    service_date: string | null;
  };
  candidate: {
    woman_id: string;
    internal_id: string;
    name: string | null;
    stable_identifier: string | null;
    phone: string | null;
  };
}

export const listCandidates = () => apiGet<IdentityCandidate[]>("/identity-candidates");
export const confirmCandidate = (id: string) => apiPost(`/identity-candidates/${id}/confirm`);
export const rejectCandidate = (id: string) => apiPost(`/identity-candidates/${id}/reject`);
