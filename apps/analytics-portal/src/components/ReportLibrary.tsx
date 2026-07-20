"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchReportLibrary } from "@/lib/api";
import type { ReportLibraryPack } from "@/lib/types";

export function ReportLibrary() {
  const [packs, setPacks] = useState<ReportLibraryPack[]>([]);
  const [activePack, setActivePack] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReportLibrary()
      .then((data) => {
        setPacks(data.packs);
        setActivePack(data.packs[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  const selected = packs.find((p) => p.id === activePack) ?? packs[0];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-400">
          Utility analytics
        </p>
        <h1 className="mt-1 text-2xl font-bold text-white">Report library</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Governed reports for billing, payments, operations, customer operations, and finance —
          each opens with the right period and chart for utility workflows.
        </p>
      </div>

      {loading ? (
        <div className="loading-shimmer h-48 rounded-2xl" />
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {packs.map((pack) => (
              <button
                key={pack.id}
                type="button"
                onClick={() => setActivePack(pack.id)}
                className={`chip ${activePack === pack.id ? "chip-active" : ""}`}
              >
                {pack.title}
                <span className="ml-1 opacity-60">({pack.report_count})</span>
              </button>
            ))}
          </div>

          {selected ? (
            <div className="glass-panel p-5">
              <div className="mb-4 border-b border-white/10 pb-4">
                <h2 className="text-lg font-semibold text-white">{selected.title}</h2>
                <p className="mt-1 text-sm text-slate-400">{selected.description}</p>
                <p className="mt-1 text-xs text-slate-500">For {selected.audience}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {selected.reports.map((report) => (
                  <Link
                    key={`${report.snapshot_id}-${report.report_id}`}
                    href={report.explore_url}
                    className="group rounded-xl border border-white/10 bg-slate-950/40 p-4 transition hover:border-sky-400/30 hover:bg-slate-900/60"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                        {report.workstream_label}
                      </span>
                      <span className="text-slate-600 transition group-hover:text-sky-400">
                        Open →
                      </span>
                    </div>
                    <h3 className="mt-2 font-medium text-white group-hover:text-sky-100">
                      {report.title}
                    </h3>
                    <p className="mt-1 line-clamp-2 text-xs text-slate-500">
                      {report.description}
                    </p>
                    <p className="mt-2 text-[10px] text-slate-600">{report.snapshot_label}</p>
                  </Link>
                ))}
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
