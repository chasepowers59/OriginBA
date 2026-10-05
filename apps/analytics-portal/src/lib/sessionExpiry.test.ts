import { describe, expect, it } from "vitest";
import { expiredLoginUrl, endsSession } from "./sessionExpiry";

/**
 * A session that ran out mid-use left every panel reading "Invalid or expired token": the
 * client had no 401 branch, and only a page load checked the session (audit 2026-10-05).
 * A 401 on any API call now ends the session cleanly: back to sign-in, then to the same page.
 */
describe("a 401 ends the session; sign-in brings the person back", () => {
  const signedIn = { hasSession: true, page: "/explore/rpt_gl" };
  it("a 401 from a data call ends it; a refused sign-in or password check does not", () => {
    expect(endsSession(401, "/snapshots/rpt_gl/query", signedIn)).toBe(true);
    expect(endsSession(401, "/auth/me", signedIn)).toBe(true);
    expect(endsSession(401, "/auth/login", signedIn)).toBe(false);
    expect(endsSession(400, "/auth/change-password", signedIn)).toBe(false);
    expect(endsSession(403, "/portal/health", signedIn)).toBe(false);
    expect(endsSession(500, "/snapshots", signedIn)).toBe(false);
  });

  // found live 2026-10-05: the sign-in page's own calls answer 401 to a signed-out visitor,
  // and ending a session that did not exist redirected the page to itself and lost ?next=
  it("there is nothing to end without a session, or on the sign-in pages", () => {
    expect(endsSession(401, "/portal/config", { hasSession: false, page: "/dashboards" })).toBe(false);
    expect(endsSession(401, "/portal/config", { hasSession: true, page: "/login" })).toBe(false);
    expect(endsSession(401, "/portal/config", { hasSession: true, page: "/change-password" })).toBe(false);
  });

  it("returns to the page the person was on, through the same safe check as sign-in", () => {
    expect(expiredLoginUrl("/explore/rpt_gl", "?report=x")).toBe("/login?next=%2Fexplore%2Frpt_gl%3Freport%3Dx&expired=1");
    expect(expiredLoginUrl("/login", "")).toBe("/login?next=%2F&expired=1");
  });
});
