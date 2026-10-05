import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { NoOrganization, needsOrganization } from "@/components/NoOrganization";

/**
 * A signed-in reader with no organization assigned got a full Home that could not load:
 * "Connect your database in Settings" (a page they cannot open), "Unable to load executive
 * metrics", an Ask Ori box and saved views that the server refuses with "No organization
 * assigned" (2026-10-05). They get one page saying what is missing and who can fix it.
 */
describe("a reader with no organization", () => {
  it("is told so instead of shown pages that cannot load", () => {
    expect(needsOrganization({ role: "user", organization_id: null })).toBe(true);
    expect(needsOrganization({ role: "editor", organization_id: null })).toBe(true);
    expect(needsOrganization({ role: "client_admin", organization_id: null })).toBe(true);
  });

  it("an administrator chooses an organization from the picker, and an assigned reader has one", () => {
    expect(needsOrganization({ role: "admin", organization_id: null })).toBe(false);
    expect(needsOrganization({ role: "user", organization_id: "citycorp" })).toBe(false);
    expect(needsOrganization(null)).toBe(false);
  });

  it("names what is missing and who can fix it, and offers nothing that would be refused", () => {
    const html = renderToStaticMarkup(<NoOrganization email="user.smoke@origin.local" />);
    expect(html).toContain("isn&#x27;t assigned to a client organization yet");
    expect(html).toContain("administrator");
    expect(html).toContain("user.smoke@origin.local");
    expect(html).not.toContain("Settings");
  });
});
