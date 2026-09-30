import { test, expect, type Page } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The builder's numbers follow the reader's last move. Every change re-runs the query after a
 * short pause, and a slower answer to an EARLIER question must never land on top of the latest
 * one: switching Total -> Average -> Total quickly has to end on the Total's numbers, labelled
 * Total (2026-09-30).
 *
 *   npx playwright test e2e/builder-modes.spec.ts
 */
async function drop(page: Page, field: string, shelfIndex: number) {
  const pill = page.getByTitle(/drag to a shelf/).filter({ has: page.getByText(field, { exact: true }) }).first();
  await expect(pill).toBeVisible({ timeout: 60_000 });
  await pill.scrollIntoViewIfNeeded();
  const from = (await pill.boundingBox())!;
  const shelf = page.getByText("Drag a field here").nth(shelfIndex);
  const to = (await shelf.boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2 + 40, from.y + from.height / 2 + 10, { steps: 6 });
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 10 });
  await page.mouse.up();
}

type Answer = { agg: string; rows: Record<string, unknown>[] };

test("switching the aggregation quickly ends on the last choice", async ({ page, context }, info) => {
  await asOrg(context, info);
  const answers: Answer[] = [];
  const asked: string[] = [];
  page.on("request", (req) => {
    if (req.url().includes("/snapshots/rpt_bill_segment/query") && req.method() === "POST") {
      asked.push(JSON.parse(req.postData() ?? "{}").measures?.[0]?.agg);
    }
  });
  page.on("response", async (res) => {
    if (!res.url().includes("/snapshots/rpt_bill_segment/query") || res.request().method() !== "POST") return;
    const agg = JSON.parse(res.request().postData() ?? "{}").measures?.[0]?.agg;
    answers.push({ agg, rows: (await res.json()).rows });
  });

  await page.goto("/build");
  await page.getByRole("button", { name: "Bill Segment", exact: true }).click();
  await drop(page, "Bill Cycle", 0);       // Columns / Group
  await drop(page, "Billed Amount", 0);    // Values: the Columns shelf is no longer empty
  await expect.poll(() => answers.filter((a) => a.agg === "sum").length, { timeout: 60_000 }).toBeGreaterThan(0);
  const total = answers.find((a) => a.agg === "sum")!.rows;

  // the Average answer is held back three seconds; the reader switches back to Total meanwhile
  await page.route("**/snapshots/rpt_bill_segment/query", async (route) => {
    const agg = JSON.parse(route.request().postData() ?? "{}").measures?.[0]?.agg;
    if (agg === "avg") await new Promise((r) => setTimeout(r, 3000));
    await route.continue();
  });
  const select = page.locator("select").filter({ has: page.locator("option", { hasText: "Average" }) }).first();
  await select.selectOption("avg");
  await page.waitForTimeout(600);          // past the builder's debounce: the Average request is out
  await select.selectOption("sum");
  await expect.poll(() => asked.includes("avg"), { timeout: 15_000 }).toBe(true);
  await page.waitForTimeout(3500);         // past the held-back Average answer, cancelled or not

  // what the page shows is the Total, not the late Average (it once read "Average Billed Amount
  // by Bill Cycle" under a Total dropdown)
  expect(await select.inputValue()).toBe("sum");
  await expect(page.getByRole("img", { name: /bar chart: Total Billed Amount by Bill Cycle/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /Average Billed Amount/ })).toHaveCount(0);
  expect(total.length).toBeGreaterThan(0);
});
