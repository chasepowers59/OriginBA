import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * Letters on Ellensburg (e2e/org.ts): raw CISADM read through the org's own Oracle connection.
 * May 2026 is the last complete month before its data_as_of (2026-06-18) and holds about 3,200
 * letters; a cold month takes tens of seconds over the VPN. See the rows, choose one, and see its
 * PDF preview. Customer names are never read or asserted here.
 *
 *   npx playwright test e2e/letters.spec.ts --project=desktop
 */
const LOAD = { timeout: 150_000 };

test("a letter in the window opens its PDF preview", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/letters");
  // it opens on the last full month the data covers (as of 2026-06-18), not the viewer's last month
  await expect(page.getByLabel("From", { exact: true })).toHaveValue("2026-05-01", { timeout: 60_000 });
  await expect(page.getByLabel("To", { exact: true })).toHaveValue("2026-05-31");

  const rows = page.locator("tbody tr");
  await expect(rows.first()).toBeVisible(LOAD);
  expect(await rows.count()).toBeGreaterThan(0);

  await rows.first().click();
  const preview = page.locator('iframe[title^="Letter "]');
  await expect(preview).toBeVisible({ timeout: 60_000 });
  await expect(preview).toHaveAttribute("src", /^blob:/);
  await expect(page.getByRole("button", { name: "Download PDF" })).toBeEnabled();
});

test("a window longer than the server allows is refused before it is asked", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/letters");
  const from = page.getByLabel("From", { exact: true });
  await expect(from).not.toHaveValue("", { timeout: 60_000 });
  const asked: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/portal/letters?from=2025-01-01")) asked.push(r.url()); });

  await from.fill("2025-01-01");
  await page.getByLabel("To", { exact: true }).fill("2026-05-31");
  await page.getByRole("button", { name: "Show letters" }).click();

  // by text, not role: the router's own announcer is an alert too
  await expect(page.getByText(/at most 366 days/)).toBeVisible();
  expect(asked).toEqual([]);
});
