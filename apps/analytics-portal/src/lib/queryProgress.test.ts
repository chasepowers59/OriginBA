import { afterEach, describe, expect, it, vi } from "vitest";
import { runSnapshotQuery } from "./api";
import { runningLabel } from "./queryProgress";

// Ellensburg's slow explorer pages (17-32 s) showed only a grey skeleton: no sign the
// query was alive and no way to stop it.
describe("runningLabel", () => {
  it("stays quiet for the first two seconds", () => {
    expect(runningLabel(0)).toBeNull();
    expect(runningLabel(1999)).toBeNull();
  });

  it("then counts whole elapsed seconds", () => {
    expect(runningLabel(2000)).toBe("Running… 2s");
    expect(runningLabel(17_900)).toBe("Running… 17s");
  });
});

describe("runSnapshotQuery cancellation", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("hands the caller's AbortSignal to fetch, so Cancel stops the request", async () => {
    const fetchMock = vi.fn((_url: string, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      }));
    vi.stubGlobal("fetch", fetchMock);
    const ctl = new AbortController();
    const pending = runSnapshotQuery("rpt_billed_usage", { dimensions: [], measures: [], filters: [], limit: 500 }, ctl.signal);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(fetchMock.mock.calls[0][1]?.signal).toBe(ctl.signal);
    ctl.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
});
