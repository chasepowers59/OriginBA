"use client";

import { measureDisplaysAsCurrency } from "@/lib/businessLabels";
import { formatCompact, formatDate, formatPercent } from "@/lib/format";
import { comparePeriods } from "@/lib/periodCompare";
import type { QueryResponse } from "@/lib/types";

/** "What changed" against the previous period of the same length: the total, then the groups
 *  that moved most. Shown only when the explorer ran both (lib/periodCompare.canCompare). */
export function CompareSummary({ current, prior, priorRange, dimensionKey, measureKey, measureField, measureAgg }: {
  current: QueryResponse;
  prior: QueryResponse;
  priorRange: [string, string];
  dimensionKey: string;
  measureKey: string;
  measureField: string;
  measureAgg: string;
}) {
  const unbroken = (r: QueryResponse) => (r.totals?.[measureKey] == null ? null : Number(r.totals[measureKey]));
  const c = comparePeriods(current.rows, prior.rows, dimensionKey, measureKey, 3,
    { current: unbroken(current), prior: unbroken(prior) });
  const currency = measureDisplaysAsCurrency(measureField, measureAgg);
  const money = (v: number) => formatCompact(v, { currency });
  const signed = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${money(Math.abs(v))}`;
  const pct = (v: number | null) => (v === null ? "new" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${formatPercent(Math.abs(v))}`);
  return (
    <section aria-label="What changed" className="glass-panel px-5 py-4 text-sm">
      <p className="text-heading">
        <span className="font-medium">What changed</span>{" "}
        <span className="text-fg-muted">
          against {formatDate(priorRange[0])} – {formatDate(priorRange[1])}:
        </span>{" "}
        {money(c.total.current)} vs {money(c.total.prior)}{" "}
        <span className={c.total.change < 0 ? "text-danger" : "text-heading"}>
          ({signed(c.total.change)}, {pct(c.total.pct)})
        </span>
      </p>
      {c.movers.length ? (
        <ul className="mt-2 space-y-0.5 text-fg-muted">
          {c.movers.map((g) => (
            <li key={g.key}>
              <span className="text-heading">{g.key}</span>: {signed(g.change)} ({pct(g.pct)})
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
