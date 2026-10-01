/** A column sitting on the builder's Columns/Group shelf. */
export type ShelfColumn = {
  field: string;
  label: string;
  kind: "dim" | "time";
  grain?: string;
};

/**
 * Split the Columns shelf into the two things the query API takes.
 *
 * Both are sent together. A date used to REPLACE the shelf — the request built
 * `dimensions: timeDims.length ? [] : dims` — so dragging in a date silently
 * dropped every column the user had already chosen and left one measure per
 * bucket. `build_query` has always appended time-dimension expressions and plain
 * dimensions to both SELECT and GROUP BY, so the collapse was never a server
 * limitation; the client was discarding the columns before they were sent.
 */
export function shelfDimensions(cols: ShelfColumn[]): {
  dimensions: string[];
  timeDimensions: { field: string; grain: string }[];
} {
  return {
    dimensions: cols.filter((c) => c.kind === "dim").map((c) => c.field),
    timeDimensions: cols
      .filter((c) => c.kind === "time")
      .map((c) => ({ field: c.field, grain: c.grain ?? "month" })),
  };
}

// Text glyphs, not emoji: a colour emoji ignores the badge colour and is illegible at 9px.
const ROLE_GLYPH: Record<string, string> = { dimension: "Abc", measure: "#", date: "YMD" };

/** The type chip on a field. A flag is a dimension, but reading "Abc" beside Is Frozen
 *  says it holds words; it holds true or false. */
export function fieldGlyph(field: { role: string; type: string }): string {
  if (field.type === "boolean") return "T/F";
  return ROLE_GLYPH[field.role] ?? "?";
}

/** What the empty builder offers to start from: one ready-to-run question per workstream. */
export function startingQuestions<T extends { workstream: string }>(questions: T[], shown = 6): T[] {
  const seen = new Set<string>();
  return questions.filter((q) => !seen.has(q.workstream) && seen.add(q.workstream)).slice(0, shown);
}

// --- reordering what sits on a shelf -------------------------------------------------------
// A chip on a shelf is sortable under the id "<shelf>::<key>"; the shelves themselves are
// droppable under their bare names. The palette's pills use "palette:<field>".
const SEP = "::";

export function sortableId(shelf: string, key: string): string {
  return `${shelf}${SEP}${key}`;
}

export function parseSortableId(id: string): { shelf: string; key: string } | null {
  const at = id.indexOf(SEP);
  return at > 0 ? { shelf: id.slice(0, at), key: id.slice(at + SEP.length) } : null;
}

/** The shelf a drop landed on, whether the pointer was over the shelf or over a chip in it. */
export function dropShelf(overId: string): string {
  return parseSortableId(overId)?.shelf ?? overId;
}

/** Move the item keyed `activeKey` to where `overKey` sits, or to the end when the drop
 *  was on the shelf itself (`overKey` null). Unchanged (same array) when nothing moves. */
export function reorderShelf<T>(items: T[], keyOf: (t: T) => string, activeKey: string, overKey: string | null): T[] {
  const from = items.findIndex((t) => keyOf(t) === activeKey);
  const to = overKey === null ? items.length - 1 : items.findIndex((t) => keyOf(t) === overKey);
  if (from < 0 || to < 0 || from === to) return items;
  const out = items.slice();
  const [moved] = out.splice(from, 1);
  out.splice(to, 0, moved);
  return out;
}

/** A measure on the Values shelf is the field AND its aggregation: the same column summed
 *  and maxed is two items. */
export function valueKey(v: { field: string; agg: string }): string {
  return `${v.field}|${v.agg}`;
}
