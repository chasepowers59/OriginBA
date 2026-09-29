import { test, expect } from "@playwright/test";

/**
 * The analytics assistant is Ori: "Ask Ori, your AI analytics assistant" on the home page, an
 * "Ask Ori" button on every other page that opens Ori beside it. The words come from one
 * place (src/lib/ori.ts) so every Ori surface speaks the same way.
 *
 *   npx playwright test e2e/ori.spec.ts --project=desktop
 */
const ORG = process.env.VISUAL_ORG ?? "demo25";

test.beforeEach(async ({ context }, info) => {
  await context.addCookies([{ name: "portal_active_organization", value: ORG, url: info.project.use.baseURL! }]);
});

test("home presents Ask Ori", async ({ page }) => {
  await page.goto("/");
  const ori = page.getByRole("region", { name: "Ask Ori" });
  await expect(ori).toBeVisible();
  await expect(ori.getByText("Your AI analytics assistant")).toBeVisible();
  await expect(page.getByText(/the assistant/i)).toHaveCount(0);
});

test("home has one question box: the vetted-metric form waits folded under Ori", async ({ page }) => {
  await page.goto("/");
  const form = page.getByPlaceholder("Total accounts billed by customer class…");
  await expect(form).toBeHidden();
  await page.getByText("Run a vetted metric with your own filters").click();
  await expect(form).toBeVisible();
});

test("every other page offers Ask Ori beside it", async ({ page }) => {
  await page.goto("/reports");
  await page.getByRole("button", { name: "Ask Ori" }).click();
  await expect(page.getByRole("dialog", { name: "Ask Ori" })).toBeVisible();
});
