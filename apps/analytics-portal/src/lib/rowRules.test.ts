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

  it("a page behind a permission is offered only to someone who holds it", () => {
    const withLetters = [{ id: "home" }, { id: "letters", permission: "letters:read" },
      { id: "settings", permission: "settings:manage" }];
    const editor = (p: string) => p === "letters:read";
    expect(visibleNav(withLetters, { row_rules: [] }, editor).map((n) => n.id)).toEqual(["home", "letters"]);
    expect(visibleNav(withLetters, { row_rules: [] }, () => false).map((n) => n.id)).toEqual(["home"]);
    expect(visibleNav(withLetters, null, () => true).map((n) => n.id)).toEqual(["home", "letters", "settings"]);
  });

  it("a page open to any of several permissions is offered to whoever holds one", () => {
    const nav = [{ id: "home" }, { id: "settings", permission: ["settings:manage", "users:manage"] }];
    const clientAdmin = (p: string) => p === "users:manage";
    expect(visibleNav(nav, { row_rules: [] }, clientAdmin).map((n) => n.id)).toEqual(["home", "settings"]);
    expect(visibleNav(nav, { row_rules: [] }, () => false).map((n) => n.id)).toEqual(["home"]);
  });

  it("letters are never offered to a restricted person, permission or not", () => {
    // api/letters/routes.py refuses them: a letter cannot be cut down to a person's rows
    const restricted = { row_rules: [{ field: "Service Type", values: ["Water"] }] };
    expect(visibleNav([{ id: "letters", permission: "letters:read" }], restricted, () => true)).toEqual([]);
  });

  it("a module the client does not use is not offered (api/client_capabilities.py)", () => {
    const withLetters = [{ id: "home" }, { id: "letters", permission: "letters:read" }];
    const ids = (modules?: Record<string, boolean>) =>
      visibleNav(withLetters, { row_rules: [] }, () => true, modules).map((n) => n.id);
    expect(ids({ letters: false })).toEqual(["home"]);
    expect(ids({ letters: true })).toEqual(["home", "letters"]);
    expect(ids(undefined)).toEqual(["home", "letters"]);   // not measured: nothing hidden
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
