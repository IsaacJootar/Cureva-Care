// API client for the Django backend. The Next.js app is a decoupled SPA that
// authenticates with a JWT access+refresh pair (cureva-docs/04,05). Tokens are
// kept in localStorage; a single transparent refresh is attempted on a 401.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

const ACCESS_KEY = "cv-access";
const REFRESH_KEY = "cv-refresh";

export const tokenStore = {
  get access() {
    try {
      return localStorage.getItem(ACCESS_KEY);
    } catch {
      return null;
    }
  },
  get refresh() {
    try {
      return localStorage.getItem(REFRESH_KEY);
    } catch {
      return null;
    }
  },
  set(access: string, refresh?: string) {
    try {
      localStorage.setItem(ACCESS_KEY, access);
      if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    } catch {
      /* storage unavailable (private mode) — session is in-memory only */
    }
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
  },
};

export class ApiError extends Error {
  status: number;
  data: unknown;
  constructor(status: number, data: unknown) {
    super(typeof data === "object" && data && "detail" in data ? String((data as { detail: unknown }).detail) : `Request failed (${status})`);
    this.status = status;
    this.data = data;
  }
}

async function rawFetch(path: string, init: RequestInit, withAuth: boolean): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (withAuth && tokenStore.access) {
    headers.set("Authorization", `Bearer ${tokenStore.access}`);
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

async function tryRefresh(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await rawFetch(
    "/auth/token/refresh",
    { method: "POST", body: JSON.stringify({ refresh }) },
    false,
  );
  if (!res.ok) return false;
  const data = (await res.json()) as { access?: string };
  if (!data.access) return false;
  tokenStore.set(data.access);
  return true;
}

export interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  auth?: boolean;
}

export async function api<T = unknown>(path: string, opts: ApiOptions = {}): Promise<T> {
  const { body, auth = true, ...rest } = opts;
  const init: RequestInit = {
    ...rest,
    body: body === undefined ? undefined : JSON.stringify(body),
  };

  let res = await rawFetch(path, init, auth);

  if (res.status === 401 && auth && tokenStore.refresh) {
    if (await tryRefresh()) {
      res = await rawFetch(path, init, auth);
    }
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("Content-Type") ?? "";
  const payload = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    throw new ApiError(res.status, payload);
  }
  return payload as T;
}

export const apiGet = <T = unknown>(path: string, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "GET" });
export const apiPost = <T = unknown>(path: string, body?: unknown, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "POST", body });
export const apiPatch = <T = unknown>(path: string, body?: unknown, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "PATCH", body });
export const apiPut = <T = unknown>(path: string, body?: unknown, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "PUT", body });
export const apiDelete = <T = unknown>(path: string, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "DELETE" });
