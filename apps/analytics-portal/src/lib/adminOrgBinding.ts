/**
 * An admin administers every client and carries no organization of their own; the API
 * refuses an account that is both (api/auth/service.py ADMIN_ORG_ERROR). These keep the
 * panel from ever composing that request.
 */

export function organizationForRole(
  role: string,
  organizationId: string | null | undefined,
): string | null {
  if (role === "admin") return null;
  return organizationId?.trim() ? organizationId : null;
}

/**
 * The patch for a role change. Promotion must clear the organization in the SAME
 * request: sending `{role: "admin"}` alone leaves the old client attached, which is
 * how the forbidden account got created in the first place.
 */
export function rolePatch(role: string): { role: string; organization_id?: null } {
  return role === "admin" ? { role, organization_id: null } : { role };
}
