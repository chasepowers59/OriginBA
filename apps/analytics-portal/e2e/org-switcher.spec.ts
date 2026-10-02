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
