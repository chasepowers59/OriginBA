"use client";

import { useMemo, useState } from "react";
import { runSnapshotRawSql } from "@/lib/api";
import { exportRowsCsv, formatNumber } from "@/lib/format";
import { prettifyFieldName } from "@/lib/businessLabels";
import type { QueryResponse } from "@/lib/types";

export function RawSqlPanel({
  snapshotId,
  tableName,
}: {
  snapshotId: string;
  tableName: string;
}) {
  const defaultSql = useMemo(
    () =>
      `SELECT *\nFROM CISADM.${tableName}\nWHERE ROWNUM <= 25`,
    [tableName],
  );
  const [sql, setSql] = useState(defaultSql);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await runSnapshotRawSql(snapshotId, sql, 100);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel space-y-4 p-4">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          SQL workspace
        </p>
        <p className="mt-1 text-xs text-slate-600">
          Read-only SELECT against{" "}
          <code className="text-slate-400">CISADM.{tableName}</code> only. Read-only access.
        </p>
      </div>
      <textarea
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        rows={8}
        spellCheck={false}
        className="input-modern font-mono text-xs leading-relaxed"
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={run} disabled={loading} className="btn-primary">
          {loading ? "Running…" : "Run SQL"}
        </button>
        <button type="button" onClick={() => setSql(defaultSql)} className="btn-ghost">
          Reset template
        </button>
        {result ? (
          <button
            type="button"
            onClick={() =>
              exportRowsCsv(result.columns, result.rows, `${snapshotId}_sql_results.csv`)
            }
            className="btn-ghost"
          >
            Export results
          </button>
        ) : null}
      </div>
      {error ? (
        <p className="rounded-lg border border-red-400/20 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error.includes("503") || error.toLowerCase().includes("configured")
            ? "Database unavailable — check connection settings and ensure the API is running."
            : error}
        </p>
      ) : null}
      {result ? (
        <div className="overflow-hidden rounded-xl border border-white/10">
          <div className="border-b border-white/10 px-3 py-2 text-xs text-slate-500">
            {result.row_count} rows · capped at 100
          </div>
          <div className="max-h-80 overflow-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-950/95">
                <tr>
                  {result.columns.map((col) => (
                    <th key={col} className="px-3 py-2 font-medium text-slate-400">
                      {prettifyFieldName(col)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, idx) => (
                  <tr key={idx} className="border-t border-white/5">
                    {result.columns.map((col) => (
                      <td key={col} className="px-3 py-2 text-slate-200">
                        {formatNumber(row[col]) !== "—" && String(row[col]).match(/^-?\d/)
                          ? formatNumber(row[col])
                          : String(row[col] ?? "—")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <pre className="max-h-32 overflow-auto border-t border-white/10 bg-black/30 p-3 text-[10px] text-slate-500">
            {result.sql}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
