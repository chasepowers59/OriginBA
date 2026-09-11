"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { fetchReportLibrary } from "@/lib/api";
import { reportShape } from "@/lib/reportShape";
import type { ReportLibraryPack, ReportLibraryEntry } from "@/lib/types";

const ALL = "__all__";

/**
 * The library is where somebody who does not know the data goes to find a question
 * already answered. Two things it could not do: SEARCH -- 92 reports behind six pack
 * chips, one pack visible at a time, so finding "arrears" meant clicking through every
 * pack and reading -- and say what a report RETURNS. A title tells you the question and
 * the paragraph tells you why it matters; neither says whether it counts rows or sums
 * money, or that it is already filtered.
 */
export function ReportLibrary() {
  const [packs, setPacks] = useState<ReportLibraryPack[]>([]);
  const [activePack, setActivePack] = useState<string>(ALL);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // The workstream rail beside this list is a filter, not a second navigation: picking
  // "Collections & Debt" should narrow what is on screen, which is what a reader expects
  // of a tree sitting next to a list. It rides in the URL so it survives a reload and a
  // shared link, and composes with the search box rather than fighting it.
  const workstreamFilter = useSearchParams().get("workstream");

  useEffect(() => {
    fetchReportLibrary()
      .then((data) => setPacks(data.packs))
      .catch(() => setError("Couldn't load the report library."))
      .finally(() => setLoading(false));
  }, []);

  const totalReports = useMemo(
    () => packs.reduce((n, p) => n + p.reports.length, 0),
    [packs],
  );

  // Search covers everything a reader might remember: the question, why it matters, the
  // canvas it reads, and the columns it groups by. Matching only the title meant
  // "arrears" found nothing while three reports grouped by an arrears band.
  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const inScope = activePack === ALL ? packs : packs.filter((p) => p.id === activePack);
    return inScope
      .map((pack) => ({
        pack,
        reports: pack.reports.filter((r) => {
          if (workstreamFilter && r.workstream !== workstreamFilter) return false;
          if (!needle) return true;
          const haystack = [
            r.title,
            r.description,
            r.snapshot_label,
            r.workstream_label,
            ...(r.dimensions ?? []),
          ]
            .join(" ")
            .toLowerCase();
          return haystack.includes(needle);
        }),
      }))
      .filter((group) => group.reports.length > 0);
  }, [packs, activePack, query, workstreamFilter]);

  const shown = results.reduce((n, g) => n + g.reports.length, 0);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">
          Utility analytics
        </p>
        <h1 className="mt-1 text-2xl font-bold text-heading">Report library</h1>
        <p className="mt-2 max-w-2xl text-sm text-fg-muted">
          Governed reports for billing, payments, operations, customer operations and finance —
          each opens with the right period and chart for utility workflows.
        </p>
      </div>

      {loading ? (
        <div className="loading-shimmer h-48 rounded-2xl" />
      ) : error || !packs.length ? (
        <div className="glass-panel p-8 text-center text-sm text-fg-muted">
          {error ?? "No report packs are available for this organization yet."}{" "}
          <button
            type="button"
            onClick={() => location.reload()}
            className="text-primary hover:underline dark:text-primary"
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search reports — try arrears, meter, cycle…"
              aria-label="Search the report library"
              className="input-modern w-full sm:max-w-sm"
            />
            <p className="text-xs text-fg-muted" aria-live="polite">
              {query.trim() || workstreamFilter
                ? `${shown} of ${totalReports} reports match`
                : `${totalReports} reports across ${packs.length} packs`}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setActivePack(ALL)}
              className={`chip ${activePack === ALL ? "chip-active" : ""}`}
            >
              All packs
              <span className="ml-1 opacity-60">({totalReports})</span>
            </button>
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

          {results.length === 0 ? (
            <div className="glass-panel p-8 text-center">
              <p className="text-sm text-heading">
                {query.trim()
                  ? `No report matches “${query.trim()}”${workstreamFilter ? " in this workstream" : ""}.`
                  : "No reports in this workstream."}
              </p>
              <p className="mt-1 text-xs text-fg-muted">
                Try a broader word, or build the question yourself in Explore.
              </p>
              <div className="mt-3 flex justify-center gap-2">
                <button type="button" onClick={() => setQuery("")} className="btn-ghost text-xs">
                  Clear search
                </button>
                <Link href="/build" className="btn-ghost text-xs">
                  Open Explore →
                </Link>
              </div>
            </div>
          ) : (
            results.map(({ pack, reports }) => (
              <div key={pack.id} className="glass-panel p-5">
                <div className="mb-4 border-b border-edge-subtle pb-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-lg font-semibold text-heading">{pack.title}</h2>
                    <span className="text-xs text-fg-muted">
                      {reports.length}
                      {reports.length !== pack.report_count ? ` of ${pack.report_count}` : ""} reports
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-fg-muted">{pack.description}</p>
                  {pack.audience ? (
                    <p className="mt-1 text-xs text-fg-muted">For {pack.audience}</p>
                  ) : null}
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {reports.map((report) => (
                    <ReportCard key={`${report.snapshot_id}-${report.report_id}`} report={report} />
                  ))}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}

function ReportCard({ report }: { report: ReportLibraryEntry }) {
  const shape = reportShape(report);
  return (
    <Link
      href={report.explore_url}
      className="group flex flex-col rounded-xl border border-edge-subtle bg-surface-subtle p-4 transition hover:border-edge"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-[10px] font-medium uppercase tracking-wide text-fg-subtle">
          {report.workstream_label}
        </span>
        <span className="shrink-0 text-fg-muted transition group-hover:text-primary dark:group-hover:text-primary">
          Open →
        </span>
      </div>
      <h3 className="mt-2 font-medium text-heading group-hover:text-primary dark:group-hover:text-primary">
        {report.title}
      </h3>
      <p className="mt-1 line-clamp-2 text-xs text-fg-muted">{report.description}</p>

      {/* What you actually get, in one line, before you open it. */}
      {shape ? (
        <p className="mt-2 line-clamp-2 text-[11px] text-fg" title={shape}>
          {shape}
        </p>
      ) : null}

      <p className="mt-auto pt-2 text-[10px] text-fg-subtle">
        Reads {report.snapshot_label}
        {report.grain_description ? ` · ${report.grain_description.toLowerCase()}` : ""}
      </p>
    </Link>
  );
}
