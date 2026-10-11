// Template + mapping API helpers (Systems admin). cureva-docs/03, 05.
import { apiGet, apiPost } from "./api";
import type { RegisterFamily } from "./intake";

export interface TemplateColumn {
  canonical_field: string;
  label: string;
  type: string;
  required?: boolean;
  aliases: string[];
  enum_values?: string[];
  plausible_range?: string;
}

export interface Template {
  id: string;
  register_family: RegisterFamily;
  facility: string | null;
  facility_name: string | null;
  version: number;
  effective_date: string;
  is_active: boolean;
  schema: { columns: TemplateColumn[] };
  column_count: number;
  created_at: string;
}

export interface TemplateFlag {
  id: string;
  intake: string;
  facility_name: string;
  register_family: RegisterFamily;
  flagged_by_name: string;
  note: string | null;
  created_at: string;
}

export interface MappingData {
  template_id: string | null;
  register_family: RegisterFamily;
  facility_name: string;
  unmatched_labels: string[];
  canonical_fields: { canonical_field: string; label: string }[];
  open_flags: { id: string; note: string | null }[];
}

export const listTemplates = (family?: RegisterFamily) =>
  apiGet<Template[]>(`/templates${family ? `?register_family=${family}` : ""}`);
export const listTemplateFlags = () => apiGet<TemplateFlag[]>("/template-flags");
export const getMapping = (intakeId: string) => apiGet<MappingData>(`/intakes/${intakeId}/mapping`);
export const addAlias = (templateId: string, canonical_field: string, alias: string) =>
  apiPost<Template>(`/templates/${templateId}/aliases`, { canonical_field, alias });
