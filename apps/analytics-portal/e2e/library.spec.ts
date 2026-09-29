import { test, expect } from "@playwright/test";

/**
 * The report library is scannable: packs start folded (the page was 10,000 px tall with every
 * report open), a search opens what matches, and on a phone the title and search come before the
 * workstream rail (UI-18 in docs/PORTAL_ISSUES_LOG.md).
 */
test.beforeEach(async ({ context }, info) => {
  await context.addCookies([{ name: "portal_active_organization", value: "demo25", url: info.project.use.baseURL! }]);
});

test("packs start folded and a search opens what matches", async ({ page }) => {
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Report library" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  expect(height).toBeLessThan(4000);
  await page.getByRole("searchbox", { name: "Search the report library" }).fill("arrears");
  await expect(page.getByRole("link", { name: /arrears/i }).first()).toBeVisible();
  await expect(page.getByPlaceholder("Search processes…")).toHaveCount(0);
});

test("on a phone the title comes before the workstream rail", async ({ page }, info) => {
  test.skip(info.project.name === "desktop", "phone layout");
  await page.goto("/reports");
  const title = await page.getByRole("heading", { name: "Report library" }).boundingBox();
  const rail = await page.getByText("Workstreams", { exact: true }).first().boundingBox();
  expect(title!.y).toBeLessThan(rail!.y);
});
