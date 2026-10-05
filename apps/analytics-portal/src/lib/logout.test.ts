import { afterEach, describe, expect, it, vi } from "vitest";
import { logout } from "./authApi";

// Sign-out used to clear only the browser, so a copied token kept working until it expired.
describe("logout", () => {
  afterEach(() => vi.unstubAllGlobals());

  function browser(fetchImpl: (url: string, init?: RequestInit) => Promise<Response>) {
    const store = new Map([["portal_access_token", "t0k3n"]]);
    const calls: string[] = [];
    vi.stubGlobal("window", {});
    vi.stubGlobal("document", { cookie: "" });
    vi.stubGlobal("sessionStorage", {
      getItem: (k: string) => store.get(k) ?? null,
      removeItem: (k: string) => { calls.push(`clear ${k}`); store.delete(k); },
    });
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${String(url).replace(/^https?:\/\/[^/]+/, "")}`);
      return fetchImpl(url, init);
    }));
    return calls;
  }

  it("retires the session on the server, with its token, before clearing the browser", async () => {
    const calls = browser(async () => new Response(JSON.stringify({ signed_out: true })));
    await logout();
    expect(calls[0]).toBe("POST /auth/logout");
    expect(calls.indexOf("clear portal_access_token")).toBeGreaterThan(0);
    const [, init] = (fetch as unknown as { mock: { calls: [string, RequestInit][] } }).mock.calls[0];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer t0k3n");
  });

  it("still clears the browser when the server cannot be reached", async () => {
    const calls = browser(async (url) => {
      if (String(url).endsWith("/auth/logout")) throw new TypeError("Failed to fetch");
      return new Response(null, { status: 204 });
    });
    await logout();
    expect(calls).toContain("clear portal_access_token");
  });
});
