import { describe, expect, it } from "vitest";
import { resolveDateField, tileWindow, tileWindowField } from "./tileDateField";

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

/**
 * The dashboard's "last N days" window. A canvas of what exists now (catalog
 * `all_dates`: accounts, agreements, meters) and a backlog report (every open item,
 * however old) are never windowed: on rpt_customer_account the window fell on Account
 * Setup Date, so "Accounts on budget billing" on a 30-day board counted only the
 * accounts opened this month.
 */
describe("tileWindowField", () => {
  const dated = { default_date_field: "Bill Date", date_fields: [{ id: "Bill Date" }] };

  it("windows a dated canvas on its date", () => {
    expect(tileWindowField(dated, null)).toBe("Bill Date");
    expect(tileWindowField(dated, { all_dates: false })).toBe("Bill Date");
  });

  it("never windows a canvas of what exists now", () => {
    expect(tileWindowField({ ...dated, default_date_preset: "all_dates" }, null)).toBeNull();
  });

  it("never windows a backlog report", () => {
    expect(tileWindowField(dated, { all_dates: true })).toBeNull();
  });

  it("has nothing to window without a date", () => {
    expect(tileWindowField({ default_date_field: null, date_fields: [] }, null)).toBeNull();
  });
});

/**
 * What a tile tells the server about dates. Sending no window is not enough: the server
 * applies its own trailing window to any unfiltered query unless told all_dates, so a
 * backlog tile ("open exceptions, however old") quietly lost every old exception.
 */
describe("tileWindow", () => {
  const dated = { default_date_field: "Created Date/Time", date_fields: [{ id: "Created Date/Time" }] };
  const range: [string, string] = ["2026-04-01", "2026-09-30"];

  it("windows a dated tile and leaves all_dates off", () => {
    expect(tileWindow(dated, null, range)).toEqual({
      filters: [{ field: "Created Date/Time", op: "between", value: range }], all_dates: false,
    });
  });

  it("asks for all dates outright when the tile is not windowed", () => {
    expect(tileWindow(dated, { all_dates: true }, range)).toEqual({ filters: [], all_dates: true });
    expect(tileWindow({ ...dated, default_date_preset: "all_dates" }, null, range))
      .toEqual({ filters: [], all_dates: true });
  });
});
