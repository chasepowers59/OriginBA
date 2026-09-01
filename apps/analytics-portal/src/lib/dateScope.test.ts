import { describe, expect, it } from "vitest";
import { dateScope } from "./dateScope";

/**
 * The canvas header showed a "Date filter" pill reading "Reporting period" on every dbt
 * canvas — a hardcoded fallback for when `required_date_field` is absent, which it always
 * is: no canvas declares one. So the page asserted a mandatory reporting-period filter
 * that does not exist and cannot be adjusted.
 *
 * A canvas still HAS a date it works in — `default_date_field`, the one the builder and
 * the KPIs window on — and saying which is genuinely useful. Saying "Reporting period"
 * is only reassuring.
 */
describe("dateScope", () => {
  it("reports a genuine required filter as required", () => {
    const scope = dateScope({
      required_date_field: "ACCOUNTING_DT",
      required_date_label: "Accounting date",
      default_date_field: "Bill Date",
      date_fields: [],
    });
    expect(scope).toEqual({ label: "Date filter", value: "Accounting date", required: true });
  });

  it("falls back to the field's own label when no friendly one is set", () => {
    const scope = dateScope({
      required_date_field: "ACCOUNTING_DT",
      required_date_label: null,
      default_date_field: null,
      date_fields: [{ id: "ACCOUNTING_DT", label: "Accounting Date" }],
    });
    expect(scope?.value).toBe("Accounting Date");
  });

  it("names the default date a canvas actually works in, and does not call it a filter", () => {
    const scope = dateScope({
      required_date_field: null,
      required_date_label: null,
      default_date_field: "SA Start Date",
      date_fields: [{ id: "SA Start Date", label: "SA Start Date" }],
    });
    expect(scope).toEqual({ label: "Dates on", value: "SA Start Date", required: false });
  });

  it("shows nothing rather than inventing a period when there is no date at all", () => {
    expect(
      dateScope({
        required_date_field: null,
        required_date_label: null,
        default_date_field: null,
        date_fields: [],
      }),
    ).toBeNull();
  });

  it("never returns the old invented wording", () => {
    const scope = dateScope({
      required_date_field: null,
      required_date_label: null,
      default_date_field: "Bill Date",
      date_fields: [],
    });
    expect(scope?.value).not.toBe("Reporting period");
  });
});

describe("snapshot detail line", () => {
  it("names the date the canvas works in", async () => {
    const { snapshotDetailLine } = await import("./snapshot");
    const line = snapshotDetailLine({
      grain_description: "One row per service agreement",
      required_date_field: null,
      default_date_field: "SA Start Date",
      date_fields: [],
    } as never);
    expect(line).toBe("One row per service agreement · dates on SA Start Date");
  });

  it("never says the tautology it used to", async () => {
    const { snapshotDetailLine } = await import("./snapshot");
    const line = snapshotDetailLine({
      grain_description: "One row per account",
      required_date_field: null,
      default_date_field: null,
      date_fields: [],
    } as never);
    expect(line).toBe("One row per account");
    expect(line).not.toContain("reporting period uses");
  });
});
