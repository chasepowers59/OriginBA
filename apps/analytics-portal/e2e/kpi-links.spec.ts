import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * A KPI card opens the question that produced its number, and the builder answers it with the
 * SAME number (2026-10-01: every card opened its data set's bare page). Compared on the API's
 * own answers, not on formatted text. Run per org: E2E_ORG=citycorp ...
 *
 *   npx playwright test e2e/kpi-links.spec.ts
 */
test.beforeEach(async ({ context }, info) => {
  await asOrg(context, info);
});

for (const [ws, label] of [["billing", "Billed amount"], ["debt", "Accounts receivable"]] as const) {
  test(`the ${label} card opens its own number in the builder`, async ({ page }) => {
    const summary = page.waitForResponse((r) => r.url().includes(`/workstream-summary/${ws}`) && r.ok(), { timeout: 120_000 });
    await page.goto(`/workstream/${ws}`);
    const card = ((await (await summary).json()).kpis as { label: string; value: number }[]).find((k) => k.label === label)!;
    expect(card.value).not.toBeNull();

    const answered = page.waitForResponse((r) => r.url().includes("/query") && r.request().method() === "POST" && r.ok(), { timeout: 120_000 });
    await page.locator(".glass-panel").filter({ has: page.getByRole("heading", { name: label, exact: true }) })
      .getByRole("link", { name: /comes from|full report/ }).first().click({ timeout: 120_000 });
    await expect(page).toHaveURL(/\/build\?question=/);
    const rows = (await (await answered).json()).rows as Record<string, number>[];
    expect(rows).toHaveLength(1);
    expect(Math.abs(Number(rows[0].m0) - card.value)).toBeLessThan(0.005);
  });
}
