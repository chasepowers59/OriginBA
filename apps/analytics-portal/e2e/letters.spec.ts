import { test, expect } from "@playwright/test";

/**
 * Letters for demo25 -- the one check not on Ellensburg (e2e/org.ts): letters read raw CISADM
 * and run only for Postgres organizations until the Oracle letters (phase 2) are built. Pick August 2022 (the demo warehouse has 15 letters then), see the rows,
 * choose one, and see its PDF preview. Customer names are never read or asserted here.
 *
 *   npx playwright test e2e/letters.spec.ts --project=desktop
 */
test("a letter in the window opens its PDF preview", async ({ page, context }, info) => {
  await context.addCookies([{ name: "portal_active_organization", value: "demo25", url: info.project.use.baseURL! }]);
  await page.goto("/letters");
  const from = page.getByLabel("From", { exact: true });
  await expect(from).not.toHaveValue("", { timeout: 60_000 }); // the default month is set after hydration

  await from.fill("2022-08-01");
  await page.getByLabel("To", { exact: true }).fill("2022-08-31");
  await page.getByRole("button", { name: "Show letters" }).click();

  const rows = page.locator("tbody tr");
  await expect(rows.first()).toBeVisible({ timeout: 60_000 });
  expect(await rows.count()).toBeGreaterThan(0);

  await rows.first().click();
  const preview = page.locator('iframe[title^="Letter "]');
  await expect(preview).toBeVisible({ timeout: 60_000 });
  await expect(preview).toHaveAttribute("src", /^blob:/);
  await expect(page.getByRole("button", { name: "Download PDF" })).toBeEnabled();
});

test("a window longer than the server allows is refused before it is asked", async ({ page, context }, info) => {
  await context.addCookies([{ name: "portal_active_organization", value: "demo25", url: info.project.use.baseURL! }]);
  await page.goto("/letters");
  const from = page.getByLabel("From", { exact: true });
  await expect(from).not.toHaveValue("", { timeout: 60_000 });
  const asked: string[] = [];
  page.on("request", (r) => { if (r.url().includes("/portal/letters?from=2021-01-01")) asked.push(r.url()); });

  await from.fill("2021-01-01");
  await page.getByLabel("To", { exact: true }).fill("2022-08-31");
  await page.getByRole("button", { name: "Show letters" }).click();

  // by text, not role: the router's own announcer is an alert too
  await expect(page.getByText(/at most 366 days/)).toBeVisible();
  expect(asked).toEqual([]);
});
