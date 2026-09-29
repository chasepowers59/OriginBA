import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./apiErrors";
import { approveLetterRun, createLetterRun, fetchLetterRuns, releaseLetterRun } from "./api";
import { NO_FILTERS } from "./letters";
import {
  createRunBlocker,
  MAX_RUN_LETTERS,
  runActions,
  runErrorMessage,
  runFilters,
  runStatus,
  type LetterRun,
  type RunPermissions,
} from "./letterRuns";

const RUN = (over: Partial<LetterRun>): LetterRun => ({
  id: "0123456789abcdef0123456789abcdef", status: "draft", from: "2028-03-01", to: "2028-03-31",
  filters: { kinds: [], printed: "all" }, created_by: "a@utility.gov", created_at: "2028-04-01T10:00:00+00:00",
  created_by_you: false, approved_by: null, approved_at: null, released_by: null, released_at: null, pages: null,
  cancelled_by: null, cancelled_at: null, history: [], counts: { letters: 3, by_kind: [] }, ...over,
});

const EDITOR: RunPermissions = { generate: true, approve: true, release: true, admin: false };

describe("what each run lets you do", () => {
  it("a draft someone else created can be approved", () => {
    const a = runActions(RUN({}), EDITOR);
    expect(a.approve).toEqual({ show: true, enabled: true, reason: null });
    expect(a.release.show).toBe(false);
  });

  it("the creator sees Approve disabled with the four-eyes reason", () => {
    const a = runActions(RUN({ created_by_you: true }), EDITOR);
    expect(a.approve).toEqual({ show: true, enabled: false, reason: "You created this run, so someone else must approve it." });
    expect(a.cancel.enabled).toBe(true);
  });

  it("an approved run is released; a released one downloads again", () => {
    expect(runActions(RUN({ status: "approved" }), EDITOR).release).toEqual({ show: true, enabled: true, reason: null, label: "Release" });
    const released = runActions(RUN({ status: "released" }), EDITOR);
    expect(released.release.label).toBe("Download again");
    expect(released.approve.show).toBe(false);
    expect(released.cancel.show).toBe(false);
  });

  it("nothing is offered on a cancelled run", () => {
    const a = runActions(RUN({ status: "cancelled", created_by_you: true }), { ...EDITOR, admin: true });
    expect([a.approve.show, a.release.show, a.cancel.show]).toEqual([false, false, false]);
  });

  it("hides what the person's access does not include", () => {
    const a = runActions(RUN({ status: "approved" }), { generate: false, approve: false, release: false, admin: false });
    expect([a.approve.show, a.release.show, a.cancel.show]).toEqual([false, false, false]);
  });

  it("only the creator or an administrator cancels", () => {
    expect(runActions(RUN({}), EDITOR).cancel.show).toBe(false);
    expect(runActions(RUN({}), { ...EDITOR, admin: true }).cancel.show).toBe(true);
    expect(runActions(RUN({ status: "approved", created_by_you: true }), EDITOR).cancel.show).toBe(true);
  });
});

describe("run status", () => {
  it("reads as a state, coloured by its token pair", () => {
    expect(runStatus("draft")).toEqual({ label: "Waiting for approval", tone: "bg-warn-bg text-warn" });
    expect(runStatus("approved").label).toBe("Approved");
    expect(runStatus("released")).toEqual({ label: "Released", tone: "bg-ok-bg text-ok" });
    expect(runStatus("cancelled").label).toBe("Cancelled");
  });
});

describe("creating a run from what is shown", () => {
  it("sends only the type and status filters", () => {
    expect(runFilters({ search: "", kinds: ["reminder"], printed: "not_printed" }))
      .toEqual({ kinds: ["reminder"], printed: "not_printed" });
  });

  it("refuses when the shown letters are not what a run would hold", () => {
    expect(createRunBlocker({ ...NO_FILTERS, search: "1000" }, 4))
      .toBe("Clear the search first: a run is chosen by date, letter type and status.");
    expect(createRunBlocker(NO_FILTERS, 0)).toBe("No letters to put in a run.");
    expect(createRunBlocker(NO_FILTERS, MAX_RUN_LETTERS + 1)).toMatch(/at most 5,000 letters/);
    expect(createRunBlocker(NO_FILTERS, 12)).toBeNull();
  });
});

describe("what a refused step says", () => {
  it("passes the server's sentence through: it names the reason", () => {
    expect(runErrorMessage(new ApiError("Since this run was created, 2 letters changed in the customer system.", 409)))
      .toMatch(/2 letters changed/);
    expect(runErrorMessage("boom")).toBe("That did not work. Try again.");
  });
});

describe("the runs API calls", () => {
  afterEach(() => vi.unstubAllGlobals());

  function signedIn(response: Response) {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => response);
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", {});
    vi.stubGlobal("sessionStorage", { getItem: () => "test-token" });
    vi.stubGlobal("document", { cookie: "portal_active_organization=demo25" });
    return fetchMock;
  }

  it("lists and creates", async () => {
    let fetchMock = signedIn(new Response(JSON.stringify({ runs: [] })));
    await fetchLetterRuns();
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/portal\/letters\/runs$/);
    fetchMock = signedIn(new Response(JSON.stringify(RUN({}))));
    await createLetterRun("2028-03-01", "2028-03-31", { kinds: [], printed: "all" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/portal\/letters\/runs$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ from: "2028-03-01", to: "2028-03-31", filters: { kinds: [], printed: "all" } });
  });

  it("escapes the run id", async () => {
    const fetchMock = signedIn(new Response(JSON.stringify(RUN({}))));
    await approveLetterRun("x/../y");
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/portal\/letters\/runs\/x%2F\.\.%2Fy\/approve$/);
  });

  it("releases as one PDF, fetched with the signed-in headers and never cached", async () => {
    const fetchMock = signedIn(new Response(new Blob(["%PDF-1.4"]), { headers: { "X-Letter-Font": "Helvetica" } }));
    const blob = await releaseLetterRun("0123456789abcdef0123456789abcdef");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/runs\/0123456789abcdef0123456789abcdef\/release$/);
    expect(init?.method).toBe("POST");
    expect(init?.cache).toBe("no-store");
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer test-token");
    expect(await blob.text()).toBe("%PDF-1.4");
  });

  it("a refused release carries the server's reason and status", async () => {
    signedIn(new Response(JSON.stringify({ detail: "1 letter changed" }), { status: 409 }));
    await expect(releaseLetterRun("0123456789abcdef0123456789abcdef")).rejects.toMatchObject({ status: 409, message: "1 letter changed" });
  });
});
