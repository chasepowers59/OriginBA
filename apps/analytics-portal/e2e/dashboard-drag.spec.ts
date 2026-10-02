import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * Dashboard tiles move by dragging their grip onto another slot (the swap is unit-tested in
 * src/lib/dashboardSlots.test.ts; this proves the drag reaches it). The dashboard is STUBBED:
 * the store is tracked in git (data/analytics_portal/) and a test must never write to it.
 *
 *   npx playwright test e2e/dashboard-drag.spec.ts
 */
const DASH = {
  id: "qa-drag", client_id: "smartcity", title: "QA drag", days: 365, can_edit: true,
  created_at: "2026-10-01T00:00:00Z", updated_at: "2026-10-01T00:00:00Z",
  tiles: [
    { id: "t-a", slot: 0, title: "Tile Alpha", visual: "kpi", snapshot_id: "rpt_bill", measure_field: "*", measure_agg: "count" },
    { id: "t-b", slot: 1, title: "Tile Bravo", visual: "kpi", snapshot_id: "rpt_bill", measure_field: "*", measure_agg: "count" },
  ],
};

test("a dashboard tile dragged onto another slot swaps with it", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.route(/\/portal\/dashboards\/qa-drag(\?.*)?$/, (route) =>
    route.request().method() === "GET" ? route.fulfill({ json: DASH }) : route.fulfill({ json: DASH }));
  await page.goto("/dashboards/qa-drag");
  const titles = page.getByText(/^Tile (Alpha|Bravo)$/);
  await expect(titles).toHaveCount(2, { timeout: 60_000 });
  await expect(titles.nth(0)).toHaveText("Tile Alpha");

  const grips = page.getByRole("button", { name: "Drag tile to another slot" });
  const from = (await grips.nth(0).boundingBox())!;
  const to = (await grips.nth(1).boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x + 30, from.y + 20, { steps: 6 });
  await page.mouse.move(to.x + 60, to.y + 80, { steps: 14 });
  await page.mouse.up();
  await expect(titles.nth(0)).toHaveText("Tile Bravo");
  await expect(titles.nth(1)).toHaveText("Tile Alpha");
});
