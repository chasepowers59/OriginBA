import { test, expect, type Page } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The builder OPERATED: every visual type draws the same answer, a date's grain changes the
 * buckets, and a field dragged to Filters scopes the view. Run per org: E2E_ORG=citycorp ...
 *
 *   npx playwright test e2e/builder-interactions.spec.ts
 */
async function openBill(page: Page) {
  await page.goto("/build");
  await page.getByRole("button", { name: "Bill", exact: true }).click();
  await expect(page.getByTitle(/drag to a shelf/).first()).toBeVisible({ timeout: 60_000 });
}

const pill = (page: Page, glyph: string, n = 0) =>
  page.locator('[title*="drag to a shelf"]').filter({ has: page.getByText(glyph, { exact: true }) }).nth(n);

const rowsLine = (page: Page) => page.getByText(/^(top )?\d[\d,]* rows?\b/).first();
const noFailure = async (page: Page) =>
  expect(page.getByText(/query failed|took too long|could not be read/i)).toHaveCount(0);

test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

test("every visual type draws the answer", async ({ page }) => {
  await openBill(page);
  await pill(page, "Abc").click();
  await pill(page, "#").click();
  await expect(rowsLine(page)).toBeVisible({ timeout: 90_000 });
  for (const visual of ["Bar", "Stacked", "Horizontal", "Line", "Area", "Stacked area", "Pie", "Table"]) {
    const button = page.getByRole("button", { name: new RegExp(`${visual}$`) }).first();
    if (await button.isDisabled()) continue;   // its title says why (e.g. a pie of negatives)
    await button.click();
    await noFailure(page);
    if (visual === "Table") await expect(page.locator("table").first()).toBeVisible();
    else await expect(page.locator(".recharts-surface").first()).toBeVisible({ timeout: 30_000 });
  }
});

test("a date's grain changes the buckets", async ({ page }) => {
  await openBill(page);
  await pill(page, "YMD").click();
  await pill(page, "#").click();
  await expect(rowsLine(page)).toBeVisible({ timeout: 90_000 });
  const months = await rowsLine(page).textContent();
  await page.getByTestId("shelf-columns").locator("select").first().selectOption("year");
  await expect.poll(async () => rowsLine(page).textContent(), { timeout: 90_000 }).not.toBe(months);
  await noFailure(page);
});

test("a field dragged to Filters scopes the view", async ({ page }) => {
  await openBill(page);
  await pill(page, "Abc").click();
  await expect(rowsLine(page)).toBeVisible({ timeout: 90_000 });
  // a field with a value list (Bill ID is free text and would only test the text box)
  const source = page.locator('[title*="drag to a shelf"]').filter({ hasText: /^.*Bill Status$/ }).first();
  const from = (await source.boundingBox())!;
  const to = (await page.getByTestId("shelf-filters").boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x + 40, from.y + 8, { steps: 6 });
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 14 });
  await page.mouse.up();
  const chip = page.getByTestId("shelf-filters").getByTestId("shelf-chip");
  await expect(chip).toHaveCount(1);
  await expect(chip.locator("select, input")).toBeVisible({ timeout: 60_000 });   // past "loading…"
  const select = chip.locator("select");
  if (await select.count()) {
    const values = await select.locator("option").allTextContents();
    const pick = values.find((v) => v.trim() && !/^(choose|any|all|=|—)/i.test(v.trim()));
    test.skip(!pick, "the field offers no values to filter on");
    // the re-run must carry the filter and come back answered (a capped list's row line can
    // read the same before and after, so the request is what proves the scope)
    const filtered = page.waitForResponse((r) => r.url().includes("/query") && r.request().method() === "POST"
      && JSON.stringify(r.request().postDataJSON()?.filters ?? []).includes(`"value":"${pick}"`), { timeout: 90_000 });
    await select.selectOption({ label: pick! });
    expect((await filtered).ok()).toBe(true);
  } else {
    test.skip(true, "free-text filter: no value list to pick from");
  }
  await expect(rowsLine(page)).toBeVisible({ timeout: 90_000 });
  await noFailure(page);
});
