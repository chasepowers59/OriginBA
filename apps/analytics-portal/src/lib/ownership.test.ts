import { describe, expect, it } from "vitest";
import { ownershipLabel } from "./ownership";
import { savedViewToFavorite } from "./savedViews";
import type { SavedView } from "./types";

const view = (over: Partial<SavedView> = {}): SavedView => ({
  id: "v1", client_id: "dev", snapshot_id: "rpt_bill", snapshot_label: "Bill", title: "t", kind: "custom",
  saved_at: "2026-09-28T00:00:00Z", ...over,
});

describe("who owns a saved item", () => {
  it("a view keeps its owner, visibility and whether you may edit it", () => {
    const f = savedViewToFavorite(view({ visibility: "private", owner_email: "alice@utility.gov", can_edit: true }));
    expect(f.visibility).toBe("private");
    expect(f.ownerEmail).toBe("alice@utility.gov");
    expect(f.canEdit).toBe(true);
  });

  it("an item saved before owners existed is editable and shared", () => {
    const f = savedViewToFavorite(view());
    expect(f.visibility).toBe("organization");
    expect(f.canEdit).toBe(true);
  });

  it("reads as private, or as whose it is", () => {
    expect(ownershipLabel({ visibility: "private", ownerEmail: "alice@utility.gov" }, "alice@utility.gov")).toBe("Private");
    expect(ownershipLabel({ visibility: "organization", ownerEmail: "alice@utility.gov" }, "bob@utility.gov")).toBe("Shared by alice@utility.gov");
    expect(ownershipLabel({ visibility: "organization", ownerEmail: "alice@utility.gov" }, "alice@utility.gov")).toBe("Shared with your organization");
    expect(ownershipLabel({ visibility: "organization" }, "bob@utility.gov")).toBe("");
  });
});
