type DateScopeSource = {
  default_date_field?: string | null;
  date_fields?: { id: string; label?: string }[] | null;
};

/**
 * Which date a canvas works in, for the header.
 *
 * "Dates on: Bill Date" tells the reader something they can act on; a canvas with no
 * date says nothing. The date is never compulsory — a mandatory transaction window was
 * a notion from the retired snapshot catalog, and it is meaningless on a dimension
 * table like the price list.
 */
export function dateScope(
  meta: DateScopeSource,
): { label: string; value: string; required: boolean } | null {
  const field = meta.default_date_field;
  if (!field) return null;
  const named = meta.date_fields?.find((d) => d.id === field)?.label || field;
  return { label: "Dates on", value: named, required: false };
}
