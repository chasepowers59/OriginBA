import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * With auth disabled, the portal used to fabricate its own dev user client-side and
 * never ask the API. The API builds ITS dev context from `dev_organization_id()`, so
 * the two could not agree: locally the header read "Ellensburg" over CityCorp's data,
 * and the stub's permission list had drifted to omit `database:sql`, hiding the SQL
 * surface in the only mode you can browse without signing in.
 *
 * A constant cannot track a runtime-configured value, so the fix is to ask the API and
 * these assert the fabrication is gone rather than that the two copies match.
 */
const SOURCE = readFileSync(resolve(__dirname, "AuthProvider.tsx"), "utf8");

describe("AuthProvider disabled-auth identity", () => {
  it("invents no organization of its own", () => {
    expect(SOURCE).not.toMatch(/organization_id:\s*["'`]/);
    expect(SOURCE).not.toMatch(/organization_name:\s*["'`]/);
  });

  it("invents no permission list of its own", () => {
    expect(SOURCE).not.toMatch(/permissions:\s*\[/);
  });

  it("asks the API for the current user", () => {
    expect(SOURCE).toMatch(/fetchCurrentUser\(\)/);
  });
});
