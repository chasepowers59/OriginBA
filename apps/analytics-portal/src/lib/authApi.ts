import type { AccessGroup, AuthStatus, AuthUser, PortalOrganization } from "@/lib/auth";
import { authHeaders, clearAccessToken, setActiveOrganization, storeAccessToken } from "@/lib/auth";
import { parseApiError } from "@/lib/apiErrors";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(parseApiError(detail, res.statusText));
  }
  return res.json() as Promise<T>;
}

export function fetchAuthStatus(): Promise<AuthStatus> {
  return authFetch<AuthStatus>("/auth/status", { headers: authHeaders() });
}

export function fetchCurrentUser(): Promise<AuthUser> {
  return authFetch<AuthUser>("/auth/me");
}

export async function login(
  email: string,
  password: string,
  organization?: string | null,
): Promise<AuthUser> {
  const res = await authFetch<{
    access_token: string;
    expires_in_minutes: number;
    user: AuthUser;
    active_organization_id?: string | null;
  }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, ...(organization ? { organization } : {}) }),
  });
  storeAccessToken(res.access_token, res.expires_in_minutes * 60);
  // Bind the session to the org the server authorized (the tenant for an admin entering
  // a client, otherwise the user's home org).
  if (res.active_organization_id) setActiveOrganization(res.active_organization_id);
  return res.user;
}

/** Public single-tenant lookup for the /<slug> login page. Throws if the slug is unknown. */
export function resolveTenant(slug: string): Promise<PortalOrganization> {
  return authFetch<PortalOrganization>(`/auth/tenants/${encodeURIComponent(slug)}`);
}

export function logout(): void {
  clearAccessToken();
}

export function changePassword(current_password: string, new_password: string): Promise<AuthUser> {
  return authFetch<AuthUser>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });
}

export function listPortalOrganizations(): Promise<PortalOrganization[]> {
  return authFetch<PortalOrganization[]>("/auth/organizations");
}

export function listPortalUsers(): Promise<AuthUser[]> {
  return authFetch<AuthUser[]>("/auth/users");
}

export function createPortalUser(body: {
  email: string;
  display_name: string;
  password: string;
  role: string;
  organization_id?: string | null;
  group_ids: string[];
  is_active: boolean;
}): Promise<AuthUser> {
  return authFetch<AuthUser>("/auth/users", { method: "POST", body: JSON.stringify(body) });
}

export function updatePortalUser(
  userId: string,
  body: Partial<{
    display_name: string;
    role: string;
    organization_id: string | null;
    group_ids: string[];
    is_active: boolean;
    password: string;
  }>,
): Promise<AuthUser> {
  return authFetch<AuthUser>(`/auth/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function listAccessGroups(): Promise<AccessGroup[]> {
  return authFetch<AccessGroup[]>("/auth/groups");
}

export function createAccessGroup(body: {
  name: string;
  description: string;
  workstreams: string[];
}): Promise<AccessGroup> {
  return authFetch<AccessGroup>("/auth/groups", { method: "POST", body: JSON.stringify(body) });
}

export function updateAccessGroup(
  groupId: string,
  body: Partial<{ name: string; description: string; workstreams: string[] }>,
): Promise<AccessGroup> {
  return authFetch<AccessGroup>(`/auth/groups/${groupId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteAccessGroup(groupId: string): Promise<{ deleted: string }> {
  return authFetch<{ deleted: string }>(`/auth/groups/${groupId}`, { method: "DELETE" });
}

export type AuditEvent = {
  id: string;
  actor_email: string;
  action: string;
  target_type: string;
  target_id: string;
  detail: string;
  created_at: string | null;
};

export function listAuditEvents(limit = 50): Promise<AuditEvent[]> {
  return authFetch<AuditEvent[]>(`/auth/audit-log?limit=${limit}`);
}
