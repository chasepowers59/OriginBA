"use client";

import { useEffect, useState } from "react";
import { fetchSnapshotSampleRows } from "@/lib/api";
import { formatCellValue } from "@/lib/format";
import { prettifyFieldName } from "@/lib/businessLabels";
import type { SampleRowsResponse } from "@/lib/types";

export function SampleRowsPanel({
  snapshotId,
  tableName,
  schemaName = "CISADM",
  grainDescription,
  skipSampleRows,
}: {
  snapshotId: string;
  tableName: string;
  /** The snapshot's own schema. A dbt canvas lives in `reporting`; only the legacy
   *  snapshots live in CISADM, and hardcoding it labelled every canvas wrongly. */
  schemaName?: string;
  grainDescription?: string;
  skipSampleRows?: boolean;
}) {
  const [data, setData] = useState<SampleRowsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    if (skipSampleRows) return;
    setData(null);
    setError(null);
    fetchSnapshotSampleRows(snapshotId, 3)
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Unable to load sample rows"),
      );
  }, [snapshotId, skipSampleRows]);

  if (skipSampleRows) return null;

  return (
    <div className="glass-panel overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-sky-400/80">
            Row preview
          </p>
          <h3 className="mt-1 text-lg font-semibold text-white">What one row looks like</h3>
          <p className="mt-1 text-sm text-slate-500">
            {grainDescription ?? "Sample rows from the governed snapshot table"} ·{" "}
            <code className="text-xs text-slate-400">{schemaName}.{tableName}</code>
          </p>
        </div>
        <span className="text-slate-500">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded ? (
        <div className="border-t border-white/10 px-5 pb-5">
          {error ? (
            <p className="mt-4 rounded-lg border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              {error.includes("503") || error.toLowerCase().includes("configured")
                ? "Connect your database in Settings to load live sample rows."
                : error}
            </p>
          ) : null}
          {!data && !error ? (
            <div className="loading-shimmer mt-4 h-32 rounded-xl" />
          ) : null}
          {data?.rows.length ? (
            <div className="mt-4 space-y-4">
              {data.rows.map((row, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-white/10 bg-slate-950/40 p-4"
                >
                  <p className="mb-3 text-xs font-medium text-sky-300">Sample row {idx + 1}</p>
                  <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {data.columns.map((col) => (
                      <div key={col} className="min-w-0">
                        <dt className="truncate text-[10px] uppercase tracking-wide text-slate-500">
                          {data.column_labels[col] ?? prettifyFieldName(col)}
                        </dt>
                        <dd className="truncate text-sm text-slate-200" title={String(row[col] ?? "")}>
                          {formatCellValue(row[col], { columnId: col })}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
              ))}
            </div>
          ) : null}
          {data && !data.rows.length && !error ? (
            <p className="mt-4 text-sm text-slate-500">No sample rows returned for this domain.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
