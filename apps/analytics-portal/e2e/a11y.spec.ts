import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import fs from "node:fs";
import path from "node:path";

/**
 * Accessibility (WCAG 2.1 A and AA) on the key pages, with axe-core. Fails on serious and
 * critical violations; every violation is written to e2e/.out/a11y/<page>.json.
 *
 *   npx playwright test e2e/a11y.spec.ts --project=desktop
 */
const ORG = process.env.VISUAL_ORG ?? "demo25";
const PAGES = ["/", "/reports", "/dashboards", "/dashboards/new", "/build", "/database", "/data-quality", "/settings",
  "/workstream/billing", "/explore/rpt_bill_segment"];

for (const route of PAGES) {
  test(`accessible: ${route}`, async ({ page, context }, info) => {
    await context.addCookies([{ name: "portal_active_organization", value: ORG, url: info.project.use.baseURL! }]);
    await page.goto(route, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
    await page.waitForTimeout(800);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .exclude("nextjs-portal")
      .analyze();
    const found = results.violations.map((v) => ({
      id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length,
      where: v.nodes.slice(0, 60).map((n) => `${n.target.join(" ")} :: ${(n.any[0]?.message ?? "").slice(0, 90)}`),
    }));
    const dir = path.join(__dirname, ".out", "a11y", info.project.name);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${route === "/" ? "home" : route.slice(1).replace(/\//g, "__")}.json`),
      JSON.stringify(found, null, 2));
    expect(found.filter((v) => v.impact === "serious" || v.impact === "critical"), "serious accessibility violations")
      .toEqual([]);
  });
}

// The admin tabs render only when clicked, so the page check above sees just the first.
for (const tab of ["Users & access", "Content packs", "System health"]) {
  test(`accessible: /settings tab ${tab}`, async ({ page, context }, info) => {
    await context.addCookies([{ name: "portal_active_organization", value: ORG, url: info.project.use.baseURL! }]);
    await page.goto("/settings", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: tab, exact: true }).click();
    await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
    await page.waitForTimeout(800);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .exclude("nextjs-portal")
      .analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => ({ id: v.id, help: v.help, where: v.nodes.slice(0, 10).map((n) => n.target.join(" ")) }));
    expect(serious, "serious accessibility violations").toEqual([]);
  });
}
