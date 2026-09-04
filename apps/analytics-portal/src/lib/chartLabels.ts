import { formatBoolean } from "@/lib/format";

/** A chart category, rendered as the table would render the same cell. */
export function categoryLabel(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return formatBoolean(value);
  return String(value);
}
