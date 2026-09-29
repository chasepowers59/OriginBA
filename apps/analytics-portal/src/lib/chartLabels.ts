import { formatBoolean } from "@/lib/format";

/** A chart category: a boolean as the table renders it, a missing one in words (UI-15). */
export function categoryLabel(value: unknown): string {
  if (value == null || value === "") return "Not recorded";
  if (typeof value === "boolean") return formatBoolean(value);
  return String(value);
}
