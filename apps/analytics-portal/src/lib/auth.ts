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
