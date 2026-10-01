/** Row-level security as the interface sees it (the rules and their enforcement: api/row_security.py). */

export type RowRule = { field: string; values: string[] };

/** Pages the portal cannot restrict to a person's rows: free SQL, and letters (refused by the API). */
const UNRESTRICTABLE = new Set(["database", "dq", "letters", "forecasts"]);

export function isRestricted(user: { row_rules?: RowRule[] | null } | null | undefined): boolean {
  return Boolean(user?.row_rules?.length);
}

/** The pages to offer: none a person's row rules cannot cover, none behind a permission they
 *  lack, none the client does not use (portal config "modules"). A list of permissions means
 *  any one of them opens the page. */
export function visibleNav<T extends { id: string; permission?: string | readonly string[] }>(
  items: T[],
  user: { row_rules?: RowRule[] | null } | null,
  can: (permission: string) => boolean = () => true,
  modules?: Record<string, boolean>,
): T[] {
  const restricted = isRestricted(user);
  const allowed = (p: T["permission"]) => !p || (typeof p === "string" ? can(p) : p.some(can));
  return items.filter((i) => !(restricted && UNRESTRICTABLE.has(i.id)) && allowed(i.permission)
    && modules?.[i.id] !== false);
}

export function describeRules(rules: RowRule[] | null | undefined): string {
  if (!rules?.length) return "All rows";
  return rules.map((r) => `${r.field} is ${r.values.join(" or ")}`).join("; ");
}

export function parseRuleInput(field: string, values: string): RowRule[] {
  const vs = values.split(",").map((v) => v.trim()).filter(Boolean);
  return field.trim() && vs.length ? [{ field: field.trim(), values: vs }] : [];
}
