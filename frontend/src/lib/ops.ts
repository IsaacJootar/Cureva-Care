// Operations API helpers (settings, notification prefs, user management).
import { apiDelete, apiGet, apiPatch, apiPost } from "./api";
import type { CurrentUser, IntelModule, Role, SubscriptionTier } from "./types";

export interface PlatformSetting {
  key: string;
  value: number | string | boolean;
  value_type: "integer" | "decimal" | "boolean" | "string";
  description: string;
  default: number | string | boolean;
  updated_at: string;
}

export interface NotificationPref {
  id: string;
  notification_type: string;
  channel: "email" | "sms" | "email_and_sms" | "none";
  updated_at: string;
}

// Subscription tiers (intelligence module bundles) — Systems admin only.
export const listTiers = () =>
  apiGet<{ modules: IntelModule[]; tiers: SubscriptionTier[] }>("/tiers");
export const updateTier = (
  id: string,
  body: { modules?: string[]; name?: string; order?: number },
) => apiPatch<SubscriptionTier>(`/tiers/${id}`, body);

export const listSettings = () => apiGet<PlatformSetting[]>("/settings");
export const updateSetting = (key: string, value: unknown) =>
  apiPatch<PlatformSetting>(`/settings/${key}`, { value });

export const getNotificationPrefs = (userId: string) =>
  apiGet<NotificationPref[]>(`/users/${userId}/notification-preferences`);
export const updateNotificationPref = (userId: string, type: string, channel: string) =>
  apiPatch<NotificationPref>(`/users/${userId}/notification-preferences/${type}`, { channel });

// /users is a DRF ViewSet and comes back paginated ({ count, results }); other
// callers (facilities, organisations) unwrap the same way. Always hand back an array.
export const listUsers = async (): Promise<CurrentUser[]> => {
  const data = await apiGet<{ results?: CurrentUser[] } | CurrentUser[]>("/users");
  return Array.isArray(data) ? data : (data.results ?? []);
};
export const createUser = (body: { name: string; email: string; role: Role; facility?: string | null; password?: string }) =>
  apiPost<CurrentUser & { initial_password: string | null }>("/users", body);
export const changePassword = (current_password: string, new_password: string) =>
  apiPost<{ detail: string }>("/auth/change-password", { current_password, new_password });
export const adminSetPassword = (userId: string, password?: string) =>
  apiPost<{ status: string; initial_password: string | null }>(`/users/${userId}/set-password`, password ? { password } : {});
export const editUser = (id: string, body: { name?: string; role?: Role }) =>
  apiPatch<CurrentUser>(`/users/${id}`, body);
export const deactivateUser = (id: string) => apiPost(`/users/${id}/deactivate`);
export const reactivateUser = (id: string) => apiPost(`/users/${id}/reactivate`);
export const deleteOrgUser = (orgId: string, userId: string) =>
  apiDelete(`/organisations/${orgId}/users/${userId}`);
