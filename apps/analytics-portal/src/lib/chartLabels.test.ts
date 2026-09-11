import { describe, expect, it } from "vitest";
import { categoryLabel } from "./chartLabels";

/**
 * A chart category is a business value, rendered like a table cell. BuilderChart used
 * String(value ?? "—"), so a boolean dimension -- "Service off but installed" by
 * "Installed But Switched Off" -- drew bars labelled "true" and "false" while the
 * table beside it said True / False (demo25, 2026-09-04).
 */
describe("categoryLabel", () => {
  it("renders a boolean as a state, like the table", () => {
    expect(categoryLabel(true)).toBe("True");
    expect(categoryLabel(false)).toBe("False");
  });
  it("renders a missing category as a dash, not an empty axis slot", () => {
    expect(categoryLabel(null)).toBe("—");
    expect(categoryLabel(undefined)).toBe("—");
    expect(categoryLabel("")).toBe("—");
  });
  it("leaves text and numbers as they are", () => {
    expect(categoryLabel("Residential")).toBe("Residential");
    expect(categoryLabel(2026)).toBe("2026");
  });
});
