import type { BrowserContext, TestInfo } from "@playwright/test";

/**
 * The organization every check runs on: Ellensburg, real client data on the 25.4 TEST
 * instance (VPN). Chase, 2026-09-29: demo25 is not a comparison source. Pages show real
 * customer names, so screenshots and reports stay under the gitignored e2e/.out.
 */
export const ORG = process.env.E2E_ORG ?? "ellensburg";

export async function asOrg(context: BrowserContext, info: TestInfo, org = ORG): Promise<void> {
  await context.addCookies([{ name: "portal_active_organization", value: org, url: info.project.use.baseURL! }]);
}
