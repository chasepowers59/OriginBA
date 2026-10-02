import { test, expect } from "@playwright/test";
import { asOrg } from "./org";

/**
 * The organization picker looks the same whichever client is chosen. It turned amber for every
 * client but the admin's home one (2026-10-01: "CityCorp is yellow, Ellensburg is white"), which
 * read as a warning about the client rather than a choice of client. The name in it says whose
 * data this is.
 */
test("the organization picker looks the same for every client", async ({ page, context }, info) => {
  const looks: string[] = [];
  for (const org of ["ellensburg", "citycorp"]) {
    await asOrg(context, info, org);
    await page.goto("/reports");
    const picker = page.getByRole("combobox", { name: "Client organization" });
    await expect(picker).toBeVisible({ timeout: 60_000 });
    looks.push(await picker.evaluate((el) => {
      const s = getComputedStyle(el);
      return [s.backgroundColor, s.color, s.borderColor, s.fontWeight].join("|");
    }));
  }
  expect(looks[1]).toBe(looks[0]);
});

/**
 * A conversation with Ori belongs to the organization it was had in. The switch is a full
 * reload that session storage survives, and on 2026-10-02 the Ellensburg thread (a
 * cancelled-tender table) showed under CityCorp's banner, where a follow-up would have sent
 * it into CityCorp's model context. Seeded without a model call: a stored turn is enough.
 */
test("a conversation had in one organization is not shown in another", async ({ page, context }, info) => {
  await asOrg(context, info, "ellensburg");
  await page.goto("/");
  await page.evaluate(() => {
    sessionStorage.setItem("originba_assistant_turns:ellensburg", JSON.stringify([{ role: "user", text: "Ellensburg's own question about cancelled tenders" }]));
  });
  await page.reload();
  const ori = page.getByRole("region", { name: "Ask Ori" });
  await expect(ori).toContainText("Ellensburg's own question about cancelled tenders", { timeout: 60_000 });
  await asOrg(context, info, "citycorp");
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Ask Ori" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("region", { name: "Ask Ori" })).not.toContainText("Ellensburg's own question");
});
