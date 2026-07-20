import type { SnapshotMetadata } from "./types";
import {
  requiredDateLabel,
  snapshotGrainDescription,
  snapshotSummary,
  workstreamDisplayName,
} from "./businessLabels";

export function snapshotSubtitle(meta: SnapshotMetadata): string {
  const summary = snapshotSummary(meta);
  const grain = snapshotGrainDescription(meta);
  const period = requiredDateLabel(meta);
  return summary || `${workstreamDisplayName(meta.workstream)} · ${grain} · filtered by ${period}`;
}

export function snapshotDetailLine(meta: SnapshotMetadata): string {
  const grain = snapshotGrainDescription(meta);
  const period = requiredDateLabel(meta);
  return `${grain} · reporting period uses ${period}`;
}
