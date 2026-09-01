type DateFieldSource = {
  required_date_field?: string | null;
  default_date_field?: string | null;
  date_fields?: { id: string }[] | null;
};

/**
 * The date a tile should group by when it asks for a time grain.
 *
 * `required_date_field` is a CISADM-era notion -- a snapshot too large to scan without
 * a date filter -- and no dbt canvas sets one. Keying the time dimension off it alone
 * meant every "by month" tile on the dbt path quietly lost its grouping and charted a
 * single aggregate against itself. Every canvas carries `default_date_field`, so the
 * answer is only ever null when the canvas really has no date at all.
 */
export function resolveTileDateField(meta: DateFieldSource | undefined | null): string | null {
  if (!meta) return null;
  return (
    meta.required_date_field || meta.default_date_field || meta.date_fields?.[0]?.id || null
  );
}
