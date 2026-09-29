/** A schedule's recent runs (api/report_schedules.py keeps the last 20). */

export type ScheduleRun = { at: string; trigger: "schedule" | "send now"; status: string; rows: number | null };

export function runLine(run: ScheduleRun, when: (iso: string) => string): string {
  const how = run.trigger === "send now" ? "Send now" : "scheduled";
  const outcome = run.rows != null ? `${run.status}, ${run.rows.toLocaleString()} rows` : run.status;
  return `${when(run.at)} · ${how} · ${outcome}`;
}
