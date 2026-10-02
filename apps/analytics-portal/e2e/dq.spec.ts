import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * Data quality rows carry an action, not a status: "Mark done" reads as something to press, is
 * at least 32 px tall, and says which row it acts on (UI-13 in docs/PORTAL_ISSUES_LOG.md).
 *
 *   npx playwright test e2e/dq.spec.ts --project=desktop
 */
test("each finding row has a Mark done button", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/data-quality");
  const mark = page.getByRole("button", { name: /^Mark .+ done$/ }).first();
  await expect(mark).toBeVisible({ timeout: 60_000 });
  await expect(mark).toContainText("Mark done");
  expect((await mark.boundingBox())!.height).toBeGreaterThanOrEqual(32);
  await expect(page.getByRole("button", { name: "Done", exact: true })).toHaveCount(0);
  // the build time reads as a date, never the raw build stamp (20260928180601:20260910084138:39)
  const header = page.getByText(/Rules run against this organization/);
  await expect(header).toContainText(/data refreshed [A-Z][a-z]{2} \d{1,2}, \d{4}/);
  await expect(header).not.toContainText(/\d{14}/);
  // both e2e organizations are frozen TEST copies with a data_as_of anchor: every "Days ..."
  // column is aged to it, and the page says so; a live organization would say nothing here
  await expect(header).toContainText(/ages counted to [A-Z][a-z]{2} \d{1,2}, \d{4}, this organization's data-as-of date/);
});
