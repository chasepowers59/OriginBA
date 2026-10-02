import { formatBoolean } from "@/lib/format";

/** A chart category: a boolean as the table renders it, a missing one in words (UI-15). */
export function categoryLabel(value: unknown): string {
  if (value == null || value === "") return "Not recorded";
  if (typeof value === "boolean") return formatBoolean(value);
  return String(value);
}

/**
 * A time-axis tick, kept to fifteen characters and an ellipsis so a dozen months fit;
 * the one tick that must say more (the bucket a window cuts short, "Jun 2026 (to Jun 2,
 * 2026)") is shown whole, since that qualifier is what the chart is saying.
 */
export function tickText(label: string, { whole = false }: { whole?: boolean } = {}): string {
  if (whole || label.length <= 16) return label;
  return `${label.slice(0, 15)}…`;
}
