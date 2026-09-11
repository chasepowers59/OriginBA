import { describe, expect, it } from "vitest";
import { resolveDateField } from "./tileDateField";

/**
 * The ONE resolver for the date a canvas works in. Every canvas with a date declares a
 * measured `default_date_field`; the first declared date is the only fallback, and null
 * means the canvas genuinely has no date. Three consumers key off this -- the explorer's
 * presets, the dashboard's day window and a tile's time grain -- so a wrong answer here
 * silently un-windows or un-groups all of them.
 */
describe("resolveDateField", () => {
  it("prefers the measured default", () => {
    expect(resolveDateField({ default_date_field: "Bill Date",
                              date_fields: [{ id: "Due Date" }] })).toBe("Bill Date");
  });

  it("falls back to the first declared date", () => {
    expect(resolveDateField({ default_date_field: null, date_fields: [{ id: "Due Date" }] }))
      .toBe("Due Date");
  });

  it("is null only when the canvas has no date at all", () => {
    expect(resolveDateField({ default_date_field: null, date_fields: [] })).toBeNull();
    expect(resolveDateField(undefined)).toBeNull();
    expect(resolveDateField(null)).toBeNull();
  });
});
