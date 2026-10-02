import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * Dragging a field in the builder shows the field under the cursor, then drops it on a shelf.
 * Chase, 2026-09-29: "I want to be able to see the outline or the actual column field that I'm
 * dragging as I am dragging it versus it just being blank" -- dnd-kit moves nothing by itself, so
 * the pill only faded where it was.
 *
 *   npx playwright test e2e/builder-drag.spec.ts
 */
test("the dragged field follows the cursor and lands on the shelf", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/build");
  await page.getByRole("button", { name: "Bill", exact: true }).click();
  const pill = page.getByTitle(/drag to a shelf/).first();
  await expect(pill).toBeVisible({ timeout: 60_000 });
  const label = (await pill.locator("span.truncate").textContent())?.trim() ?? "";
  expect(label).not.toBe("");

  const from = (await pill.boundingBox())!;
  const shelf = page.getByText("Drag a field here").first();
  const to = (await shelf.boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2 + 60, from.y + from.height / 2 + 10, { steps: 8 });

  const preview = page.getByTestId("field-drag-preview");
  await expect(preview).toBeVisible();
  await expect(preview).toContainText(label);

  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 12 });
  await page.mouse.up();
  await expect(preview).toHaveCount(0);
  await expect(page.getByText("Columns / Group").locator("xpath=../..")).toContainText(label);
});

// Chase, 2026-10-01: "when you drop down one of the canvases, you're unable to roll it back up"
test("a data set opened in the field list closes again from its own arrow", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/build");
  const bill = page.getByRole("button", { name: "Bill", exact: true });
  await bill.click();
  await expect(bill).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByTitle(/drag to a shelf/).first()).toBeVisible({ timeout: 60_000 });
  await bill.click();
  await expect(bill).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByTitle(/drag to a shelf/)).toHaveCount(0);
  await bill.click();                                   // and opens again
  await expect(bill).toHaveAttribute("aria-expanded", "true");
});

// Chase, 2026-10-01: "when you bring a column or field or group into the view, you're unable to
// rearrange them" -- a chip on a shelf moves by dragging its grip
test("fields on a shelf rearrange by drag and drop", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/build");
  await page.getByRole("button", { name: "Bill", exact: true }).click();
  const pills = page.getByTitle(/drag to a shelf/);
  await expect(pills.first()).toBeVisible({ timeout: 60_000 });
  const dims = page.locator('[title*="drag to a shelf"]').filter({ has: page.getByText("Abc", { exact: true }) });
  const first = (await dims.nth(0).locator("span.truncate").textContent())!.trim();
  const second = (await dims.nth(1).locator("span.truncate").textContent())!.trim();
  await dims.nth(0).click();                            // click adds to its shelf
  await dims.nth(1).click();
  const shelf = page.getByTestId("shelf-columns");
  const chips = shelf.getByTestId("shelf-chip");
  await expect(chips).toHaveCount(2);
  await expect(chips.nth(0)).toContainText(first);

  const grip = chips.nth(1).getByRole("button", { name: `Move ${second}` });
  const from = (await grip.boundingBox())!;
  const to = (await chips.nth(0).boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x - 20, from.y + 4, { steps: 6 });
  await page.mouse.move(to.x + 6, to.y + to.height / 2, { steps: 12 });
  await page.mouse.up();
  await expect(chips.nth(0)).toContainText(second);
  await expect(chips.nth(1)).toContainText(first);
});
