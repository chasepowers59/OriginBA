import { describe, expect, it } from "vitest";
import { shelfDimensions } from "./builderShelves";

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
