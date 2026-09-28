/**
 * The filters shelf, shared between running a query and saving a view.
 *
 * buildRequest already knew which filters are live; saveView did not save them at all,
 * so a scoped view reopened over the whole canvas. Both now use `activeFilters`, so the
 * view that reopens is by construction the view that ran.
 */

/** Matches the builder's FilItem: a pill always has a label and a role to render. */
export type ShelfFilter = {
  field: string;
  label: string;
  op: string;
  value: unknown;
  role: string;
  /** Ask for this filter's value when the saved view is opened (a report parameter). */
  prompt?: boolean;
};

export type QueryFilter = { field: string; op: string; value: unknown };
/** A filter as a saved view stores it: the query filter plus whether to ask for it. */
export type SavedFilter = QueryFilter & { prompt?: boolean };

type FieldLike = { id: string; label?: string; role?: string };

/**
 * A non-date filter whose value has not been chosen is inert — sending it as `= ''`
 * would silently return zero rows. Compared against "" rather than truthiness so a
 * chosen 0 or false survives.
 */
export function activeFilters(fils: readonly ShelfFilter[] | undefined): QueryFilter[] {
  return (fils ?? [])
    .filter((f) => f.role === "date" || String(f.value ?? "") !== "")
    .map((f) => ({ field: f.field, op: f.op, value: f.value }));
}

/**
 * The option list a value picker should render. Distinct values are capped at 100, so
 * a saved filter on a high-cardinality field routinely falls outside them — and a
 * <select> whose value matches no option silently shows its first ("choose value…")
 * while the filter still applies. Admitting the current value keeps what the picker
 * SHOWS and what the query DOES the same thing.
 */
export function optionsWithCurrent(
  values: string[] | null,
  current: string,
): string[] | null {
  if (values === null) return null;
  if (!current || values.includes(current)) return values;
  return [current, ...values];
}

/** Rebuild shelf pills from a saved view, dropping fields the canvas no longer has. */
/** What a saved view stores: the query's filters, each marked if it is asked for on open. */
export function savedFilters(fils: readonly ShelfFilter[] | undefined): SavedFilter[] {
  const asked = new Set((fils ?? []).filter((f) => f.prompt).map((f) => f.field));
  return activeFilters(fils).map((f) => (asked.has(f.field) ? { ...f, prompt: true } : f));
}

/** The shelf with the person's answers in place of the saved defaults. */
export function answerPrompts(fils: readonly ShelfFilter[], answers: Record<string, unknown>): ShelfFilter[] {
  return fils.map((f) => (f.prompt && f.field in answers ? { ...f, value: answers[f.field] } : f));
}

/** The asked-for filters still without a value: a blank, or a range missing an end. */
export function unanswered(fils: readonly ShelfFilter[]): string[] {
  const blank = (v: unknown) => (Array.isArray(v) ? v.length < 2 || v.some((x) => String(x ?? "") === "")
                                                  : String(v ?? "") === "");
  return fils.filter((f) => f.prompt && blank(f.value)).map((f) => f.field);
}

export function restoreFilters(
  saved: SavedFilter[] | null | undefined,
  fields: FieldLike[] | undefined,
): ShelfFilter[] {
  if (!saved?.length || !fields?.length) return [];
  const out: ShelfFilter[] = [];
  for (const f of saved) {
    const field = fields.find((x) => x.id === f.field);
    // A pill for a missing field would have no value picker, so the scope it applies
    // could be neither seen nor removed.
    if (!field) continue;
    out.push({
      field: f.field,
      label: field.label ?? f.field,
      op: f.op,
      value: f.value,
      role: field.role ?? "dimension",
      ...(f.prompt ? { prompt: true } : {}),
    });
  }
  return out;
}

/**
 * The pills a governed question opens with. The server windows a query only when it has NO
 * filters (a caller's filter is never overlaid with a hidden window), so a question that
 * declares flag filters -- revenue on frozen segments -- ran over all time. When a question
 * filters but not on a date, the canvas's default window joins the shelf as its own pill:
 * visible, labelled, and removable.
 */
export function questionFilters(
  declared: readonly QueryFilter[] | null | undefined,
  fields: FieldLike[] | undefined,
  defaultWindow: QueryFilter | null | undefined,
): ShelfFilter[] {
  const pill = (f: QueryFilter): ShelfFilter => {
    const fd = fields?.find((x) => x.id === f.field);
    return { field: f.field, label: fd?.label ?? f.field, op: f.op, value: f.value, role: fd?.role ?? "dimension" };
  };
  const pills = (declared ?? []).map(pill);
  const datesFiltered = pills.some((p) => p.role === "date");
  if (pills.length && !datesFiltered && defaultWindow) pills.push({ ...pill(defaultWindow), role: "date" });
  return pills;
}
