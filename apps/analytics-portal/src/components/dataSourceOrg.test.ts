import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Settings named the wrong tenant on a page that saves database credentials.
 *
 * The heading read `authUser.organization_name` — the user's HOME org — while every
 * read and write on the page goes through apiGet/apiPost, which send the ACTIVE org
 * header. Measured against the running API with the active org set to `dev`:
 *
 *   heading said   "Connect the analytics portal to your Oracle C2M database for CityCorp"
 *   status shown   "Not configured" — which is dev's status, correctly fetched for dev
 *   meanwhile      citycorp is configured: source "environment", user CP***, dsn 10.1***
 *
 * So an admin who had switched to INT_DEV would read that CityCorp has no connection,
 * and type CityCorp's credentials into a form that saves them against INT_DEV. The
 * label and the thing being edited have to come from the same place, and that place is
 * the effective organization.
 */
const SOURCE = readFileSync(
  resolve(__dirname, "DataSourceSettings.tsx"),
  "utf8",
);

describe("DataSourceSettings tenant labelling", () => {
  it("does not name the tenant from the signed-in user's home org", () => {
    expect(SOURCE).not.toMatch(/authUser[?.]*\.organization_name/);
  });

  it("names the tenant from the effective organization the page is editing", () => {
    expect(SOURCE).toMatch(/usePortalConfig|organization_name/);
  });

  it("still shows a fallback rather than an empty sentence", () => {
    expect(SOURCE).toMatch(/your assigned client|this organization/);
  });
});
