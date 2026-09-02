/**
 * Wire names from api/auth/service.py ADMIN_AUDIT_ACTIONS, rendered for a reader. The
 * fallback matters as much as the map: when a new action is added server-side this
 * feed should still say something in English rather than leaking the identifier.
 */
const LABELS: Record<string, string> = {
  "user.create": "User created",
  "user.update": "User updated",
  "user.password_change": "Password changed",
  "group.create": "Access group created",
  "group.update": "Access group updated",
  "group.delete": "Access group deleted",
  sso_jit_provision: "Account provisioned by SSO",
  sql_refused: "SQL blocked",
};

export function auditActionLabel(action: string): string {
  const key = (action ?? "").trim();
  if (!key) return "Unknown action";
  if (LABELS[key]) return LABELS[key];
  const words = key.replace(/[._]+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Unknown action";
}
