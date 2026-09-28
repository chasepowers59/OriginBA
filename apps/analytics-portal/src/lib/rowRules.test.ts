import { describe, expect, it } from "vitest";
import { describeRules, isRestricted, parseRuleInput, visibleNav } from "./rowRules";

const nav = [{ id: "home" }, { id: "database" }, { id: "dq" }, { id: "reports" }];

describe("row rules in the interface", () => {
  it("a restricted person is not offered what runs SQL the portal cannot restrict", () => {
    expect(visibleNav(nav, { row_rules: [{ field: "Service Type", values: ["Water"] }] }).map((n) => n.id))
      .toEqual(["home", "reports"]);
    expect(visibleNav(nav, { row_rules: [] }).map((n) => n.id)).toEqual(["home", "database", "dq", "reports"]);
    expect(isRestricted(null)).toBe(false);
  });

  it("reads as a sentence", () => {
    expect(describeRules([{ field: "Service Type", values: ["Water", "Sewer"] }])).toBe("Service Type is Water or Sewer");
    expect(describeRules([])).toBe("All rows");
  });

  it("an admin types a field and comma-separated values", () => {
    expect(parseRuleInput("Service Type", "Water, Sewer ,")).toEqual([{ field: "Service Type", values: ["Water", "Sewer"] }]);
    expect(parseRuleInput("", "Water")).toEqual([]);
    expect(parseRuleInput("Service Type", " ")).toEqual([]);
  });
});
