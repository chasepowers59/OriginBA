import type { PortalRole } from "@/lib/auth";

export type SettingsTab = "connection" | "access" | "packs" | "health";

/** The Settings tabs a person may open. A client admin (api/auth/permissions.py) manages
 *  their client's users and groups and nothing platform-wide: connection, content packs
 *  and system health belong to the platform admin. */
export function settingsTabs(can: (permission: string) => boolean): SettingsTab[] {
  const platform = can("settings:manage");
  return (["connection", "access", "packs", "health"] as const).filter((tab) =>
    tab === "access" ? can("users:manage") : platform);
}

/** The roles a person may give, mirroring can_assign_role in api/auth/permissions.py. */
export function assignableRoles(role: PortalRole | undefined): PortalRole[] {
  if (role === "admin") return ["user", "editor", "client_admin", "admin"];
  if (role === "client_admin") return ["user", "editor", "client_admin"];
  return [];
}
