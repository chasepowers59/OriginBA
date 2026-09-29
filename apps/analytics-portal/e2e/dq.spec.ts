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
});
