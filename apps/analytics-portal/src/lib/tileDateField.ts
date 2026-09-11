type DateFieldSource = {
  default_date_field?: string | null;
  date_fields?: { id: string }[] | null;
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
