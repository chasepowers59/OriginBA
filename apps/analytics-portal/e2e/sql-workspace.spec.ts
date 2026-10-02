import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * "Open in SQL →" on a data set page lands in the SQL workspace with a browse query that RUNS
 * on this organization's engine. On 2026-10-02 CityCorp (Oracle, in-database) was seeded the
 * Postgres form and Run answered ORA-00907. Run per org: E2E_ORG=citycorp ...
 */
test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

test("Open in SQL seeds a browse query that runs on this organization's engine", async ({ page }) => {
  await page.goto("/explore/rpt_payment");
  await page.getByRole("link", { name: /Open in SQL/ }).click({ timeout: 120_000 });
  await expect(page).toHaveURL(/\/database\?table=rpt_payment/, { timeout: 60_000 });
  const editor = page.getByRole("textbox", { name: /starter query|SELECT/ });
  await expect(editor).toHaveValue(/rpt_payment/, { timeout: 60_000 });
  const answered = page.waitForResponse((r) => r.url().includes("/database/") && r.request().method() === "POST", { timeout: 120_000 });
  await page.getByRole("button", { name: "Run", exact: true }).click();
  expect((await answered).ok()).toBe(true);
  await expect(page.getByText(/Query failed/)).toHaveCount(0);
  await expect(page.getByRole("table")).toBeVisible({ timeout: 60_000 });
});
