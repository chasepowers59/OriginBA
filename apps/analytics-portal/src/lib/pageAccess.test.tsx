import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { NoAccess, pageOffered } from "@/components/NoAccess";

/**
 * The navigation hides a page a person may not use, but typing its address still rendered it,
 * and every call on it then failed one by one (2026-10-05, round 10). The shell now refuses the
 * whole page with the same rule the navigation uses.
 */
const NAV = [
  { id: "home" },
  { id: "letters", permission: "letters:read" },
  { id: "settings", permission: ["settings:manage", "users:manage"] as const },
  { id: "forecasts" },
];
const can = (granted: string[]) => (p: string) => granted.includes(p);

describe("pageOffered: the navigation's own rule, applied to the page being opened", () => {
  it("a page behind a permission the person lacks is not offered", () => {
    expect(pageOffered(NAV, "letters", { row_rules: [] }, can([]))).toBe(false);
    expect(pageOffered(NAV, "letters", { row_rules: [] }, can(["letters:read"]))).toBe(true);
    expect(pageOffered(NAV, "settings", { row_rules: [] }, can(["users:manage"]))).toBe(true);
    expect(pageOffered(NAV, "settings", { row_rules: [] }, can([]))).toBe(false);
  });

  it("a row-restricted reader is not offered a page row rules cannot cover", () => {
    expect(pageOffered(NAV, "forecasts", { row_rules: [{ field: "Service Type", values: ["Water"] }] }, can([]))).toBe(false);
  });

  it("a module the client does not use is not offered", () => {
    expect(pageOffered(NAV, "letters", { row_rules: [] }, can(["letters:read"]), { letters: false })).toBe(false);
  });

  it("a page outside the navigation, or no page named, is left to itself", () => {
    expect(pageOffered(NAV, undefined, { row_rules: [] }, can([]))).toBe(true);
    expect(pageOffered(NAV, "dashboard", { row_rules: [] }, can([]))).toBe(true);
  });

  it("says plainly the page is not available to this account, with the way back", () => {
    const html = renderToStaticMarkup(<NoAccess />);
    expect(html).toContain("This page isn&#x27;t available to your account");
    expect(html).toContain('href="/"');
  });
});
