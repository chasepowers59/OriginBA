import { describe, expect, it } from "vitest";
import * as XLSX from "xlsx";
import { buildWorkbook } from "./exportXlsx";

/**
 * True .xlsx export ("Export to Excel" used to write CSV — utility finance lives in
 * Excel, and CSV loses types). Contract: numbers stay numeric, booleans render as the
 * app-wide True/False, null is empty, sheet names are Excel-legal, and a dashboard
 * exports one sheet per section.
 */
describe("buildWorkbook", () => {
  const roundTrip = (buf: ArrayBuffer) => XLSX.read(buf, { type: "array" });

  it("keeps numbers numeric and strings intact", () => {
    const wb = roundTrip(
      buildWorkbook([
        {
          name: "Data",
          columns: ["Customer Class", "Accounts", "Balance"],
          rows: [
            { "Customer Class": "Residential", Accounts: 1042, Balance: 1727934.38 },
            { "Customer Class": "Commercial", Accounts: 70, Balance: -2482.32 },
          ],
        },
      ]),
    );
    const sheet = wb.Sheets["Data"];
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet);
    expect(rows[0]["Accounts"]).toBe(1042);
    expect(typeof rows[0]["Balance"]).toBe("number");
    expect(rows[1]["Customer Class"]).toBe("Commercial");
    expect(rows[1]["Balance"]).toBeCloseTo(-2482.32);
  });

  it("renders booleans as True/False and null as empty", () => {
    const wb = roundTrip(
      buildWorkbook([
        {
          name: "Flags",
          columns: ["Is Frozen", "Note"],
          rows: [
            { "Is Frozen": true, Note: null },
            { "Is Frozen": false, Note: "x" },
          ],
        },
      ]),
    );
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(wb.Sheets["Flags"], {
      defval: "",
    });
    expect(rows[0]["Is Frozen"]).toBe("True");
    expect(rows[1]["Is Frozen"]).toBe("False");
    expect(rows[0]["Note"]).toBe("");
  });

  it("sanitizes sheet names (31-char cap, illegal chars) and keeps them unique", () => {
    const wb = roundTrip(
      buildWorkbook([
        { name: "Billed revenue: by class [2026/Q1]", columns: ["A"], rows: [{ A: 1 }] },
        { name: "Billed revenue: by class [2026/Q2]", columns: ["A"], rows: [{ A: 2 }] },
      ]),
    );
    expect(wb.SheetNames).toHaveLength(2);
    for (const n of wb.SheetNames) {
      expect(n.length).toBeLessThanOrEqual(31);
      expect(/[\[\]:*?/\\]/.test(n)).toBe(false);
    }
    expect(new Set(wb.SheetNames).size).toBe(2);
  });

  it("exports one sheet per dashboard section", () => {
    const wb = roundTrip(
      buildWorkbook([
        { name: "Revenue", columns: ["A"], rows: [{ A: 1 }] },
        { name: "Payments", columns: ["A"], rows: [{ A: 2 }] },
        { name: "Debt", columns: ["A"], rows: [] },
      ]),
    );
    expect(wb.SheetNames).toEqual(["Revenue", "Payments", "Debt"]);
  });
});
