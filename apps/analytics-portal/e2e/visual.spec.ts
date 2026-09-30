import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * Pixel comparison of the key pages against a baseline, so a layout change is seen before
 * a user sees it. Runs on Ellensburg (e2e/org.ts), a frozen copy whose data does not move
 * between rebuilds; retake the baseline after a rebuild. Baselines live in
 * e2e/.out/baseline (gitignored, like every screenshot here); take them on a known-good
 * build, then compare after each change:
 *
 *   npx playwright test e2e/visual.spec.ts --update-snapshots   # take the baseline
 *   npx playwright test e2e/visual.spec.ts                      # compare against it
 *
 * Timestamps, token spend and the dev-server badge are masked: they change on every run.
 */

const PAGES = [
  "/", "/reports", "/dashboards", "/build", "/database", "/data-quality", "/settings",
  "/workstream/billing", "/workstream/finance",
  "/explore/rpt_bill_segment", "/explore/rpt_payment", "/explore/rpt_rate_configuration",
];

for (const route of PAGES) {
  test(`looks the same: ${route}`, async ({ page, context }, info) => {
    await asOrg(context, info);
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
    await page.waitForTimeout(1000);
    const name = `${route === "/" ? "home" : route.slice(1).replace(/\//g, "__")}.png`;
    await expect(page).toHaveScreenshot(name, {
      fullPage: true,
      animations: "disabled",
      caret: "hide",
      maxDiffPixelRatio: 0.002,
      mask: [
        page.locator("nextjs-portal"),
        page.locator('[data-testid="spend-line"]'),
        page.getByText(/refreshed|minutes? ago|hours? ago|seconds? ago/i),
      ],
      timeout: 30_000,
    });
  });
}
