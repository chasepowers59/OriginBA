import { canvasOpensOnAllDates } from "@/lib/datePresets";
import type { DatePresetConfig } from "@/lib/types";

type DateFieldSource = {
  default_date_field?: string | null;
  date_fields?: { id: string }[] | null;
  default_date_preset?: DatePresetConfig | string;
};

/**
 * The date a canvas works in: the MEASURED default, then the first declared date.
 *
 * Every canvas with a date declares `default_date_field`, chosen by
 * build_data_dictionary from pg_stats.null_frac so it is populated on at least 90% of
 * rows — the same column the warehouse indexes and the server windows on. So the
 * answer is only ever null when the canvas genuinely has no date at all.
 *
 * This is the ONE resolver. The explorer's date presets, the dashboard's day window
 * and a tile's time grain all key off it; when two of them keyed off a retired
 * mandatory-window field instead, "Prior month" changed state and sent no filter.
 */
export function resolveDateField(meta: DateFieldSource | undefined | null): string | null {
  if (!meta) return null;
  return meta.default_date_field || meta.date_fields?.[0]?.id || null;
}

/**
 * The date a dashboard's "last N days" applies on, or null when it must not apply: a
 * canvas of what exists now (accounts, agreements, meters) and a backlog report count
 * every row whatever its date, or the window quietly turns "accounts on budget" into
 * "accounts opened this month".
 */
export function tileWindowField(
  meta: DateFieldSource | undefined | null,
  report: { all_dates?: boolean } | null | undefined,
): string | null {
  if (canvasOpensOnAllDates(meta?.default_date_preset) || report?.all_dates) return null;
  return resolveDateField(meta);
}
