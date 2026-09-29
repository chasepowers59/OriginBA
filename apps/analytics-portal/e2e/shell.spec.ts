import { test, expect } from "@playwright/test";

/**
 * The page frame on a phone: the reader can always see whose data this is (an organization
 * chip in the header, amber when an admin views another client), and the Ask Ori button is a
 * compact icon that does not cover the page (UI-11, UI-12 in docs/PORTAL_ISSUES_LOG.md).
 *
 *   npx playwright test e2e/shell.spec.ts --project=phone
 */
test("a phone shows the organization and a compact Ask Ori button", async ({ page, context }, info) => {
  test.skip(info.project.name === "desktop", "phone layout");
  await context.addCookies([{ name: "portal_active_organization", value: "demo25", url: info.project.use.baseURL! }]);
  await page.goto("/reports");
  const chip = page.getByTestId("org-chip");
  await expect(chip).toBeVisible();
  await expect(chip).toContainText("Demo 25.4");
  const ask = page.getByRole("button", { name: "Ask Ori" });
  await expect(ask).toBeVisible();
  expect((await ask.boundingBox())!.width).toBeLessThanOrEqual(56);
});
