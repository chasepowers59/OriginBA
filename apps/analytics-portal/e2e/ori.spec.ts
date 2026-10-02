import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The analytics assistant is Ori: "Ask Ori, your AI analytics assistant" on the home page, an
 * "Ask Ori" button on every other page that opens Ori beside it. The words come from one
 * place (src/lib/ori.ts) so every Ori surface speaks the same way.
 *
 *   npx playwright test e2e/ori.spec.ts --project=desktop
 */

test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
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
  // the folded form lists the metrics it answers; choosing one runs it, no model call
  const picker = page.getByRole("combobox", { name: "Choose a metric" });
  await expect(picker).toBeVisible({ timeout: 30_000 });
  const answered = page.waitForResponse((r) => r.url().includes("/analytics-nlq") && r.request().method() === "POST", { timeout: 120_000 });
  await picker.selectOption({ label: "Total customer accounts" });
  expect((await answered).ok()).toBe(true);
  await expect(form).toHaveValue(/.+/);
});

test("every other page offers Ask Ori beside it", async ({ page }) => {
  await page.goto("/reports");
  await page.getByRole("button", { name: "Ask Ori" }).click();
  await expect(page.getByRole("dialog", { name: "Ask Ori" })).toBeVisible();
});
