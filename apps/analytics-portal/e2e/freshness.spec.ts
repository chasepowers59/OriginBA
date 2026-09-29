import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * Every page says when the reporting data stopped refreshing: Ellensburg's tables sat 19 days old
 * (2026-09-29) with no page saying so. Live Ellensburg was rebuilt that day, so it shows no notice;
 * a stale answer is stubbed to show the notice.
 *
 *   npx playwright test e2e/freshness.spec.ts
 */
test("fresh data shows no notice", async ({ page, context }, info) => {
  await asOrg(context, info);
  const answered = page.waitForResponse((r) => r.url().includes("/portal/freshness"));
  await page.goto("/reports");
  await answered;
  await expect(page.getByTestId("stale-data")).toHaveCount(0);
});

test("stale data is named on every page", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.route("**/portal/freshness", (route) =>
    route.fulfill({ json: { built_at: "2026-09-10T08:41:38-04:00", age_hours: 462.3, stale: true } }));
  for (const path of ["/", "/reports", "/data-quality"]) {
    await page.goto(path);
    const notice = page.getByTestId("stale-data");
    await expect(notice).toContainText("Reporting data was last refreshed Sep 10, 2026");
    await expect(notice).toContainText("(19 days ago)");
  }
});
