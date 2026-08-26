"use client";

/**
 * Data Quality board — the rules engine's findings as a CIS worklist.
 *
 * Every card is one rule run against this tenant's governed reporting canvases:
 * severity, plain-English title, the exact action to take in CIS, and the finding
 * rows. Act-now findings open expanded; clean rules collapse to a single line so
 * the page reads as "what needs attention", not "what we checked".
 */
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type DqRule = {
  id: string;
  object: string;
  severity: "action" | "review" | "info";
  title: string;
  action: string;
  columns: string[];
  rows: (string | null)[][];
  acked_rows?: (string | null)[][];
  /** Server-computed ack key per row (rule's declared entity, not blindly col 0). */
  row_keys?: string[];
  acked_row_keys?: string[];
  count: number;
  capped?: boolean;
  error?: string;
};

type DqResponse = {
  configured: boolean;
  act_now?: number;
  review?: number;
  acknowledged?: number;
  refresh_marker?: string;
  rules: DqRule[];
  error?: string;
};

const SEV_STYLE: Record<string, string> = {
  action: "bg-red-800 text-white",
  review: "bg-amber-600 text-white",
  info: "bg-slate-500 text-white",
};
const SEV_LABEL: Record<string, string> = {
  action: "ACT NOW",
  review: "REVIEW",
  info: "INFO",
};

export function DataQualityBoard() {
  const [data, setData] = useState<DqResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const reload = () =>
    apiGet<DqResponse>("/dq/findings")
      .then(setData)
      .catch((e) => setErr(String(e)));
  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const mark = async (key: string, done: boolean) => {
    await apiPost(done ? "/dq/ack" : "/dq/unack", { key });
    await reload();
  };

  const rules = useMemo(() => {
    if (!data?.rules) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return data.rules;
    return data.rules.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        r.object.toLowerCase().includes(q) ||
        r.id.includes(q),
    );
  }, [data, filter]);

  if (err) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-800">
        Could not load data-quality findings: {err}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="animate-pulse space-y-3 p-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-16 rounded-lg bg-slate-100" />
        ))}
      </div>
    );
  }
  if (!data.configured) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
        No reporting warehouse is configured for this organization, so the
        data-quality rules have nothing to run against.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Data Quality</h1>
          <p className="text-sm text-slate-500">
            Rules run against the governed reporting canvases; every finding says
            exactly where to act in CIS.
          </p>
        </div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter rules…"
          aria-label="Filter rules"
          className="w-56 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
        />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="Act-now findings" value={data.act_now ?? 0} tone="red" />
        <SummaryCard label="Review findings" value={data.review ?? 0} tone="amber" />
        <SummaryCard label="Rules run" value={data.rules.length} tone="slate" />
        <SummaryCard
          label="Marked done (until refresh)"
          value={data.acknowledged ?? 0}
          tone="green"
        />
      </div>

      <div className="space-y-2">
        {rules.map((r) => (
          <details
            key={r.id}
            open={r.severity === "action" && r.count > 0}
            className="rounded-lg border border-slate-200 bg-white shadow-sm"
          >
            <summary className="flex cursor-pointer items-center gap-3 px-4 py-3">
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-bold tracking-wide ${SEV_STYLE[r.severity]}`}
              >
                {SEV_LABEL[r.severity]}
              </span>
              <span className="font-medium text-slate-900">{r.title}</span>
              <span className="ml-auto text-sm text-slate-500">
                {r.error
                  ? "rule error"
                  : r.count
                    ? `${r.count}${r.capped ? "+" : ""} finding${r.count === 1 ? "" : "s"}`
                    : "clean"}
                {" · "}
                {r.object}
              </span>
            </summary>
            <div className="border-t border-slate-100 px-4 py-3">
              <p className="mb-3 rounded-md border-l-2 border-teal-700 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                <span className="font-semibold">What to do: </span>
                {r.action}
              </p>
              {r.error ? (
                <p className="text-sm text-red-700">rule error: {r.error}</p>
              ) : r.count === 0 ? (
                <p className="text-sm text-slate-400">No findings — clean.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs">
                    <thead>
                      <tr>
                        <th className="border-b border-slate-200 bg-slate-50 px-2 py-1.5" />
                        {r.columns.map((c) => (
                          <th
                            key={c}
                            className="whitespace-nowrap border-b border-slate-200 bg-slate-50 px-2 py-1.5 text-left font-semibold text-slate-600"
                          >
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {r.rows.map((row, i) => (
                        <tr key={i} className="border-b border-slate-100">
                          <td className="px-2 py-1">
                            <button
                              onClick={() => mark(r.row_keys?.[i] ?? `${r.id}|${row[0]}`, true)}
                              title="Mark done until the next data refresh"
                              className="rounded border border-emerald-600 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700 hover:bg-emerald-50"
                            >
                              Done
                            </button>
                          </td>
                          {row.map((v, j) => (
                            <td key={j} className="whitespace-nowrap px-2 py-1 text-slate-700">
                              {v ?? ""}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {r.capped && (
                    <p className="mt-1 text-xs text-slate-400">showing first 100</p>
                  )}
                </div>
              )}
              {(r.acked_rows?.length ?? 0) > 0 && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-slate-400">
                    {r.acked_rows!.length} marked done (hidden until the next data
                    refresh)
                  </summary>
                  <ul className="mt-1 space-y-0.5 text-xs text-slate-500">
                    {r.acked_rows!.map((row, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <button
                          onClick={() => mark(r.acked_row_keys?.[i] ?? `${r.id}|${row[0]}`, false)}
                          className="rounded border border-slate-300 px-1.5 py-0.5 text-[10px] hover:bg-slate-50"
                        >
                          Undo
                        </button>
                        <span className="line-through">{row.filter(Boolean).slice(0, 4).join(" · ")}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "red" | "amber" | "green" | "slate";
}) {
  const tones: Record<string, string> = {
    red: "text-red-800",
    amber: "text-amber-700",
    green: "text-emerald-700",
    slate: "text-slate-800",
  };
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className={`text-2xl font-semibold ${tones[tone]}`}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}
