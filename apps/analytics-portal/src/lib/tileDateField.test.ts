import { describe, expect, it } from "vitest";
import { resolveTileDateField } from "./tileDateField";

/**
 * A dashboard tile only built its time dimension when the canvas declared a
 * `required_date_field`, and no dbt canvas declares one -- it is a CISADM-era notion
 * for snapshots too large to scan unfiltered. So on the dbt path every "by month" tile
 * dropped its time dimension, the query came back as a single aggregate row, and the
 * chart fell through to plotting the MEASURE on the x axis: "Billed revenue by month"
 * drew one dot labelled 1072398.6, a dollar amount posing as a month.
 *
 * Every canvas does carry `default_date_field`, so there is always a date to group by.
 */
describe("resolveTileDateField", () => {
  const meta = (over = {}) => ({
    required_date_field: null,
    default_date_field: "Bill Date",
    date_fields: [{ id: "Bill Date" }, { id: "Due Date" }],
    ...over,
  });

  it("uses the canvas default when nothing is required", () => {
    expect(resolveTileDateField(meta())).toBe("Bill Date");
  });

  it("keeps honouring a required date field above all else", () => {
    expect(resolveTileDateField(meta({ required_date_field: "Accounting Date" }))).toBe(
      "Accounting Date",
    );
  });

  it("falls back to the first declared date field", () => {
    expect(resolveTileDateField(meta({ default_date_field: null }))).toBe("Bill Date");
  });

  it("returns null when the canvas genuinely has no date", () => {
    expect(resolveTileDateField(meta({ default_date_field: null, date_fields: [] }))).toBeNull();
    expect(resolveTileDateField(undefined)).toBeNull();
  });
});
