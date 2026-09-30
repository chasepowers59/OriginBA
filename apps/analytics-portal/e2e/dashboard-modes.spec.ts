import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The dashboards follow the reader's last choice. Switching 30 -> 90 -> 30 days quickly must end
 * on the 30-day numbers: a slower 90-day answer arriving last used to replace them (2026-09-30),
 * the same fault the builder had (e2e/builder-modes.spec.ts).
 *
 *   npx playwright test e2e/dashboard-modes.spec.ts
 */
test("switching the window quickly ends on the last choice", async ({ page, context }, info) => {
  await asOrg(context, info);
  const asked: string[] = [];
  const answered: string[] = [];
  page.on("requestfinished", (req) => {
    if (req.url().includes("/snapshots/executive-summary")) answered.push(new URL(req.url()).searchParams.get("days") ?? "");
  });
  page.on("request", (req) => {
    if (req.url().includes("/snapshots/executive-summary")) asked.push(new URL(req.url()).searchParams.get("days") ?? "");
  });
  await page.goto("/");
  await expect(page.getByText(/^Last 30 days to /)).toBeVisible({ timeout: 90_000 });

  // the 90-day answer is held back four seconds; the reader goes back to 30 days meanwhile
  await page.route("**/snapshots/executive-summary**", async (route) => {
    if (new URL(route.request().url()).searchParams.get("days") === "90") await new Promise((r) => setTimeout(r, 4000));
    await route.continue();
  });
  await page.getByRole("button", { name: "90 days", exact: true }).first().click();
  await expect.poll(() => asked.includes("90"), { timeout: 15_000 }).toBe(true);
  await page.getByRole("button", { name: "30 days", exact: true }).first().click();
  await expect.poll(() => answered.includes("90"), { timeout: 60_000 }).toBe(true);   // the late answer is in
  await page.waitForTimeout(500);

  await expect(page.getByText(/^Last 30 days to /)).toBeVisible();
  await expect(page.getByText(/^Last 90 days to /)).toHaveCount(0);
});
