"use client";

import { useEffect, useState } from "react";
import { fetchOriFindings, fetchOriTrends, type OriRead, type OriTrends } from "@/lib/api";
import { requestAsk } from "@/lib/assistantContext";
import { ORI } from "@/lib/ori";
import { investigations, oriPanelShows } from "@/lib/oriPanel";
import Link from "next/link";
import { OriMark } from "@/components/OriMark";

const NO_READ: OriRead = { findings: [] };
const NO_TRENDS: OriTrends = { through: "", anomalies: [], forecasts: [] };

/**
 * Ori's read on home (and, with `workstream`, on that page from its own cards): a brief of the period, what is worth investigating (large moves against the
 * prior period from api/ori_insights.py, and unusual months), and one line per forecast with the way to the Forecasts page. The
 * findings are fast and the trends can take half a minute cold, so each arrives on its own.
 */
export function OriInsights({ workstream }: { workstream?: string } = {}) {
  const [read, setRead] = useState<OriRead | null>(null);
  const [trends, setTrends] = useState<OriTrends | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    // An aborted request is not an empty answer: Strict Mode aborts the first mount's requests.
    fetchOriFindings(signal, workstream).then(setRead, () => signal.aborted || setRead(NO_READ));
    // projections read the home cards' monthly history, so a workstream page has none
    if (workstream) setTrends(NO_TRENDS);
    else fetchOriTrends(signal).then(setTrends, () => signal.aborted || setTrends(NO_TRENDS));
    return () => controller.abort();
  }, [workstream]);

  if (!read || !oriPanelShows(read, trends)) return null;

  const brief = read.brief?.trim();
  const items = investigations(read.findings, trends?.anomalies ?? []);
  const forecasts = trends?.forecasts ?? [];

  return (
    <section aria-label={ORI.read} className="glass-panel p-6">
      <div className="flex items-center gap-2.5">
        <OriMark size="h-10 w-10" />
        <h2 className="text-xl font-bold text-heading">{ORI.read}</h2>
      </div>
      {brief ? <p className="mt-3 max-w-3xl text-sm leading-relaxed text-heading">{brief}</p> : null}

      {items.length ? (
        <section aria-label={ORI.worthInvestigating} className="mt-6">
          <h3 className="text-base font-semibold text-heading">{ORI.worthInvestigating}</h3>
          <ul className="mt-1 divide-y divide-edge-subtle">
            {items.map((item) => (
              <li key={item.key} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-heading">{item.headline}</p>
                  <p className="text-sm tabular-nums text-fg-muted">{item.detail}</p>
                </div>
                <button type="button" className="btn-ghost shrink-0 text-xs" onClick={() => requestAsk(item.ask)}>
                  {ORI.askWhy}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {forecasts.length ? (
        <section aria-label={ORI.heading} className="mt-6">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h3 className="text-base font-semibold text-heading">{ORI.heading}</h3>
            <Link href="/forecasts" className="text-sm font-medium text-primary hover:underline">
              {ORI.seeAllForecasts}
            </Link>
          </div>
          <ul className="mt-1 divide-y divide-edge-subtle">
            {forecasts.map((f) => (
              <li key={f.kpi_id} className="py-2 text-sm font-medium text-heading">{f.headline}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {trends ? null : (
        <p role="status" className="mt-6 text-sm text-fg-muted">
          {ORI.thinking}
        </p>
      )}
    </section>
  );
}
