// Shared API types, mirroring the Django serializers (identity_access).

export type Role =
  | "data_officer"
  | "facility_lead"
  | "organisation_user"
  | "systems_admin";

export type ThemePreference = "light" | "dark" | "system";
export type AccessLevel = "aggregate" | "de_identified" | "identifiable";
export type ScopeType = "facility" | "ward" | "local_government" | "state";

export interface CurrentUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  facility: string | null;
  facility_name?: string | null;
  organisation: string | null;
  organisation_name?: string | null;
  can_manage_org_users: boolean;
  theme_preference: ThemePreference;
}

export interface GeoState {
  id: string;
  name: string;
}
export interface LocalGovernment {
  id: string;
  name: string;
  state: string;
}
export interface Ward {
  id: string;
  name: string;
  local_government: string;
}

export interface Facility {
  id: string;
  name: string;
  facility_type: string | null;
  is_active: boolean;
  ward: string;
  ward_name?: string;
  local_government_name?: string;
  state_name?: string;
  created_at?: string;
}

export interface FacilityAccessGrant {
  id: string;
  organisation: string;
  scope_type: ScopeType;
  scope_id: string;
  access_level: AccessLevel;
  scope_label: string | null;
  granted_at: string;
}

export interface Organisation {
  id: string;
  name: string;
  org_type: string | null;
  is_active: boolean;
  facility_access: FacilityAccessGrant[];
  active_user_count: number;
  access_summary: string;
  created_at: string;
}
