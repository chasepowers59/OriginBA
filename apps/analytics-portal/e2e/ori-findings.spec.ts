import { test, expect } from "@playwright/test";

/**
 * "Ori found something worth investigating": the large moves in the home cards, each with a
 * one-click follow-up to Ori. The findings response is stubbed so the test does not depend on
 * the demo data moving 25% this month (the rules are pinned in tests/test_ori_insights.py).
 */
const FINDING = {
  kpi_id: "billed_revenue", change_pct: -32,
  headline: "Billed revenue is down 32% vs prior 30 days",
  detail: "$700.00 now, $1,030.00 before.",
  question: "Why is Billed revenue down 32% vs prior 30 days? What changed?",
};

test.beforeEach(async ({ context }, info) => {
  await context.addCookies([{ name: "portal_active_organization", value: "demo25", url: info.project.use.baseURL! }]);
});

test("home shows Ori's findings and hands the question to Ori", async ({ page }) => {
  await page.route("**/portal/ori/findings", (route) => route.fulfill({ json: { findings: [FINDING] } }));
  await page.route("**/portal/assistant/stream", (route) => route.abort());
  await page.goto("/");
  const card = page.getByRole("region", { name: "Ori found something worth investigating" });
  await expect(card).toBeVisible();
  await expect(card.getByText(FINDING.headline)).toBeVisible();
  await expect(card.getByText(FINDING.detail)).toBeVisible();
  await card.getByRole("button", { name: "Ask Ori why" }).click();
  await expect(page.getByRole("region", { name: "Ask Ori" }).getByText(FINDING.question)).toBeVisible();
});

test("no findings, no card", async ({ page }) => {
  await page.route("**/portal/ori/findings", (route) => route.fulfill({ json: { findings: [] } }));
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Ask Ori" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Ori found something worth investigating" })).toHaveCount(0);
});
