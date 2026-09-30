import { describe, expect, it } from "vitest";
import { activeFilters, answerPrompts, cascadeFilters, optionsWithCurrent, restoreFilters, questionFilters, savedFilters, unanswered, type ShelfFilter } from "./builderFilters";

/**
 * The builder never saved its filters shelf, and the restore never set it. A view
 * scoped to one service type reopened over the WHOLE canvas -- different numbers, no
 * warning. (The API dropped them too: SavedViewCreate did not declare `filters`, so
 * Pydantic discarded them; see tests/test_saved_view_route_fidelity.py.)
 *
 * The rule for which filters are live is shared here on purpose. buildRequest already
 * had it -- "a filter whose value hasn't been chosen yet is inert, sending it as = ''
 * would silently return zero rows" -- and saveView needs the SAME rule, or the view
 * that reopens is not the view that ran.
 */
describe("activeFilters", () => {
  it("drops a filter whose value was never chosen", () => {
    expect(activeFilters([{ field: "SA Type", label: "SA Type", op: "eq", value: "", role: "dimension" }])).toEqual([]);
    expect(activeFilters([{ field: "SA Type", label: "SA Type", op: "eq", value: null, role: "dimension" }])).toEqual([]);
  });

  it("keeps a date filter even though its value is implicit", () => {
    const out = activeFilters([
      { field: "Bill Date", label: "Bill Date", op: "between", value: ["2025-01-01", "2025-12-31"], role: "date" },
    ]);
    expect(out).toHaveLength(1);
    expect(out[0].field).toBe("Bill Date");
  });

  it("keeps a zero and a false, which are chosen values", () => {
    // `if (!value)` would drop both; the shelf compares against "" for this reason.
    expect(activeFilters([{ field: "Count", label: "Count", op: "eq", value: 0, role: "measure" }])).toHaveLength(1);
    expect(activeFilters([{ field: "Is Frozen", label: "Is Frozen", op: "eq", value: false, role: "dimension" }])).toHaveLength(1);
  });

  it("carries only the wire fields, not the shelf's label and role", () => {
    expect(
      activeFilters([{ field: "SA Type", label: "SA Type", op: "eq", value: "E-RES", role: "dimension" }]),
    ).toEqual([{ field: "SA Type", op: "eq", value: "E-RES" }]);
  });

  it("is empty for an empty shelf", () => {
    expect(activeFilters([])).toEqual([]);
    expect(activeFilters(undefined)).toEqual([]);
  });
});

const FIELDS = [
  { id: "SA Type", label: "SA Type", role: "dimension" },
  { id: "Bill Date", label: "Bill Date", role: "date" },
];

describe("restoreFilters", () => {
  it("rebuilds the shelf pills with their labels and roles", () => {
    const out = restoreFilters([{ field: "SA Type", op: "eq", value: "E-RES" }], FIELDS);
    expect(out).toEqual([
      { field: "SA Type", label: "SA Type", op: "eq", value: "E-RES", role: "dimension" },
    ]);
  });

  it("restores a date filter with its saved range, not a fresh default", () => {
    const out = restoreFilters(
      [{ field: "Bill Date", op: "between", value: ["2025-01-01", "2025-12-31"] }],
      FIELDS,
    );
    expect(out[0].value).toEqual(["2025-01-01", "2025-12-31"]);
    expect(out[0].role).toBe("date");
  });

  it("drops a filter on a field this canvas no longer has", () => {
    // Rendering a pill for a field that is gone would give it no value picker and no
    // way to remove the scope it is silently applying.
    expect(restoreFilters([{ field: "Retired Column", op: "eq", value: "x" }], FIELDS)).toEqual([]);
  });

  it("labels nothing it cannot label", () => {
    expect(restoreFilters(null, FIELDS)).toEqual([]);
    expect(restoreFilters([], FIELDS)).toEqual([]);
    expect(restoreFilters([{ field: "SA Type", op: "eq", value: "x" }], undefined)).toEqual([]);
  });

  it("keeps a filter whose value the option list cannot show", () => {
    // See optionsWithCurrent below — the pill must still restore; it is the PICKER
    // that has to admit the value, not the restore that should drop it.
    const out = restoreFilters([{ field: "SA Type", op: "eq", value: "RARE" }], FIELDS);
    expect(out[0].value).toBe("RARE");
  });

  it("round-trips with activeFilters", () => {
    const shelf = [
      { field: "SA Type", label: "SA Type", op: "eq", value: "E-RES", role: "dimension" },
    ];
    expect(restoreFilters(activeFilters(shelf), FIELDS)).toEqual(shelf);
  });
});

/**
 * The value picker fetches a field's distinct values CAPPED AT 100 and rendered a
 * <select> whose value was the filter's. When the saved value is not among those 100 —
 * routine for a high-cardinality field — the select falls back to its first option and
 * displays "choose value…", while the filter is still applied.
 *
 * Measured on /build?view=… with a filter on Bill ID (exactly 100 options returned):
 *   picker showed   "choose value…", select.value === ""
 *   query ran       WHERE "Bill ID" = %(b0)s   -> 0 rows
 *
 * So the user sees an empty chart and a filter that looks unset. That is the
 * scope-mismatch failure inverted: the UI claims no scope while the query has one.
 */
describe("optionsWithCurrent", () => {
  it("leaves the list alone when the value is in it", () => {
    expect(optionsWithCurrent(["A", "B"], "A")).toEqual(["A", "B"]);
  });

  it("adds the value the list does not carry, so the picker can show it", () => {
    expect(optionsWithCurrent(["A", "B"], "RARE")).toEqual(["RARE", "A", "B"]);
  });

  it("adds nothing when no value is chosen", () => {
    expect(optionsWithCurrent(["A", "B"], "")).toEqual(["A", "B"]);
  });

  it("passes through the loading state untouched", () => {
    expect(optionsWithCurrent(null, "RARE")).toBeNull();
  });

  it("never duplicates", () => {
    const out = optionsWithCurrent(["A", "A", "B"], "A");
    expect(out!.filter((v) => v === "A")).toHaveLength(2); // preserves the source list
    expect(optionsWithCurrent(["A"], "A")).toEqual(["A"]);
  });
});

describe("questionFilters", () => {
  const fields = [
    { id: "Bill Date", label: "Bill Date", role: "date" },
    { id: "Is Frozen", label: "Is Frozen", role: "dimension" },
    { id: "Is Cancelled", label: "Is Cancelled", role: "dimension" },
  ];
  const window = { field: "Bill Date", op: "between", value: ["2026-03-20", "2026-06-18"] };
  const frozen = [{ field: "Is Frozen", op: "eq", value: true }, { field: "Is Cancelled", op: "eq", value: false }];

  it("adds the canvas's default window, as a visible pill, to a question that filters on flags only", () => {
    // Declaring "Is Frozen" on revenue-by-cycle (2026-09-28) turned "last 90 days" into all
    // time: the server windows only a query with NO filters. The window is now the builder's
    // own pill, so it is seen and can be removed.
    const pills = questionFilters(frozen, fields, window);
    expect(pills.map((p) => p.field)).toEqual(["Is Frozen", "Is Cancelled", "Bill Date"]);
    expect(pills[2]).toMatchObject({ op: "between", value: ["2026-03-20", "2026-06-18"], role: "date" });
  });

  it("leaves a question that already filters on a date alone", () => {
    const own = [...frozen, { field: "Bill Date", op: "gte", value: "2026-01-01" }];
    expect(questionFilters(own, fields, window).map((p) => p.field)).toEqual(["Is Frozen", "Is Cancelled", "Bill Date"]);
    expect(questionFilters(own, fields, window)[2].op).toBe("gte");
  });

  it("adds nothing to a question with no filters: the server's disclosed window covers it", () => {
    expect(questionFilters([], fields, window)).toEqual([]);
  });

  it("adds nothing when the canvas has no default window", () => {
    expect(questionFilters(frozen, fields, null).map((p) => p.field)).toEqual(["Is Frozen", "Is Cancelled"]);
  });
});

describe("report parameters (filters asked for when a view opens)", () => {
  const fils: ShelfFilter[] = [
    { field: "Bill Cycle", label: "Bill Cycle", op: "eq", value: "C1", role: "dimension", prompt: true },
    { field: "Is Frozen", label: "Is Frozen", op: "eq", value: true, role: "dimension" },
    { field: "Bill Date", label: "Bill Date", op: "between", value: ["2026-01-01", "2026-03-31"], role: "date", prompt: true },
  ];

  it("a view saves which filters to ask for", () => {
    expect(savedFilters(fils)).toEqual([
      { field: "Bill Cycle", op: "eq", value: "C1", prompt: true },
      { field: "Is Frozen", op: "eq", value: true },
      { field: "Bill Date", op: "between", value: ["2026-01-01", "2026-03-31"], prompt: true },
    ]);
  });

  it("the query never carries the prompt flag", () => {
    expect(activeFilters(fils).every((f) => !("prompt" in f))).toBe(true);
  });

  it("reopening restores which filters to ask for", () => {
    const back = restoreFilters(savedFilters(fils), [
      { id: "Bill Cycle", role: "dimension" }, { id: "Is Frozen", role: "dimension" }, { id: "Bill Date", role: "date" },
    ]);
    expect(back.filter((f) => f.prompt).map((f) => f.field)).toEqual(["Bill Cycle", "Bill Date"]);
  });

  it("answers replace the saved defaults, and a blank answer is reported, not run", () => {
    const answered = answerPrompts(fils, { "Bill Cycle": "C7", "Bill Date": ["2026-04-01", "2026-06-18"] });
    expect(answered.find((f) => f.field === "Bill Cycle")?.value).toBe("C7");
    expect(answered.find((f) => f.field === "Bill Date")?.value).toEqual(["2026-04-01", "2026-06-18"]);
    expect(unanswered(answerPrompts(fils, { "Bill Cycle": "" }))).toEqual(["Bill Cycle"]);
    expect(unanswered(answerPrompts(fils, { "Bill Date": ["2026-04-01", ""] }))).toEqual(["Bill Date"]);
  });
});

describe("cascading report parameters", () => {
  const asked: ShelfFilter[] = [
    { field: "Bill Date", label: "Bill Date", op: "between", value: ["2026-01-01", "2026-03-31"], role: "date", prompt: true },
    { field: "Bill Cycle", label: "Bill Cycle", op: "eq", value: "", role: "dimension", prompt: true },
    { field: "Customer Class", label: "Customer Class", op: "eq", value: "", role: "dimension", prompt: true },
  ];

  it("each list is narrowed by the answered parameters above it", () => {
    const answers = { "Bill Date": ["2026-01-01", "2026-03-31"], "Bill Cycle": "C1" };
    expect(cascadeFilters(asked, answers, 2)).toEqual([
      { field: "Bill Date", op: "between", value: ["2026-01-01", "2026-03-31"] },
      { field: "Bill Cycle", op: "eq", value: "C1" },
    ]);
  });

  it("the first list and unanswered parameters narrow nothing", () => {
    expect(cascadeFilters(asked, {}, 0)).toEqual([]);
    expect(cascadeFilters(asked, { "Bill Cycle": "" }, 2)).toEqual([
      { field: "Bill Date", op: "between", value: ["2026-01-01", "2026-03-31"] },
    ]);
  });
});

describe("a parameter with no default", () => {
  it("is still saved, so it is asked for; the query leaves it out until answered", () => {
    const fils: ShelfFilter[] = [
      { field: "Customer Class", label: "Customer Class", op: "eq", value: "", role: "dimension", prompt: true },
      { field: "Bill Cycle", label: "Bill Cycle", op: "eq", value: "", role: "dimension" },
    ];
    expect(savedFilters(fils)).toEqual([{ field: "Customer Class", op: "eq", value: "", prompt: true }]);
    expect(activeFilters(fils)).toEqual([]);
  });
});
