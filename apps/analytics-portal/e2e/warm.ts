import type { APIRequestContext } from "@playwright/test";

const API = process.env.PORTAL_API_URL ?? "http://127.0.0.1:8010";

/**
 * A page opened while the warmer is still building its organization pays the cold cost of a
 * >1M-row data set and can time out: a false red (CityCorp 2026-10-02, /explore/rpt_bill_segment_read
 * failed in the crawl and passed alone 4 s later; the warm finished one minute after). The crawl
 * and the accessibility checks wait, bounded, for the organization's last warm before opening anything.
 */
export const WARM_WAIT_MS = 10 * 60_000;

/** The time a beforeAll that waits needs: a hook shares the 3-minute test timeout, and Ellensburg
 *  finished warming five minutes after an API restart (2026-10-05), so the wait was cut off,
 *  the first page failed and every page after it in that organization was skipped. */
export const WARM_HOOK_TIMEOUT_MS = WARM_WAIT_MS + 60_000;

export async function waitForWarm(request: APIRequestContext, org: string, maxMs = WARM_WAIT_MS): Promise<void> {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    const health = await request.get(`${API}/portal/health`).then((r) => (r.ok() ? r.json() : null)).catch(() => null);
    if (!health) return;                       // warming off, or no health route: run as before
    if (health.warmed?.[org]?.at) return;
    await new Promise((r) => setTimeout(r, 10_000));
  }
  console.warn(`${org} not warmed after ${maxMs / 60_000} min; running cold`);
}
