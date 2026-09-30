/**
 * Deleting an access group widens access rather than narrowing it: the API treats an
 * empty workstream list as "all" (service.py workstreams_allowed), so a member left
 * with no group gets everything. The confirm has to say that, because "delete a
 * permission group" reads like the opposite.
 */

export type DeletableGroup = {
  name: string;
  member_count: number;
  workstreams: string[];
};

/** True when the group grants everything already, so removing it widens no one. */
function grantsEverything(workstreams: string[]): boolean {
  return workstreams.length === 0 || workstreams.includes("*");
}

export function groupDeletionWarning(group: DeletableGroup): string {
  const noun = group.member_count === 1 ? "member" : "members";
  const head = `Delete the access group "${group.name}"?`;

  if (group.member_count === 0) {
    return `${head} No one is assigned to it. This cannot be undone.`;
  }

  if (grantsEverything(group.workstreams)) {
    return (
      `${head} ${group.member_count} ${noun} assigned. They already have every ` +
      `workstream, so their access does not change. This cannot be undone.`
    );
  }

  return (
    `${head} ${group.member_count} ${noun} assigned. Any of them left with no other ` +
    `group will GAIN full access to every workstream, not lose access. This cannot be undone.`
  );
}
