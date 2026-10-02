import { test, expect, type Page } from "@playwright/test";
import * as XLSX from "xlsx";
import { asOrg } from "./org";

/**
 * The explorer OPERATED, not just loaded (the crawl renders pages; this drives them):
 * every reporting period, the period comparison, a cross-filter and its removal, the sort,
 * and the Excel export with its About sheet. Run per org: E2E_ORG=citycorp ...
 *
 *   npx playwright test e2e/explorer-interactions.spec.ts
 */
const REPORT = "/explore/rpt_bill_segment?report=billed_revenue_by_type";
// the screen's line; a second copy sits in the print-only header
const shows = (page: Page) => page.getByText(/^This shows:/).filter({ visible: true }).first();

async function openReport(page: Page) {
  await page.goto(REPORT);
  await expect(shows(page)).toBeVisible({ timeout: 90_000 });
}

const noFailure = async (page: Page) =>
  expect(page.getByText(/query failed|took too long|could not be read/i)).toHaveCount(0);

test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

test("every reporting period answers, and says what it covers", async ({ page }) => {
  await openReport(page);
  for (const preset of ["Last 30 days", "Last quarter", "Prior month", "Year to date", "Last 12 months", "All dates"]) {
    const before = await shows(page).textContent();
    await page.getByRole("button", { name: preset, exact: true }).click();
    if (preset !== "Last 12 months") {   // the report opened on it: nothing to change
      await expect.poll(async () => shows(page).textContent(), { timeout: 90_000 })
        .not.toBe(before);
    }
    await noFailure(page);
    const text = (await shows(page).textContent()) ?? "";
    if (preset === "All dates") expect(text).not.toMatch(/Bill Date from/);
    else expect(text).toMatch(/Bill Date from .+ to /);
  }
});

test("comparing with the previous period names both totals", async ({ page }) => {
  await openReport(page);
  await page.getByText("Compare with the previous period").click();
  const changed = page.getByRole("region", { name: "What changed" });
  await expect(changed).toBeVisible({ timeout: 90_000 });
  await expect(changed).toContainText(/\$[\d.,]+[KMB]? vs \$[\d.,]+[KMB]?/);
  await noFailure(page);
});

test("a clicked row cross-filters the view, and the filter comes off again", async ({ page }) => {
  await openReport(page);
  const first = page.locator("table tbody tr").first();
  const name = ((await first.locator("td").first().textContent()) ?? "").trim();
  await first.click();
  await expect(page).toHaveURL(/cross_field=SA\+Type/, { timeout: 30_000 });
  await expect(shows(page)).toContainText(`SA Type is ${name}`, { timeout: 90_000 });
  await expect(page.locator("table tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: /clear (cross|drill)/i }).first().click();
  await expect(page).not.toHaveURL(/cross_field=/, { timeout: 30_000 });
  await expect.poll(async () => page.locator("table tbody tr").count(), { timeout: 90_000 }).toBeGreaterThan(1);
});

test("sorting flips the order", async ({ page }) => {
  await openReport(page);
  const amounts = async () => (await page.locator("table tbody tr td:last-child").allTextContents())
    .map((t) => Number(t.replace(/[^0-9.-]/g, "")));
  const desc = await amounts();
  expect(desc[0]).toBeGreaterThanOrEqual(desc[desc.length - 1]);
  await page.getByRole("button", { name: "Sort high → low" }).click();
  await expect(page.getByRole("button", { name: "Sort low → high" })).toBeVisible();
  const asc = await amounts();
  expect(asc[0]).toBeLessThanOrEqual(asc[asc.length - 1]);
});

test("the Excel export holds the rows and says what they are", async ({ page }) => {
  await openReport(page);
  await page.getByRole("button", { name: /^Export/ }).click();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("menuitem", { name: "Excel workbook" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/_analysis\.xlsx$/);
  const book = XLSX.read(await (await download.createReadStream()).toArray().then((c) => Buffer.concat(c)));
  expect(book.SheetNames).toContain("About this export");
  const about = XLSX.utils.sheet_to_json<{ Field: string; Value: string }>(book.Sheets["About this export"]);
  const get = (k: string) => about.find((r) => r.Field === k)?.Value ?? "";
  expect(get("Report")).toBe("What revenue was billed, by service agreement type?");
  expect(get("This shows")).toMatch(/Is Revenue Bearing: yes/);
  const rows = XLSX.utils.sheet_to_json(book.Sheets[book.SheetNames[0]]);
  expect(rows.length).toBe(Number(get("Rows").replace(/\D/g, "")));
});
