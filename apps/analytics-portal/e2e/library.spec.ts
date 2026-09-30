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

test("a folder opens as a dashboard, and a canvas of what exists now is not windowed", async ({ page }) => {
  const windows = new Map<string, boolean>();
  page.on("request", (req) => {
    const m = req.url().match(/\/snapshots\/(rpt_[a-z_]+)\/query$/);
    if (m && req.method() === "POST") {
      windows.set(m[1], (req.postDataJSON()?.filters ?? []).some((f: { op: string }) => f.op === "between"));
    }
  });
  await page.goto("/reports?folder=budget_billing");
  await page.getByRole("link", { name: "Make a dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboards\/new$/);
  await expect(page.getByText("Who is on budget billing, by customer class?")).toBeVisible();
  await expect(page.getByText("All dates").first()).toBeVisible();
  await expect.poll(() => windows.size, { timeout: 30_000 }).toBeGreaterThanOrEqual(3);
  // accounts are not "accounts opened in the last 180 days"; adjustments still are windowed
  expect(windows.get("rpt_customer_account")).toBe(false);
  expect(windows.get("rpt_financial_txn")).toBe(true);
});
