import { describe, expect, it } from "vitest";
import { dateScope } from "./dateScope";

/**
 * The header names the date a canvas works in, and never claims it is compulsory.
 *
 * It used to print "Date filter: Reporting period" -- a literal fallback for a
 * mandatory-window field no canvas sets -- so every canvas asserted a required filter
 * that did not exist and could not be adjusted. "Dates on: Bill Date" is something a
 * reader can act on; a canvas with no date says nothing.
 */
describe("dateScope", () => {
  it("names the canvas's date by its label", () => {
    expect(dateScope({
      default_date_field: "Bill Date",
      date_fields: [{ id: "Bill Date", label: "Bill Date" }],
    })).toEqual({ label: "Dates on", value: "Bill Date", required: false });
  });

  it("falls back to the id when no label is declared", () => {
    expect(dateScope({ default_date_field: "SA Start Date" }))
      .toEqual({ label: "Dates on", value: "SA Start Date", required: false });
  });

  it("says nothing for a canvas with no date", () => {
    expect(dateScope({ default_date_field: null })).toBeNull();
    expect(dateScope({})).toBeNull();
  });
});
