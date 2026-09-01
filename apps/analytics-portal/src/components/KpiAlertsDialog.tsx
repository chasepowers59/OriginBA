"use client";

import { useEffect, useState } from "react";
import {
  createKpiAlert,
  deleteKpiAlert,
  fetchKpiAlerts,
  type KpiAlert,
  type WatchableKpi,
} from "@/lib/api";
import { FormError, Modal, SmtpNotice } from "@/components/Modal";
import { parseRecipients } from "@/lib/recipients";

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
        recipients: parseRecipients(recipients),
      });
      setThreshold("");
      setRecipients("");
      refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create the alert.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      title="KPI threshold alerts"
      subtitle="Email when a metric crosses a line — sent once per breach, not daily."
      onClose={onClose}
      size="lg"
    >
      {!smtpReady ? <SmtpNotice what="alerts" /> : null}

      {alerts.length ? (
        <ul className="mt-3 space-y-1.5">
          {alerts.map((a) => (
            <li
              key={a.id}
              className="flex items-center gap-2 rounded-lg border border-edge-subtle bg-surface-subtle px-3 py-2 text-xs"
            >
              <span className="min-w-0 flex-1 truncate text-fg">
                <strong>{a.kpi_label}</strong>{" "}
                {CONDITION_LABELS[a.condition] ?? a.condition} {a.threshold}
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
        <p className="mt-3 text-xs text-fg-muted">
          No alerts yet — create the first one below.
        </p>
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
        {error ? <FormError>{error}</FormError> : null}
        <button
          type="button"
          onClick={onCreate}
          disabled={busy || !threshold.trim() || !recipients.trim()}
          className="btn-primary w-full"
        >
          {busy ? "Saving…" : "Create alert"}
        </button>
      </div>
    </Modal>
  );
}
