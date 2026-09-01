import { describe, expect, it } from "vitest";
import { exportFilename } from "./exportFilename";

/**
 * These files get emailed around, so the name is the only label they carry once they
 * leave the portal. The dashboard export produced
 *
 *   INT_DEV_(internal_dev_CISADM)_Executive_Dashboard_dashboard.xlsx
 *
 * -- "dashboard" twice, because the suffix was appended to a title that already ended
 * in it, and only whitespace was replaced, so a client whose name carries a slash or a
 * colon would have produced a name the filesystem refuses or silently truncates.
 */
describe("exportFilename", () => {
  it("does not repeat a word the title already ends with", () => {
    expect(exportFilename("Acme Executive Dashboard", "dashboard", "xlsx")).toBe(
      "Acme_Executive_Dashboard.xlsx",
    );
  });

  it("appends the kind when the title does not already say it", () => {
    expect(exportFilename("Billing operations", "dashboard", "xlsx")).toBe(
      "Billing_operations_dashboard.xlsx",
    );
  });

  it("ignores case when deciding whether the word is already there", () => {
    expect(exportFilename("Q4 DASHBOARD", "dashboard", "xlsx")).toBe("Q4_DASHBOARD.xlsx");
  });

  it("removes characters a filesystem will not take", () => {
    const name = exportFilename("Water/Sewer: North *2026*", "report", "csv");
    expect(name).not.toMatch(/[/\\:*?"<>|]/);
    expect(name.endsWith(".csv")).toBe(true);
  });

  it("keeps a real org name readable rather than mangling it", () => {
    expect(exportFilename("INT_DEV (internal dev CISADM) Executive Dashboard", "dashboard", "xlsx"))
      .toBe("INT_DEV_internal_dev_CISADM_Executive_Dashboard.xlsx");
  });

  it("collapses runs of separators instead of leaving gaps", () => {
    expect(exportFilename("A   —   B", "pack", "pdf")).toBe("A_B_pack.pdf");
  });

  it("never returns a name that is only an extension", () => {
    expect(exportFilename("", "dashboard", "xlsx")).toBe("dashboard.xlsx");
    expect(exportFilename("///", "", "csv")).toBe("export.csv");
  });
});
