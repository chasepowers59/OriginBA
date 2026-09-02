import { describe, expect, it } from "vitest";
import { auditActionLabel } from "./auditLabels";

/**
 * The admin activity feed printed the raw audit action, so the surface an admin reads
 * to answer "who changed access?" said `user.password_change` and `sso_jit_provision`.
 * These are the wire names from api/auth/service.py ADMIN_AUDIT_ACTIONS; the reader
 * should get English.
 */
describe("auditActionLabel", () => {
  it("names every action the admin feed can return", () => {
    expect(auditActionLabel("user.create")).toBe("User created");
    expect(auditActionLabel("user.update")).toBe("User updated");
    expect(auditActionLabel("user.password_change")).toBe("Password changed");
    expect(auditActionLabel("group.create")).toBe("Access group created");
    expect(auditActionLabel("group.update")).toBe("Access group updated");
    expect(auditActionLabel("group.delete")).toBe("Access group deleted");
    expect(auditActionLabel("sso_jit_provision")).toBe("Account provisioned by SSO");
    expect(auditActionLabel("sql_refused")).toBe("SQL blocked");
  });

  it("falls back to something readable for an action added later", () => {
    // A new action must not render as a bare identifier just because this map is old.
    expect(auditActionLabel("group.rename")).toBe("Group rename");
    expect(auditActionLabel("weird_new_thing")).toBe("Weird new thing");
  });

  it("does not crash on an empty action", () => {
    expect(auditActionLabel("")).toBe("Unknown action");
  });
});
