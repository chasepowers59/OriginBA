import { describe, expect, it } from "vitest";
import { packFilename, packSummary, type PackImportResult } from "./contentPack";

const result = (views: string[], skippedViews: number, boards: string[], skippedBoards = 0, dry = true): PackImportResult => ({
  dry_run: dry,
  views: { imported: views, skipped: Array.from({ length: skippedViews }, (_, i) => ({ title: `s${i}`, reason: "r" })) },
  dashboards: { imported: boards, skipped: Array.from({ length: skippedBoards }, (_, i) => ({ title: `d${i}`, reason: "r" })) },
});

describe("content packs", () => {
  it("names the file after the organization, folder and day", () => {
    expect(packFilename("demo25", "2026-09-29", "Billing & Rates")).toBe("originba-pack-demo25-Billing_Rates-2026-09-29.json");
    expect(packFilename("demo25", "2026-09-29", null)).toBe("originba-pack-demo25-2026-09-29.json");
  });

  it("says what a preview will do, in words", () => {
    expect(packSummary(result(["a", "b"], 1, ["x"]))).toBe("2 views and 1 dashboard will be added. 1 item will be skipped.");
    expect(packSummary(result(["a"], 0, [], 0, false))).toBe("1 view and 0 dashboards were added.");
    expect(packSummary(result([], 2, [], 1))).toBe("Nothing will be added. 3 items will be skipped.");
  });
});
