type DateScopeSource = {
  required_date_field?: string | null;
  required_date_label?: string | null;
  default_date_field?: string | null;
  date_fields?: { id: string; label?: string }[] | null;
};

/**
 * Which date a canvas works in, and whether it is compulsory.
 *
 * The header used to print "Date filter: Reporting period" — a literal fallback for when
 * `required_date_field` is absent. No dbt canvas declares one, so every canvas asserted
 * a mandatory reporting-period filter that does not exist and cannot be adjusted.
 *
 * A required date field is a real constraint and is still labelled as one. Otherwise the
 * canvas still has a date it works in by default, and naming it ("Dates on: SA Start
 * Date") tells the reader something they can act on. A canvas with no date says nothing.
 */
export function dateScope(
  meta: DateScopeSource,
): { label: string; value: string; required: boolean } | null {
  const required = meta.required_date_field;
  if (required) {
    const named =
      meta.required_date_label ||
      meta.date_fields?.find((d) => d.id === required)?.label ||
      required;
    return { label: "Date filter", value: named, required: true };
  }

  const fallback = meta.default_date_field;
  if (fallback) {
    const named = meta.date_fields?.find((d) => d.id === fallback)?.label || fallback;
    return { label: "Dates on", value: named, required: false };
  }
  return null;
}
