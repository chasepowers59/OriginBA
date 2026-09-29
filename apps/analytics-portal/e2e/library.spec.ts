import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The report library is scannable: reports are grouped by workstream only (UI-4: the pack chips
 * were a second taxonomy with different counts), sections start folded (the page was 10,000 px
 * tall with every report open) and a search opens what matches (UI-18 in docs/PORTAL_ISSUES_LOG.md).
 */
test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

test("workstream sections start folded and a search opens what matches", async ({ page }) => {
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Report library" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { level: 2, name: "Billing & Rates" })).toBeVisible();
  await expect(page.getByRole("button", { name: /All packs/ })).toHaveCount(0);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  expect(height).toBeLessThan(4000);
  await page.getByRole("searchbox", { name: "Search the report library" }).fill("arrears");
  await expect(page.getByRole("link", { name: /arrears/i }).first()).toBeVisible();
  await expect(page.getByPlaceholder("Search processes…")).toHaveCount(0);
});
