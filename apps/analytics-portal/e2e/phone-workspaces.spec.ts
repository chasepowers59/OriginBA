import { test, expect } from "@playwright/test";

/**
 * On a phone the SQL workspace stacks at natural height, so its results get real room (they were
 * ~50 px, squeezed into one screen with the table list and the editor), and the builder's empty
 * state does not say "on the left" when its table picker is above (UI-19).
 *
 *   npx playwright test e2e/phone-workspaces.spec.ts --project=phone
 */
test.beforeEach(async ({ context }, info) => {
  test.skip(info.project.name === "desktop", "phone layout");
  await context.addCookies([{ name: "portal_active_organization", value: "demo25", url: info.project.use.baseURL! }]);
});

test("the SQL workspace gives its results real room", async ({ page }) => {
  await page.goto("/database");
  const results = page.getByTestId("sql-results");
  await expect(results).toBeVisible({ timeout: 60_000 });
  expect((await results.boundingBox())!.height).toBeGreaterThanOrEqual(280);
});

test("the builder's empty state does not depend on the layout", async ({ page }) => {
  await page.goto("/build");
  await expect(page.getByText(/Pick a table/).first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/on the left/)).toHaveCount(0);
});
