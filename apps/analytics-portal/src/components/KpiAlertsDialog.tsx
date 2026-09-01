"use client";

import { useEffect, useState } from "react";
import {
  createKpiAlert,
  deleteKpiAlert,
  fetchKpiAlerts,
  type KpiAlert,
  type WatchableKpi,
} from "@/lib/api";

const CONDITION_LABELS: Record<string, string> = {
  above: "value rises above",
  below: "value falls below",
  pct_change_above: "period change exceeds (%)",
  pct_change_below: "period change drops below (%)",
};

/**
 * KPI threshold alerts: watch an executive KPI and get emailed the moment it
 * crosses a line. Evaluation runs server-side on the hourly runner, through the
 * same KPI queries the dashboard shows — an alert can't disagree with its tile.
 */
export function KpiAlertsDialog({ onClose }: { onClose: () => void }) {
  const [alerts, setAlerts] = useState<KpiAlert[]>([]);
  const [kpis, setKpis] = useState<WatchableKpi[]>([]);
  const [smtpReady, setSmtpReady] = useState(true);
  const [kpiId, setKpiId] = useState("");
  const [condition, setCondition] = useState("below");
  const [threshold, setThreshold] = useState("");
  const [windowDays, setWindowDays] = useState(7);
  const [recipients, setRecipients] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    fetchKpiAlerts()
      .then((r) => {
        setAlerts(r.alerts);
        setKpis(r.available_kpis);
        setSmtpReady(r.smtp_configured);
        if (!kpiId && r.available_kpis.length) setKpiId(r.available_kpis[0].id);
      })
      .catch(() => setAlerts([]));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(refresh, []);

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      await createKpiAlert({
        kpi_id: kpiId,
        condition,
        threshold: Number(threshold),
        window_days: windowDays,
        recipients: recipients
          .split(/[,;\s]+/)
          .map((r) => r.trim())
          .filter(Boolean),
      });
      setThreshold("");
      setRecipients("");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the alert.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="KPI threshold alerts"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-edge-subtle bg-surface p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-heading">KPI threshold alerts</h2>
            <p className="mt-0.5 text-xs text-fg-muted">
              Email when a metric crosses a line — sent once per breach, not daily.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-fg-muted hover:text-heading"
          >
            ✕
          </button>
        </div>

        {!smtpReady ? (
          <p className="mt-3 rounded-lg border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            Email delivery is not configured on the server yet — alerts save, but
            nothing sends until an administrator sets up SMTP.
          </p>
        ) : null}

        {alerts.length ? (
          <ul className="mt-3 space-y-1.5">
            {alerts.map((a) => (
              <li
                key={a.id}
                className="flex items-center gap-2 rounded-lg border border-edge-subtle bg-surface-subtle px-3 py-2 text-xs"
              >
                <span className="min-w-0 flex-1 truncate text-fg">
                  <strong>{a.kpi_label}</strong> {CONDITION_LABELS[a.condition] ?? a.condition}{" "}
                  {a.threshold}
                  {" · "}
                  {a.recipients.join(", ")}
                  {a.last_status ? ` · ${a.last_status}` : ""}
                </span>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    a.last_state === "breached"
                      ? "bg-red-500/15 text-red-700 dark:text-red-300"
                      : "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                  }`}
                >
                  {a.last_state === "breached" ? "Breached" : "OK"}
                </span>
                <button
                  type="button"
                  onClick={async () => {
                    await deleteKpiAlert(a.id);
                    refresh();
                  }}
                  className="shrink-0 text-fg-muted hover:text-red-600 dark:hover:text-red-300"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs text-fg-muted">No alerts yet — create the first one below.</p>
        )}

        <div className="mt-4 space-y-3 border-t border-edge-subtle pt-4 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs font-medium text-fg-muted">
              KPI
              <select
                value={kpiId}
                onChange={(e) => setKpiId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
              >
                {kpis.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-fg-muted">
              Condition
              <select
                value={condition}
                onChange={(e) => setCondition(e.target.value)}
                className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
              >
                {Object.entries(CONDITION_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-xs font-medium text-fg-muted">
              Threshold{condition.startsWith("pct_change") ? " (%)" : ""}
              <input
                type="number"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                placeholder={condition.startsWith("pct_change") ? "-20" : "100"}
                className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
              />
            </label>
            <label className="block text-xs font-medium text-fg-muted">
              Window (trailing days)
              <input
                type="number"
                min={1}
                max={366}
                value={windowDays}
                onChange={(e) => setWindowDays(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
              />
            </label>
          </div>
          <label className="block text-xs font-medium text-fg-muted">
            Recipients (comma-separated)
            <input
              type="text"
              value={recipients}
              onChange={(e) => setRecipients(e.target.value)}
              placeholder="ops@utility.gov"
              className="mt-1 w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
            />
          </label>
          {error ? (
            <p role="alert" className="rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs text-red-700 dark:text-red-300">
              {error}
            </p>
          ) : null}
          <button
            type="button"
            onClick={onCreate}
            disabled={busy || !threshold.trim() || !recipients.trim()}
            className="w-full rounded-lg bg-brand py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Create alert"}
          </button>
        </div>
      </div>
    </div>
  );
}
