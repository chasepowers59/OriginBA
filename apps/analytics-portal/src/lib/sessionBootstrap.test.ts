import { describe, expect, it, vi } from "vitest";
import { loadSession } from "./sessionBootstrap";

const user = { email: "a@b.c" } as never;
const deps = (over: Partial<Parameters<typeof loadSession>[0]> = {}) => ({
  authDisabled: false,
  hasToken: true,
  fetchStatus: vi.fn().mockResolvedValue({ enabled: true }),
  fetchUser: vi.fn().mockResolvedValue(user),
  clear: vi.fn(),
  ...over,
});

/**
 * The session bootstrap always settles. Awaiting /auth/status outside any try left the page on
 * "Loading session…" forever when the API could not be reached: the first production deploy
 * (2026-09-30, no API hosted yet) and any outage after it.
 */
describe("loadSession", () => {
  it("signs in the person holding a token", async () => {
    expect(await loadSession(deps())).toEqual({ enabled: true, user, unreachable: false });
  });

  it("says the service cannot be reached instead of waiting forever", async () => {
    const d = deps({ fetchStatus: vi.fn().mockRejectedValue(new TypeError("Failed to fetch")) });
    expect(await loadSession(d)).toEqual({ enabled: true, user: null, unreachable: true });
  });

  it("an expired token signs out rather than failing the page", async () => {
    const d = deps({ fetchUser: vi.fn().mockRejectedValue(new Error("401")) });
    expect(await loadSession(d)).toEqual({ enabled: true, user: null, unreachable: false });
    expect(d.clear).toHaveBeenCalled();
  });

  it("no token means the sign-in page, with no user call", async () => {
    const d = deps({ hasToken: false });
    expect(await loadSession(d)).toEqual({ enabled: true, user: null, unreachable: false });
    expect(d.fetchUser).not.toHaveBeenCalled();
  });

  it("open access still has its user, and an unreachable one is said so", async () => {
    expect(await loadSession(deps({ authDisabled: true }))).toEqual({ enabled: false, user, unreachable: false });
    const d = deps({ authDisabled: true, fetchUser: vi.fn().mockRejectedValue(new TypeError("Failed to fetch")) });
    expect(await loadSession(d)).toEqual({ enabled: false, user: null, unreachable: true });
  });
});
