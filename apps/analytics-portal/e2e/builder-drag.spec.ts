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
