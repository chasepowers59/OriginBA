"use client";

import { formatPercent } from "@/lib/format";

/**
 * The period-over-period delta chip. A color-tinted pill (Power BI / Tableau
 * convention) reads faster than plain text: green up, rose down, slate flat,
 * with a directional arrow and the prior-period basis stated beside it.
 */
export function KpiCompareBadge({
  changePct,
  priorLabel = "vs prior period",
}: {
  changePct: number | null | undefined;
  priorLabel?: string;
}) {
  if (changePct == null || Number.isNaN(changePct)) {
    return null;
  }
  const up = changePct > 0;
  const flat = Math.abs(changePct) < 0.05;
  const tone = flat
    ? "bg-slate-500/10 text-fg ring-slate-400/20"
    : up
      ? "bg-ok-bg text-ok ring-ok"
      : "bg-over-bg text-over ring-over";
  const arrow = flat ? "→" : up ? "▲" : "▼";

  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums ring-1 ring-inset ${tone}`}
      >
        <span className="text-[10px] leading-none">{arrow}</span>
        {formatPercent(Math.abs(changePct))}
      </span>
      <span className="text-xs text-fg-muted">{priorLabel}</span>
    </span>
  );
}
