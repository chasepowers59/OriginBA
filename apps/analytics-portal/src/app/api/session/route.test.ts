import { describe, expect, it, vi } from "vitest";

/**
 * H6 (2026-09-01): the access token was written to a JS-readable cookie.
 *
 * `storeAccessToken` set `portal_access_token` with document.cookie — no HttpOnly,
 * 48-hour max-age, no revocation — so any XSS lifted a token valid for the token's
 * full life. The cookie exists only so Next's SSR can forward Authorization to the
 * API, which does not need JS to be able to read it. This same-origin route sets it
 * HttpOnly instead.
 */

const setCalls: Array<[string, string, Record<string, unknown>]> = [];
const deleteCalls: string[] = [];

vi.mock("next/headers", () => ({
  cookies: async () => ({
    set: (name: string, value: string, opts: Record<string, unknown>) => {
      setCalls.push([name, value, opts]);
    },
    delete: (name: string) => {
      deleteCalls.push(name);
    },
  }),
}));

const { POST, DELETE } = await import("./route");

const post = (body: unknown) =>
  POST(new Request("http://localhost/api/session", {
    method: "POST",
    body: JSON.stringify(body),
  }));

describe("session cookie route", () => {
  it("sets the token cookie HttpOnly, and never exposes it to JS", async () => {
    setCalls.length = 0;
    const res = await post({ token: "jwt-value", maxAge: 8 * 3600 });
    expect(res.status).toBe(204);
    const [name, value, opts] = setCalls[0];
    expect(name).toBe("portal_access_token");
    expect(value).toBe("jwt-value");
    expect(opts.httpOnly).toBe(true);
    expect(opts.sameSite).toBe("lax");
    expect(opts.path).toBe("/");
  });

  it("never outlives the token it carries", async () => {
    setCalls.length = 0;
    await post({ token: "jwt", maxAge: 8 * 3600 });
    expect(setCalls[0][2].maxAge).toBe(8 * 3600);
    // and an absurd lifetime is clamped rather than trusted
    setCalls.length = 0;
    await post({ token: "jwt", maxAge: 60 * 60 * 24 * 30 });
    expect(setCalls[0][2].maxAge as number).toBeLessThanOrEqual(24 * 3600);
  });

  it("refuses a request with no token", async () => {
    const res = await post({});
    expect(res.status).toBe(400);
  });

  it("clears the cookie on DELETE", async () => {
    deleteCalls.length = 0;
    const res = await DELETE();
    expect(res.status).toBe(204);
    expect(deleteCalls).toContain("portal_access_token");
  });
});
