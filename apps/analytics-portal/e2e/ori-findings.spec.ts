import { test, expect, type Page } from "@playwright/test";

/**
 * Ori's read on home: the brief, what is worth investigating (large moves in the home cards and
 * unusual months), and where each card is heading, each with a one-click question to Ori. Both
 * responses are stubbed so the test does not depend on Ellensburg's data moving this month (the
 * rules are pinned in tests/test_ori_insights.py).
 */
const FINDING = {
  kpi_id: "billed_revenue", change_pct: -17.9,
  headline: "Billed revenue is down 18% vs prior 30 days",
  detail: "$3,342,118.20 now, $4,071,002.11 before.",
  question: "Why is Billed revenue down 18% vs prior 30 days? What changed?",
};

const BRIEF =
  "In the last 30 days to Jun 18, 2026, billed revenue fell 18% against the 30 days before. Payments rose 9%.";

const ANOMALY = {
  kpi_id: "billed_revenue", month: "2026-05", direction: "low",
  headline: "Billed revenue for May 2026 was unusually low",
  detail: "$1,212,408.55, below every one of the 12 months before ($2,904,117.20 to $3,611,845.02; typical $3,240,560.18).",
  question: "Why was billed revenue so low in May 2026? What changed from the months before?",
};

const HISTORY = ["2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
  "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"].map((month, i) => ({ month, value: 3_900_000 + i * 25_000 }));

const FORECAST = {
  kpi_id: "billed_revenue", label: "Billed revenue", format: "currency",
  history: HISTORY,
  forecast: [
    { month: "2026-06", value: 4_200_000, low: 3_900_000, high: 4_500_000 },
    { month: "2026-07", value: 4_200_000, low: 3_900_000, high: 4_500_000 },
    { month: "2026-08", value: 4_200_000, low: 3_900_000, high: 4_500_000 },
  ],
  total: 12_600_000, total_low: 11_700_000, total_high: 13_500_000, typical_error_pct: 6.2, checks: 24,
  headline: "Billed revenue: about $12,600,000.00 over Jun to Aug 2026",
  detail: "Likely between $11,700,000.00 and $13,500,000.00.",
  question: "What is driving the billed revenue projection for Jun to Aug 2026?",
};

async function stubOri(page: Page, read: object, trends: object) {
  await page.route("**/portal/ori/findings", (route) => route.fulfill({ json: read }));
  await page.route("**/portal/ori/trends", (route) => route.fulfill({ json: trends }));
  await page.route("**/portal/assistant/stream", (route) => route.abort());
}

test.beforeEach(async ({ context }, info) => {
  await context.addCookies([{ name: "portal_active_organization", value: "ellensburg", url: info.project.use.baseURL! }]);
});

test("home shows Ori's read and hands a finding's question to Ori", async ({ page }) => {
  await stubOri(page, { findings: [FINDING], brief: BRIEF }, { through: "2026-05", anomalies: [ANOMALY], forecasts: [FORECAST] });
  await page.goto("/");
  const panel = page.getByRole("region", { name: "Ori's read" });
  await expect(panel.getByText(BRIEF)).toBeVisible();
  const found = panel.getByRole("region", { name: "Ori found something worth investigating" });
  await expect(found.getByText(FINDING.headline)).toBeVisible();
  await expect(found.getByText(FINDING.detail)).toBeVisible();
  await expect(found.getByText(ANOMALY.headline)).toBeVisible();
  await found.getByRole("button", { name: "Ask Ori why" }).first().click();
  await expect(page.getByRole("region", { name: "Ask Ori" }).getByText(FINDING.question)).toBeVisible();
});

test("where it's heading: the projection, its chart, and a question to Ori", async ({ page }) => {
  await stubOri(page, { findings: [] }, { through: "2026-05", anomalies: [], forecasts: [FORECAST] });
  await page.goto("/");
  const heading = page.getByRole("region", { name: "Where it's heading" });
  await expect(heading.getByText(FORECAST.headline)).toBeVisible();
  await expect(heading.getByRole("img", { name: "Billed revenue by month: actual, then projected" })).toBeVisible();
  await expect(heading.locator(".recharts-line")).toHaveCount(2);
  await expect(heading.getByText("A projection from past months, not a promise.")).toBeVisible();
  await heading.getByRole("button", { name: "Ask Ori about this" }).click();
  await expect(page.getByRole("region", { name: "Ask Ori" }).getByText(FORECAST.question)).toBeVisible();
});

test("while the trends load Ori says it is looking; a failed trends request shows nothing for them", async ({ page }) => {
  let release: () => void = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/portal/ori/findings", (route) => route.fulfill({ json: { findings: [FINDING] } }));
  await page.route("**/portal/ori/trends", async (route) => {
    await held;
    await route.fulfill({ status: 500, json: { detail: "boom" } });
  });
  await page.goto("/");
  const panel = page.getByRole("region", { name: "Ori's read" });
  await expect(panel.getByRole("status")).toHaveText("Ori is analyzing your data…");
  release();
  await expect(panel.getByRole("status")).toHaveCount(0);
  await expect(panel.getByText(FINDING.headline)).toBeVisible();
  await expect(panel.getByRole("region", { name: "Where it's heading" })).toHaveCount(0);
});

test("nothing to say, no panel", async ({ page }) => {
  await stubOri(page, { findings: [], brief: null }, { through: "2026-05", anomalies: [], forecasts: [] });
  await Promise.all([page.waitForResponse("**/portal/ori/trends"), page.goto("/")]);
  await expect(page.getByRole("region", { name: "Ask Ori" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Ori's read" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Ori found something worth investigating" })).toHaveCount(0);
});
