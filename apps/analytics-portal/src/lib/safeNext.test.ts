import { describe, expect, it } from "vitest";
import { safeNext } from "./safeNext";

/**
 * Where to go after signing in (2026-10-05). The login page sent people to `?next=` as given,
 * so a link carrying an absolute address would bounce a user off the portal straight after
 * they typed their password; and the auth provider sent every signed-in visitor of /login to
 * Home, racing the login page, so the page they were heading to was lost.
 */
describe("safeNext: only a path on this site, never back to the sign-in pages", () => {
  it("keeps a same-site path with its query", () => {
    expect(safeNext("/explore/rpt_gl")).toBe("/explore/rpt_gl");
    expect(safeNext("/build?canvas=rpt_payment&report=x")).toBe("/build?canvas=rpt_payment&report=x");
  });

  it("refuses anything that leaves the site", () => {
    for (const bad of ["https://evil.example", "//evil.example/x", "/\\evil.example", "javascript:alert(1)", "evil.example", " /x", "/%2F%2Fevil.example"]) {
      expect(safeNext(bad), bad).toBe("/");
    }
  });

  it("never returns to the sign-in or password pages, and empty means Home", () => {
    expect(safeNext("/login")).toBe("/");
    expect(safeNext("/login?next=/x")).toBe("/");
    expect(safeNext("/change-password")).toBe("/");
    expect(safeNext(null)).toBe("/");
    expect(safeNext("")).toBe("/");
  });
});
