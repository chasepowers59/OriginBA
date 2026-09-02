import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { organizationForRole, rolePatch } from "./adminOrgBinding";

/**
 * An admin is a platform admin: no organization, and therefore every organization.
 * api/auth/service.py now refuses any account that is both (ADMIN_ORG_ERROR), because
 * nothing in the backend ever read that field for authorization -- users, groups and
 * the audit log are filtered by client_id, one value for the whole deployment -- so an
 * "admin for CityCorp" was a deployment-wide superuser wearing a client's name.
 *
 * The panel has to stop offering the combination, and one path in particular: the role
 * dropdown sent `{role}` alone, so promoting an org-bound editor to admin carried the
 * old organization along and produced exactly the forbidden account. Promotion has to
 * clear the organization in the same request.
 */
describe("organizationForRole", () => {
  it("drops the organization for an admin", () => {
    expect(organizationForRole("admin", "citycorp")).toBeNull();
    expect(organizationForRole("admin", "")).toBeNull();
    expect(organizationForRole("admin", null)).toBeNull();
  });

  it("keeps it for every other role", () => {
    expect(organizationForRole("editor", "citycorp")).toBe("citycorp");
    expect(organizationForRole("user", "odessa")).toBe("odessa");
  });

  it("normalises an unset organization to null rather than an empty string", () => {
    expect(organizationForRole("editor", "")).toBeNull();
  });
});

describe("rolePatch", () => {
  it("clears the organization when promoting to admin, in the same request", () => {
    expect(rolePatch("admin")).toEqual({ role: "admin", organization_id: null });
  });

  it("leaves the organization alone for a non-admin role change", () => {
    // Demoting needs the org kept; the API refuses a non-admin without one, and the
    // user already has it.
    expect(rolePatch("editor")).toEqual({ role: "editor" });
    expect(rolePatch("user")).toEqual({ role: "user" });
  });
});

describe("AdminAccessPanel", () => {
  const SOURCE = readFileSync(resolve(__dirname, "../components/AdminAccessPanel.tsx"), "utf8");

  it("never sends a bare role change", () => {
    expect(SOURCE).not.toMatch(/\{\s*role:\s*e\.target\.value\s*\}/);
    expect(SOURCE).toMatch(/rolePatch/);
  });

  it("routes the create form's organization through the same rule", () => {
    expect(SOURCE).toMatch(/organizationForRole/);
  });
});
