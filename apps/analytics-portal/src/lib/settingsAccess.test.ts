import { describe, expect, it } from "vitest";
import { assignableRoles, settingsTabs } from "./settingsAccess";

const holds = (...perms: string[]) => (p: string) => perms.includes(p);

describe("settingsTabs", () => {
  it("gives the platform admin every tab", () => {
    expect(settingsTabs(holds("settings:manage", "users:manage", "data_source:manage")))
      .toEqual(["connection", "access", "packs", "health"]);
  });

  it("gives a client admin their users and nothing platform-wide", () => {
    expect(settingsTabs(holds("users:manage", "groups:manage"))).toEqual(["access"]);
  });

  it("gives everyone else nothing", () => {
    expect(settingsTabs(holds("portal:read"))).toEqual([]);
  });
});

describe("assignableRoles", () => {
  it("the platform admin assigns every role", () => {
    expect(assignableRoles("admin")).toEqual(["user", "editor", "client_admin", "admin"]);
  });

  it("a client admin assigns every role but the platform admin", () => {
    expect(assignableRoles("client_admin")).toEqual(["user", "editor", "client_admin"]);
  });

  it("nobody else assigns roles", () => {
    expect(assignableRoles("editor")).toEqual([]);
    expect(assignableRoles(undefined)).toEqual([]);
  });
});
