/** Row-level security as the interface sees it (the rules and their enforcement: api/row_security.py). */

export type RowRule = { field: string; values: string[] };

/** Pages that run SQL the portal cannot restrict to a person's rows. */
const UNRESTRICTABLE = new Set(["database", "dq"]);

export function isRestricted(user: { row_rules?: RowRule[] | null } | null | undefined): boolean {
  return Boolean(user?.row_rules?.length);
}

export function visibleNav<T extends { id: string }>(items: T[], user: { row_rules?: RowRule[] | null } | null): T[] {
  return isRestricted(user) ? items.filter((i) => !UNRESTRICTABLE.has(i.id)) : items;
}

export function describeRules(rules: RowRule[] | null | undefined): string {
  if (!rules?.length) return "All rows";
  return rules.map((r) => `${r.field} is ${r.values.join(" or ")}`).join("; ");
}

export function parseRuleInput(field: string, values: string): RowRule[] {
  const vs = values.split(",").map((v) => v.trim()).filter(Boolean);
  return field.trim() && vs.length ? [{ field: field.trim(), values: vs }] : [];
}
