export type PortalRole = "user" | "editor" | "admin";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  role: PortalRole;
  client_id: string;
  organization_id: string | null;
  organization_name: string | null;
  is_active: boolean;
  must_change_password: boolean;
  workstreams: string[];
  permissions: string[];
  group_ids: string[];
  group_names: string[];
};

export type PortalOrganization = {
  id: string;
  display_name: string;
};

export type AuthStatus = {
  enabled: boolean;
  authenticated: boolean;
  /** True when the API is configured for OIDC single sign-on (Azure AD / Entra). */
  oidc_enabled?: boolean;
};

export type AccessGroup = {
  id: string;
  name: string;
  description: string;
  client_id: string;
  workstreams: string[];
  member_count: number;
};

const TOKEN_KEY = "portal_access_token";
const SESSION_COOKIE = "portal_session";
const TOKEN_COOKIE = "portal_access_token";

export function authDisabled(): boolean {
  return process.env.NEXT_PUBLIC_PORTAL_AUTH_DISABLED === "true";
}

export function getAccessToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(TOKEN_KEY) ?? "";
}

function cookieFlags(maxAgeSeconds: number): string {
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "; Secure"
      : "";
  return `; path=/; max-age=${maxAgeSeconds}; SameSite=Lax${secure}`;
}

export function storeAccessToken(token: string, maxAgeSeconds = 48 * 3600): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(TOKEN_KEY, token);
  document.cookie = `${SESSION_COOKIE}=1${cookieFlags(maxAgeSeconds)}`;
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}${cookieFlags(maxAgeSeconds)}`;
}

export function clearAccessToken(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(TOKEN_KEY);
  document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function hasPermission(user: AuthUser | null, permission: string): boolean {
  if (!user) return authDisabled();
  return user.permissions.includes(permission);
}

export function roleLabel(role: PortalRole): string {
  const labels: Record<PortalRole, string> = {
    user: "User",
    editor: "Editor",
    admin: "Admin",
  };
  return labels[role] ?? role;
}

/** The tenant an admin is currently viewing.
 *
 * A COOKIE, not sessionStorage. This app server-renders its pages, and a server render
 * cannot see sessionStorage -- so the first paint used the admin's HOME tenant while
 * every client-side fetch used the switched one. The header said DEV and the page below
 * it was still listing CityCorp's processes, with no error anywhere to explain it.
 *
 * A session cookie is visible to both halves and still disappears when the browser
 * closes, which is the property that matters: this is a VIEW, not an assignment, and it
 * must not outlive the session. The API ignores the header for anyone who is not an
 * admin, so a stale cookie can never widen what a non-admin sees.
 */
const ACTIVE_ORG_KEY = "portal_active_organization";

export function getActiveOrganization(): string | null {
  if (typeof document === "undefined") return null;
  const hit = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${ACTIVE_ORG_KEY}=`));
  return hit ? decodeURIComponent(hit.split("=")[1]) : null;
}

export function setActiveOrganization(orgId: string | null): void {
  if (typeof document === "undefined") return;
  document.cookie = orgId
    ? `${ACTIVE_ORG_KEY}=${encodeURIComponent(orgId)}; path=/; SameSite=Lax`
    : `${ACTIVE_ORG_KEY}=; path=/; Max-Age=0; SameSite=Lax`;
}

export function activeOrganizationHeader(): Record<string, string> {
  const org = getActiveOrganization();
  return org ? { "X-Organization-Id": org } : {};
}
