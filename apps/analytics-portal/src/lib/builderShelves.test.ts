import { describe, expect, it } from "vitest";
import { fieldGlyph, shelfDimensions, startingQuestions } from "./builderShelves";

/**
 * Dragging a date onto the Columns shelf used to WIPE every other column: the
 * request sent `dimensions: timeDims.length ? [] : dims`, so a date silently
 * turned the result into "one measure per bucket" and dropped the account,
 * class and status columns the user had already chosen.
 *
 * The server always supported both — build_query appends time-dimension
 * expressions AND plain dimensions to SELECT and GROUP BY. Only the client
 * threw them away.
 */
describe("shelfDimensions", () => {
  const dim = (field: string) => ({ field, label: field, kind: "dim" as const });
  const time = (field: string, grain = "month") => ({
    field,
    label: field,
    kind: "time" as const,
    grain,
  });

  it("keeps the other columns when a date is added", () => {
    const out = shelfDimensions([dim("Customer Class"), time("Accounting Date")]);
    expect(out.dimensions).toEqual(["Customer Class"]);
    expect(out.timeDimensions).toEqual([{ field: "Accounting Date", grain: "month" }]);
  });

  it("keeps every dimension, in shelf order", () => {
    const out = shelfDimensions([
      dim("Customer Class"),
      time("Accounting Date"),
      dim("Bill Cycle"),
    ]);
    expect(out.dimensions).toEqual(["Customer Class", "Bill Cycle"]);
  });

  it("is unchanged with no date on the shelf", () => {
    const out = shelfDimensions([dim("Customer Class"), dim("Bill Cycle")]);
    expect(out.dimensions).toEqual(["Customer Class", "Bill Cycle"]);
    expect(out.timeDimensions).toEqual([]);
  });

  it("carries each date's own grain", () => {
    const out = shelfDimensions([time("Accounting Date", "quarter"), time("Bill Date", "year")]);
    expect(out.timeDimensions).toEqual([
      { field: "Accounting Date", grain: "quarter" },
      { field: "Bill Date", grain: "year" },
    ]);
  });

  it("defaults a missing grain to month", () => {
    const out = shelfDimensions([{ field: "Accounting Date", label: "d", kind: "time" as const }]);
    expect(out.timeDimensions[0].grain).toBe("month");
  });

  it("handles an empty shelf", () => {
    expect(shelfDimensions([])).toEqual({ dimensions: [], timeDimensions: [] });
  });
});

describe("the type chip on a field", () => {
  it("marks a flag as true/false, not text (the design review read Is Frozen as Abc)", () => {
    expect(fieldGlyph({ role: "dimension", type: "boolean" })).toBe("T/F");
    expect(fieldGlyph({ role: "dimension", type: "text" })).toBe("Abc");
    expect(fieldGlyph({ role: "measure", type: "numeric(17,2)" })).toBe("#");
    expect(fieldGlyph({ role: "date", type: "timestamp" })).toBe("YMD");
    expect(fieldGlyph({ role: "other", type: "text" })).toBe("?");
  });
});

describe("the builder's starting questions", () => {
  // design review 2026-09-30: the builder opened as a blank panel and one sentence
  // one per WORKSTREAM: one per data set gave six billing questions, the gallery's first section
  const q = (id: string, workstream: string) => ({ id, workstream, title: id }) as never;
  it("one question per workstream, in the gallery's order, at most six", () => {
    const qs = [q("a1", "A"), q("a2", "A"), q("b1", "B"), q("c1", "C"), q("d1", "D"), q("e1", "E"), q("f1", "F"), q("g1", "G")];
    expect(startingQuestions(qs).map((x: { id: string }) => x.id)).toEqual(["a1", "b1", "c1", "d1", "e1", "f1"]);
  });
  it("is empty when there are no questions", () => {
    expect(startingQuestions([])).toEqual([]);
  });
});
