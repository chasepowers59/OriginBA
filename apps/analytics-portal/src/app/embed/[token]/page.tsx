"use client";

import { use, useEffect, useState } from "react";
import { DatabaseResultChart } from "@/components/DatabaseResultChart";
import { BrandMark } from "@/components/BrandMark";
import { fetchEmbed, type EmbedData } from "@/lib/api";
import { resultChart } from "@/lib/assistant";
import { formatCellValue } from "@/lib/format";

/**
 * A saved view embedded in another site through a signed, expiring link (api/embed.py).
 * No sign-in, no navigation: the view's title, a chart when one reads better, and the table.
 */
export default function EmbedPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const [data, setData] = useState<EmbedData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEmbed(token).then(setData).catch((e) => setError(e instanceof Error ? e.message : "This view could not be loaded."));
  }, [token]);

  if (error) return <main className="p-6 text-sm text-over" role="alert">{error}</main>;
  if (!data) return <main className="p-6 text-sm text-fg-muted">Loading…</main>;

  const matrix = { columns: data.columns, rows: data.rows.map((r) => data.columns.map((c) => r[c])) };
  const chart = resultChart(matrix);
  return (
    <main className="space-y-3 bg-surface-solid p-4">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-heading">{data.title}</h1>
        <BrandMark className="h-5 w-auto" />
      </header>
      {chart ? <DatabaseResultChart rows={data.rows} suggestion={chart} /> : null}
      <div className="overflow-auto rounded-lg border border-edge-subtle">
        <table className="min-w-full text-left text-xs">
          <thead>
            <tr>{data.columns.map((c) => <th key={c} scope="col" className="px-3 py-2 text-fg-muted">{c}</th>)}</tr>
          </thead>
          <tbody>
            {data.rows.map((r, i) => (
              <tr key={i} className="border-t border-edge-subtle">
                {data.columns.map((c) => <td key={c} className="px-3 py-1.5 text-heading">{formatCellValue(r[c], { columnId: c })}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
