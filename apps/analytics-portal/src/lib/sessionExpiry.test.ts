import { describe, expect, it } from "vitest";
import { expiredLoginUrl, endsSession } from "./sessionExpiry";

/**
 * A session that ran out mid-use left every panel reading "Invalid or expired token": the
 * client had no 401 branch, and only a page load checked the session (audit 2026-10-05).
 * A 401 on any API call now ends the session cleanly: back to sign-in, then to the same page.
 */
describe("a 401 ends the session; sign-in brings the person back", () => {
  it("a 401 from a data call ends it; a refused sign-in or password check does not", () => {
    expect(endsSession(401, "/snapshots/rpt_gl/query")).toBe(true);
    expect(endsSession(401, "/auth/me")).toBe(true);
    expect(endsSession(401, "/auth/login")).toBe(false);
    expect(endsSession(400, "/auth/change-password")).toBe(false);
    expect(endsSession(403, "/portal/health")).toBe(false);
    expect(endsSession(500, "/snapshots")).toBe(false);
  });

  it("returns to the page the person was on, through the same safe check as sign-in", () => {
    expect(expiredLoginUrl("/explore/rpt_gl", "?report=x")).toBe("/login?next=%2Fexplore%2Frpt_gl%3Freport%3Dx&expired=1");
    expect(expiredLoginUrl("/login", "")).toBe("/login?next=%2F&expired=1");
  });
});
