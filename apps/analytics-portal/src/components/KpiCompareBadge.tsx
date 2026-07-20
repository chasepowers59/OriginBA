"use client";

import { formatPercent } from "@/lib/format";

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
  const color = flat ? "text-slate-400" : up ? "text-emerald-400" : "text-rose-400";
  const arrow = flat ? "→" : up ? "↑" : "↓";

  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${color}`}>
      <span>{arrow}</span>
      <span>{formatPercent(Math.abs(changePct))}</span>
      <span className="text-slate-500">{priorLabel}</span>
    </span>
  );
}
