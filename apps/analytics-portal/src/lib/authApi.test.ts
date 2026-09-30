import { afterEach, describe, expect, it, vi } from "vitest";
import { listPortalOrganizations } from "./authApi";

/**
 * The org list is fetched once per page, not once per mount. OrgSwitcher is mounted
 * twice in AppShell (desktop header and the mobile drawer) and each mount fetched
 * /auth/organizations -- five requests for one list on a single home-page load in the
 * dev log, three in production. The list changes when an admin edits organizations,
 * which is not something a header re-render should re-ask about.
 */
describe("listPortalOrganizations", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shares one request across concurrent callers", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify([{ id: "dev", display_name: "Dev" }]),
      { status: 200, headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    const [a, b, c] = await Promise.all([listPortalOrganizations(), listPortalOrganizations(), listPortalOrganizations()]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(a).toEqual(b);
    expect(c[0].id).toBe("dev");
  });
});
