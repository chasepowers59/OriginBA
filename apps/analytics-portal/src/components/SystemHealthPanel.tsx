"use client";

import { useEffect, useState } from "react";
import { fetchSystemHealth } from "@/lib/api";
import { findReference, hitRate, type SystemHealth } from "@/lib/systemHealth";
import { formatDateTime, formatNumber } from "@/lib/format";
import { FormError } from "@/components/Modal";

const cell = "px-3 py-1.5 text-left align-top";

/** Requests, errors and timings of this API process, and a lookup for a user's "Reference: ...". */
export function SystemHealthPanel() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reference, setReference] = useState("");

  const load = () =>
    fetchSystemHealth()
      .then((h) => {
        setHealth(h);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not read the system health."));

  useEffect(() => {
    void load();
  }, []);

  if (error) return <div className="glass-panel p-6"><FormError>{error}</FormError></div>;
  if (!health) return <div className="glass-panel-subtle loading-shimmer h-40 rounded-xl" />;

  const found = reference.trim() ? findReference(health.errors, reference) : null;
  const stats = [
    ["Since", formatDateTime(health.started_at)],
    ["Requests", formatNumber(health.requests)],
    ["Server errors", formatNumber(health.server_errors)],
    ["Cache hit rate", hitRate(health.cache)],
  ];

  return (
    <div className="space-y-6">
      <section className="glass-panel space-y-4 p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-heading">System health</h2>
          <button type="button" onClick={() => void load()} className="btn-ghost text-xs">Refresh</button>
        </div>
        <p className="text-sm text-fg-muted">
          This API process only, since it last started; a restart begins again. Slow means {health.slow_ms / 1000} seconds
          or more.
        </p>
        <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {stats.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-edge-subtle bg-surface-subtle px-3 py-2">
              <dt className="text-xs text-fg-muted">{label}</dt>
              <dd className="text-lg font-semibold tabular-nums text-heading">{value}</dd>
            </div>
          ))}
        </dl>
        <label className="block text-xs font-semibold text-heading">
          Look up a reference a user reported
          <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Reference: 3f9c0a1b2c3d"
                 className="mt-1 block w-full max-w-md rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg" />
        </label>
        {reference.trim() ? (
          found ? (
            <p className="text-sm text-fg">
              {formatDateTime(found.at)} · {found.route} · {found.org}: <span className="font-mono text-xs">{found.error}</span>
            </p>
          ) : (
            <p className="text-sm text-fg-muted">Not among the last {health.errors.length} server errors of this process.</p>
          )
        ) : null}
      </section>

      <HealthTable title="Recent server errors" empty="No server errors since the API started."
                   head={["When", "Reference", "Route", "Organization", "Error"]}
                   rows={health.errors.map((e) => [formatDateTime(e.at), e.reference, e.route, e.org, e.error])} />
      <HealthTable title="Slowest recent requests" empty="Nothing slow since the API started."
                   head={["When", "Reference", "Route", "Organization", "Seconds"]}
                   rows={health.slow.map((s) => [formatDateTime(s.at), s.reference, s.route, s.org, formatNumber(s.ms / 1000)])} />
      <HealthTable title="Cache warming after a rebuild" empty="Nothing warmed yet: the first pass runs a minute after the API starts."
                   head={["Organization", "When", "Built", "Failed"]}
                   rows={Object.entries(health.warmed).map(([org, w]) => [org, formatDateTime(w.at), w.built.join(", "), w.failed.join(", ") || "—"])} />
      <HealthTable title="Routes by total time" empty="No requests yet."
                   head={["Route", "Requests", "Server errors", "Average ms", "Longest ms"]}
                   rows={health.routes.slice(0, 20).map((r) => [r.route, r.requests, r.server_errors, r.avg_ms, r.max_ms])} />
    </div>
  );
}

function HealthTable({ title, head, rows, empty }: { title: string; head: string[]; rows: (string | number)[][]; empty: string }) {
  return (
    <section className="glass-panel p-6">
      <h3 className="mb-3 text-sm font-semibold text-heading">{title}</h3>
      {rows.length ? (
        <div className="overflow-x-auto rounded-lg border border-edge-subtle">
          <table className="min-w-full text-xs">
            <thead><tr>{head.map((h) => <th key={h} scope="col" className={`${cell} text-fg-muted`}>{h}</th>)}</tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-edge-subtle">
                  {r.map((v, j) => <td key={j} className={`${cell} ${typeof v === "number" ? "tabular-nums" : ""} text-fg`}>{v}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="text-sm text-fg-muted">{empty}</p>}
    </section>
  );
}
