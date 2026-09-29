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

/**
 * Runs. The live test creates a run from a one-day window on Ellensburg, sees it waiting for
 * approval with the creator's Approve disabled (four eyes: open access signs everyone in as the
 * same developer, who created it), then cancels it so nothing is left open. Approve and release are
 * never done against real data here: the second test drives them with stubbed answers and invented
 * letters.
 */
test("a run is created from the letters shown and its creator cannot approve it", async ({ page, context }, info) => {
  await asOrg(context, info);
  await page.goto("/letters");
  await expect(page.getByLabel("From", { exact: true })).not.toHaveValue("", { timeout: 60_000 });
  await page.getByLabel("From", { exact: true }).fill("2026-05-01");
  await page.getByLabel("To", { exact: true }).fill("2026-05-01");
  await page.getByRole("button", { name: "Show letters" }).click();
  await expect(page.locator("section[aria-label='Letters in this window'] tbody tr").first()).toBeVisible(LOAD);

  await page.getByRole("button", { name: /^Create run from (these [\d,]+ letters|this letter)$/ }).click();
  const run = page.getByRole("table", { name: "Letter runs" }).locator("tbody tr").first();
  await expect(run.getByText("Waiting for approval")).toBeVisible(LOAD);
  await expect(run.getByText("May 1, 2026 – May 1, 2026")).toBeVisible();
  const approve = run.getByRole("button", { name: "Approve" });
  await expect(approve).toBeDisabled();
  await expect(approve).toHaveAccessibleDescription("You created this run, so someone else must approve it.");

  await run.getByRole("button", { name: "Cancel run" }).click();
  await expect(run.getByText("Cancelled")).toBeVisible();
});

test("approving and releasing a run (stubbed answers, invented letters)", async ({ page, context }, info) => {
  await asOrg(context, info);
  const base = {
    from: "2028-03-01", to: "2028-03-31", filters: { kinds: [], printed: "all" }, created_by: "a@utility.gov",
    created_at: "2028-04-01T10:00:00+00:00", created_by_you: false, approved_by: null, approved_at: null,
    released_by: null, released_at: null, pages: null, cancelled_by: null, cancelled_at: null, history: [],
    counts: { letters: 2, by_kind: [{ kind: "reminder", label: "Past due reminder", count: 2 }] },
  };
  let run: Record<string, unknown> = { ...base, id: "0123456789abcdef0123456789abcdef", status: "draft" };
  const letter = (id: string) => ({
    letter_id: id, kind: "reminder", kind_label: "Past due reminder", template_code: "T", contact_type: "R",
    letter_date: "2028-03-08", account_id: "1000000001", recipient: "Rivera,Alex", amount: "10.00",
    process_type: "Collection", process_id: "1", next_action_on: null, printed: false, copies: 1,
  });
  await page.route("**/portal/letters/as-of", (r) => r.fulfill({ json: { data_as_of: "2028-04-18" } }));
  await page.route((u) => u.pathname.endsWith("/portal/letters"), (r) =>
    r.fulfill({ json: { organization_id: "x", from: "2028-03-01", to: "2028-03-31", count: 2,
      letters: [letter("CC-1"), letter("CC-2")] } }));
  await page.route("**/portal/letters/runs", (r) => r.fulfill({ json: { organization_id: "x", runs: [run] } }));
  await page.route("**/portal/letters/runs/*/approve", (r) => {
    run = { ...run, status: "approved", approved_by: "b@utility.gov", approved_at: "2028-04-02T09:00:00+00:00" };
    return r.fulfill({ json: run });
  });
  await page.route("**/portal/letters/runs/*/release", (r) => {
    run = { ...run, status: "released", released_by: "b@utility.gov", released_at: "2028-04-02T09:05:00+00:00", pages: 2 };
    return r.fulfill({ body: "%PDF-1.4 stub", contentType: "application/pdf" });
  });

  await page.goto("/letters");
  const row = page.getByRole("table", { name: "Letter runs" }).locator("tbody tr").first();
  await expect(row.getByText("Waiting for approval")).toBeVisible(LOAD);
  await row.getByRole("button", { name: "Approve" }).click();
  await expect(row.getByText("Approved", { exact: true })).toBeVisible();
  await expect(row.getByText("b@utility.gov")).toBeVisible();

  const download = page.waitForEvent("download");
  await row.getByRole("button", { name: "Release" }).click();
  expect((await download).suggestedFilename()).toBe("letter-run-2028-03-01-01234567.pdf");
  await expect(row.getByText("Released", { exact: true })).toBeVisible();
  await expect(row.getByRole("button", { name: "Download again" })).toBeEnabled();
});
