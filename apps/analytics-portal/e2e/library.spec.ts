import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The report library is a folder tree: the rail lists the folders, the selected one leads with
 * its essentials and folds the rest, and one search looks across every folder. Folder and search
 * ride in the URL so a link and Back restore the view.
 */
test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

test("folders lead with their essentials and a search looks across every folder", async ({ page }) => {
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Report library" })).toBeVisible();
  const rail = page.getByRole("navigation", { name: "Report folders" });
  // by name, not position: "Your saved views" leads the rail when the reader has any
  const billing = rail.getByRole("link", { name: /^Billing & Revenue/ });
  const finance = rail.getByRole("link", { name: /^Finance & Adjustments/ });
  await expect(billing).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();

  await finance.click();
  await expect(page).toHaveURL(/[?&]folder=finance_adjustments/);
  await expect(finance).toHaveAttribute("aria-current", "page");
  await page.goBack();
  await expect(billing).toHaveAttribute("aria-current", "page");

  await page.getByRole("searchbox", { name: "Search the report library" }).fill("arrears");
  await expect(page).toHaveURL(/[?&]q=arrears/);
  await expect(page.getByRole("link", { name: /arrears/i }).first()).toBeVisible();
  // the search really filtered: a Billing essential that does not mention arrears is gone
  await expect(page.getByRole("link", { name: /What revenue was billed/i })).toHaveCount(0);
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  expect(height).toBeLessThan(4000);
});
