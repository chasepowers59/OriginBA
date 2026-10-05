import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * "Pin to dashboard → + New dashboard" opened a board with one empty "New tile" and no sign of
 * the report pinned (2026-10-05): the fresh-board effect reset the tiles on every run, so when
 * effects ran twice (Strict Mode, any remount) the pinned tile was wiped and the run-once pin
 * effect never put it back. An existing board raced two fetches the same way.
 */
test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

test("a report pinned to a new dashboard is its first tile", async ({ page }) => {
  await page.goto("/dashboards/new?pin_snapshot=rpt_gl&pin_title=QA%20pinned%20GL&pin_chart=bar");
  await expect(page).toHaveURL(/\/dashboards\/new$/, { timeout: 60_000 });
  await expect(page.getByText("QA pinned GL", { exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("New tile", { exact: true })).toHaveCount(0);
});
