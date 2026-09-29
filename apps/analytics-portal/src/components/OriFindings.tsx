"use client";

import { useEffect, useState } from "react";
import { fetchOriFindings, type OriFinding } from "@/lib/api";
import { requestAsk } from "@/lib/assistantContext";
import { ORI } from "@/lib/ori";
import { OriMark } from "@/components/OriMark";

/**
 * "Ori found something worth investigating": the large moves in the home cards against the
 * prior period (api/ori_insights.py), each with a one-click question to Ori. Nothing to say,
 * no card.
 */
export function OriFindings() {
  const [findings, setFindings] = useState<OriFinding[]>([]);

  useEffect(() => {
    fetchOriFindings()
      .then((r) => setFindings(r.findings))
      .catch(() => setFindings([]));
  }, []);

  if (!findings.length) return null;

  return (
    <section aria-label={ORI.worthInvestigating} className="glass-panel p-5">
      <div className="flex items-center gap-2.5">
        <OriMark size="h-8 w-8" />
        <h2 className="text-base font-semibold text-heading">{ORI.worthInvestigating}</h2>
      </div>
      <ul className="mt-3 divide-y divide-edge-subtle">
        {findings.map((f) => (
          <li key={f.kpi_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-heading">{f.headline}</p>
              <p className="text-sm tabular-nums text-fg-muted">{f.detail}</p>
            </div>
            <button type="button" className="btn-ghost shrink-0 text-xs"
                    onClick={() => requestAsk({ question: f.question, context: null })}>
              {ORI.askWhy}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
