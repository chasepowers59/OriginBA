import type { SnapshotMetadata } from "./types";
import {
  snapshotGrainDescription,
  snapshotSummary,
  workstreamDisplayName,
} from "./businessLabels";
import { dateScope } from "./dateScope";

export function snapshotSubtitle(meta: SnapshotMetadata): string {
  const summary = snapshotSummary(meta);
  if (summary) return summary;
  const grain = snapshotGrainDescription(meta);
  return [workstreamDisplayName(meta.workstream), grain, datePhrase(meta)]
    .filter(Boolean)
    .join(" · ");
}

export function snapshotDetailLine(meta: SnapshotMetadata): string {
  return [snapshotGrainDescription(meta), datePhrase(meta)].filter(Boolean).join(" · ");
}

/**
 * The date clause, or nothing.
 *
 * This used to read "reporting period uses Reporting period" — tautological, and false:
 * the label was a hardcoded fallback for canvases with no required date field, which is
 * all of them. Say which date the canvas works in, or say nothing.
 */
function datePhrase(meta: SnapshotMetadata): string {
  const scope = dateScope(meta);
  if (!scope) return "";
  return scope.required ? `filtered by ${scope.value}` : `dates on ${scope.value}`;
}
