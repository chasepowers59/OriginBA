/** Who owns a saved view or dashboard, as the reader sees it (the rules: api/ownership.py). */

export type Visibility = "organization" | "private";

export function ownershipLabel(item: { visibility?: Visibility; ownerEmail?: string | null }, me?: string | null): string {
  if (item.visibility === "private") return "Private";
  if (!item.ownerEmail) return "";
  return item.ownerEmail === me ? "Shared with your organization" : `Shared by ${item.ownerEmail}`;
}
