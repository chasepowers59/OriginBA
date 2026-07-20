"use client";

import Link from "next/link";
import { formatCurrency, formatNumber } from "@/lib/format";
import type { NlqResponse } from "@/lib/types";

type NlqAnswerCardProps = {
  result: NlqResponse;
  days?: number;
  onPinToDashboard?: () => void;
};

export function NlqAnswerCard({ result, days, onPinToDashboard }: NlqAnswerCardProps) {
  const value = result.metrics?.value;
  const format = result.format ?? "number";
  const display =
    value != null && typeof value === "number" && value > 0
      ? format === "currency"
        ? formatCurrency(value)
        : formatNumber(value)
      : value === 0
        ? format === "currency"
          ? formatCurrency(0)
          : formatNumber(0)
        : null;

  return (
    <div className="rounded-xl border border-sky-400/20 bg-gradient-to-br from-sky-500/10 to-indigo-500/10 p-4">
      {result.metric_label ? (
        <p className="text-xs font-semibold uppercase tracking-wide text-sky-300">
          {result.metric_label}
        </p>
      ) : null}
      {display ? <p className="mt-2 text-3xl font-bold text-white">{display}</p> : null}
      <p className="mt-2 text-sm leading-relaxed text-slate-200">{result.narrative}</p>
      {value === 0 ? (
        <p className="mt-2 text-xs text-amber-200/90">
          No rows in this period — try widening to 180 or 365 days for billing and finance metrics.
        </p>
      ) : null}
      {result.resolved_from ? (
        <p className="mt-2 text-xs text-slate-500">
          Source:{" "}
          <Link
            href={`/explore/${result.resolved_from}?tab=model`}
            className="text-sky-400 hover:text-sky-300"
          >
            {result.resolved_from.replace(/_RPT_CURR$/, "").replace(/_/g, " ")}
          </Link>
          {days ? ` · last ${days} days` : ""}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {result.resolved_from ? (
          <Link
            href={`/explore/${result.resolved_from}`}
            className="btn-ghost text-xs"
          >
            Open in explorer
          </Link>
        ) : null}
        {onPinToDashboard ? (
          <button type="button" onClick={onPinToDashboard} className="btn-ghost text-xs">
            Pin to dashboard
          </button>
        ) : null}
      </div>
      {result.table?.rows?.length ? (
        <div className="mt-3 overflow-auto rounded-lg border border-white/5">
          <table className="min-w-full text-left text-xs">
            <thead>
              <tr>
                {result.table.columns.map((c) => (
                  <th key={c} className="px-3 py-2 text-slate-500">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.table.rows.slice(0, 8).map((row, i) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="px-3 py-1.5 text-slate-200">{row.label}</td>
                  <td className="px-3 py-1.5 text-slate-200">{row.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
