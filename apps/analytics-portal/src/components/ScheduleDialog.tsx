"use client";

import { useEffect, useState } from "react";
import {
  createReportSchedule,
  deleteReportSchedule,
  fetchReportSchedules,
  type ReportSchedule,
} from "@/lib/api";
import { FormError, Modal, SmtpNotice } from "@/components/Modal";
import { parseRecipients } from "@/lib/recipients";

const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

/**
 * Email-schedule editor for one saved view: who gets it, how often, and how much
 * trailing data. Delivery runs server-side on the cron runner — this only manages
 * the subscription.
 */
export function ScheduleDialog({
  savedViewId,
  viewTitle,
  onClose,
}: {
  savedViewId: string;
  viewTitle: string;
  onClose: () => void;
}) {
  const [existing, setExisting] = useState<ReportSchedule[]>([]);
  const [smtpReady, setSmtpReady] = useState(true);
  const [recipients, setRecipients] = useState("");
  const [cadence, setCadence] = useState("weekly");
  const [weekday, setWeekday] = useState(0);
  const [hourUtc, setHourUtc] = useState(13);
  const [windowDays, setWindowDays] = useState(30);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    fetchReportSchedules()
      .then((r) => {
        setExisting(r.schedules.filter((s) => s.saved_view_id === savedViewId));
        setSmtpReady(r.smtp_configured);
      })
      .catch(() => setExisting([]));
  };

  useEffect(refresh, [savedViewId]);

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      await createReportSchedule({
        saved_view_id: savedViewId,
        recipients: parseRecipients(recipients),
        cadence,
        weekday,
        hour_utc: hourUtc,
        window_days: windowDays,
      });
      setRecipients("");
      refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create the schedule.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Email schedule" subtitle={viewTitle} onClose={onClose}>
      {!smtpReady ? <SmtpNotice what="schedules" /> : null}

      {existing.length ? (
        <ul className="mt-3 space-y-1.5">
          {existing.map((s) => (
            <li
              key={s.id}
              className="flex items-center gap-2 rounded-lg border border-edge-subtle bg-surface-subtle px-3 py-2 text-xs"
            >
              <span className="min-w-0 flex-1 truncate text-fg">
                {s.cadence === "weekly" ? `${WEEKDAYS[s.weekday]}s` : s.cadence}
                {" · "}
                {s.recipients.join(", ")}
                {s.last_status ? ` · ${s.last_status}` : ""}
              </span>
              <button
                type="button"
                onClick={async () => {
                  await deleteReportSchedule(s.id);
                  refresh();
                }}
                className="shrink-0 text-fg-muted hover:text-red-600 dark:hover:text-red-300"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-4 space-y-3 text-sm">
        <label className="block text-xs font-medium text-fg-muted">
          Recipients (comma-separated)
          <input
            type="text"
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            placeholder="exec@utility.gov, billing@utility.gov"
            className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs font-medium text-fg-muted">
            Cadence
            <select
              value={cadence}
              onChange={(e) => setCadence(e.target.value)}
              className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly (1st)</option>
            </select>
          </label>
          {cadence === "weekly" ? (
            <label className="block text-xs font-medium text-fg-muted">
              Day
              <select
                value={weekday}
                onChange={(e) => setWeekday(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
              >
                {WEEKDAYS.map((d, i) => (
                  <option key={d} value={i}>
                    {d}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label className="block text-xs font-medium text-fg-muted">
              Hour (UTC)
              <input
                type="number"
                min={0}
                max={23}
                value={hourUtc}
                onChange={(e) => setHourUtc(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
              />
            </label>
          )}
        </div>
        <label className="block text-xs font-medium text-fg-muted">
          Data window (trailing days)
          <input
            type="number"
            min={1}
            max={366}
            value={windowDays}
            onChange={(e) => setWindowDays(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
          />
        </label>
        {error ? <FormError>{error}</FormError> : null}
        <button
          type="button"
          onClick={onCreate}
          disabled={busy || !recipients.trim()}
          className="btn-primary w-full"
        >
          {busy ? "Saving…" : "Create schedule"}
        </button>
      </div>
    </Modal>
  );
}
