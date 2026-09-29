/**
 * Letter runs (api/letters/runs.py): a frozen list of letters, approved by someone other than its
 * creator, released as one print file.
 */
import { formatNumber } from "./format";
import type { Filters, Printed } from "./letters";

export type RunStatus = "draft" | "approved" | "released" | "cancelled";
export type RunFilters = { kinds: string[]; printed: Printed };

export type LetterRun = {
  id: string;
  status: RunStatus;
  from: string;
  to: string;
  filters: RunFilters;
  created_by: string;
  created_at: string;
  created_by_you: boolean;
  approved_by: string | null;
  approved_at: string | null;
  released_by: string | null;
  released_at: string | null;
  pages: number | null;
  cancelled_by: string | null;
  cancelled_at: string | null;
  history: { status: RunStatus; by: string; at: string }[];
  counts: { letters: number; by_kind: { kind: string; label: string; count: number }[] };
};

export type RunPermissions = { generate: boolean; approve: boolean; release: boolean; admin: boolean };
export type RunAction = { show: boolean; enabled: boolean; reason: string | null };

/** The server's ceiling (MAX_RUN_LETTERS in api/letters/runs.py). */
export const MAX_RUN_LETTERS = 5000;

const STATUS: Record<RunStatus, { label: string; tone: string }> = {
  draft: { label: "Waiting for approval", tone: "bg-warn-bg text-warn" },
  approved: { label: "Approved", tone: "tint-panel text-heading" },
  released: { label: "Released", tone: "bg-ok-bg text-ok" },
  cancelled: { label: "Cancelled", tone: "bg-chip text-fg-muted" },
};

export function runStatus(status: RunStatus): { label: string; tone: string } {
  return STATUS[status];
}

const on: RunAction = { show: true, enabled: true, reason: null };
const off: RunAction = { show: false, enabled: false, reason: null };

/** Approve and release follow the status and the person's access; the server enforces the same. */
export function runActions(run: LetterRun, can: RunPermissions) {
  const open = run.status === "draft" || run.status === "approved";
  const printable = run.status === "approved" || run.status === "released";
  return {
    approve: run.status === "draft" && can.approve
      ? run.created_by_you ? { show: true, enabled: false, reason: "You created this run, so someone else must approve it." } : on
      : off,
    release: { ...(printable && can.release ? on : off), label: run.status === "released" ? "Download again" : "Release" },
    cancel: open && can.generate && (run.created_by_you || can.admin) ? on : off,
  };
}

export function runFilters(f: Filters): RunFilters {
  return { kinds: f.kinds, printed: f.printed };
}

/** Why the letters on screen cannot become a run as they are, or null. */
export function createRunBlocker(f: Filters, shown: number): string | null {
  if (f.search.trim()) return "Clear the search first: a run is chosen by date, letter type and status.";
  if (shown === 0) return "No letters to put in a run.";
  if (shown > MAX_RUN_LETTERS) {
    return `A run holds at most ${formatNumber(MAX_RUN_LETTERS)} letters; choose a shorter window or fewer letter types.`;
  }
  return null;
}

/** The server words every refusal (four eyes, a changed letter, the limit): show its sentence. */
export function runErrorMessage(err: unknown): string {
  return err instanceof Error && err.message ? err.message : "That did not work. Try again.";
}
