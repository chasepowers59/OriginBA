import { describe, expect, it } from "vitest";
import { groupDeletionWarning } from "./groupDeletion";

/**
 * Deleting an access group WIDENS access, which is the opposite of what "delete a
 * permission" reads like. api/auth/service.py:
 *
 *   def workstreams_allowed(workstreams, workstream_id):
 *       if not workstreams or "*" in workstreams:   <- empty means ALL
 *           return True
 *
 * So a user whose only group was "smoke-finance" (Finance + Billing) does not lose
 * those two workstreams when it is deleted -- they gain the other seven. The panel
 * fired this from a single unconfirmed click, `deleteAccessGroup(id).then(reload)`,
 * with no catch, while displaying the member count right beside the button.
 *
 * Membership rows themselves are cleaned up correctly (AccessGroup.members cascades
 * all, delete-orphan), so this is about consequence and consent, not orphaned data.
 *
 * The client only knows member_count, not how many groups each member has, so the
 * warning must not claim every member will be widened -- only those left with none.
 */
describe("groupDeletionWarning", () => {
  it("says plainly that a scoped group's members gain access, not lose it", () => {
    const msg = groupDeletionWarning({
      name: "smoke-finance",
      member_count: 2,
      workstreams: ["finance", "billing"],
    });
    expect(msg).toContain("smoke-finance");
    expect(msg).toContain("2 members");
    expect(msg).toMatch(/full access/i);
    expect(msg).toMatch(/cannot be undone/i);
  });

  it("does not claim members are widened when the group already granted everything", () => {
    const msg = groupDeletionWarning({
      name: "All workstreams",
      member_count: 1,
      workstreams: ["*"],
    });
    expect(msg).toContain("All workstreams");
    expect(msg).not.toMatch(/full access to every workstream/i);
  });

  it("keeps it short when nobody is assigned", () => {
    const msg = groupDeletionWarning({ name: "Unused", member_count: 0, workstreams: ["finance"] });
    expect(msg).toMatch(/no one|nobody/i);
    expect(msg).not.toMatch(/full access/i);
  });

  it("hedges correctly for a member who may hold another group", () => {
    // The client cannot tell; claiming certainty here would be a lie.
    const msg = groupDeletionWarning({ name: "X", member_count: 3, workstreams: ["debt"] });
    expect(msg).toMatch(/no other group/i);
  });

  it("says member, not members, for one", () => {
    expect(groupDeletionWarning({ name: "X", member_count: 1, workstreams: ["debt"] })).toContain(
      "1 member ",
    );
  });

  it("treats an empty workstream list as full access, the way the API does", () => {
    const msg = groupDeletionWarning({ name: "X", member_count: 2, workstreams: [] });
    expect(msg).not.toMatch(/full access to every workstream/i);
  });
});
