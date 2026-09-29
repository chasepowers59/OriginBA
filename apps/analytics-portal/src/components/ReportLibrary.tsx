"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { reportsByWorkstream, sectionsStartOpen } from "@/lib/libraryLayout";
import { useSearchParams } from "next/navigation";
import { fetchReportLibrary } from "@/lib/api";
import { reportShape } from "@/lib/reportShape";
import type { ReportLibraryPack, ReportLibraryEntry } from "@/lib/types";

/**
 * The library is where somebody who does not know the data goes to find a question
 * already answered: search across every report, grouped by workstream (the one grouping,
 * UI-4), and each card says what the report RETURNS. A title tells you the question and
 * the paragraph tells you why it matters; neither says whether it counts rows or sums
 * money, or that it is already filtered.
 */
export function ReportLibrary({ workstreamOrder }: { workstreamOrder: string[] }) {
  const [packs, setPacks] = useState<ReportLibraryPack[]>([]);
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

  const sections = useMemo(() => reportsByWorkstream(packs, workstreamOrder), [packs, workstreamOrder]);
  const totalReports = sections.reduce((n, s) => n + s.reports.length, 0);

  // Search covers everything a reader might remember: the question, why it matters, the
  // data set it reads, and the columns it groups by. Matching only the title meant
  // "arrears" found nothing while three reports grouped by an arrears band.
  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const inScope = workstreamFilter ? sections.filter((s) => s.workstream === workstreamFilter) : sections;
    return inScope
      .map((section) => ({
        section,
        reports: section.reports.filter((r) => {
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
  }, [sections, query, workstreamFilter]);

  const shown = results.reduce((n, g) => n + g.reports.length, 0);
  const open = sectionsStartOpen({ query, workstream: workstreamFilter, sectionCount: results.length });

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
      ) : error || !sections.length ? (
        <div className="glass-panel p-8 text-center text-sm text-fg-muted">
          {error ?? "No reports are available for this organization yet."}{" "}
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
                : `${totalReports} reports in ${sections.length} workstreams`}
            </p>
          </div>

          {results.length === 0 ? (
            <div className="glass-panel p-8 text-center">
              <p className="text-sm text-heading">
                {query.trim()
                  ? `No report matches “${query.trim()}”${workstreamFilter ? " in this workstream" : ""}.`
                  : "No reports in this workstream."}
              </p>
              <p className="mt-1 text-xs text-fg-muted">
                Try a broader word, or build the question yourself.
              </p>
              <div className="mt-3 flex justify-center gap-2">
                <button type="button" onClick={() => setQuery("")} className="btn-ghost text-xs">
                  Clear search
                </button>
                <Link href="/build" className="btn-ghost text-xs">
                  Open Build →
                </Link>
              </div>
            </div>
          ) : (
            results.map(({ section, reports }) => (
              // keyed on `open` so narrowing the list re-opens sections the reader had folded
              <details key={`${section.workstream}-${open}`} open={open} className="glass-panel group p-5">
                <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-lg font-semibold text-heading">{section.label}</h2>
                    <span className="flex items-center gap-2 text-xs text-fg-muted">
                      {reports.length}
                      {reports.length !== section.reports.length ? ` of ${section.reports.length}` : ""} reports
                      <span aria-hidden className="transition group-open:rotate-180">▾</span>
                    </span>
                  </div>
                </summary>
                <div className="mt-4 grid gap-3 border-t border-edge-subtle pt-4 sm:grid-cols-2">
                  {reports.map((report) => (
                    <ReportCard key={`${report.snapshot_id}-${report.report_id}`} report={report} />
                  ))}
                </div>
              </details>
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
        <h3 className="font-medium text-heading group-hover:text-primary dark:group-hover:text-primary">
          {report.title}
        </h3>
        <span className="shrink-0 text-fg-muted transition group-hover:text-primary dark:group-hover:text-primary">
          Open →
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-xs text-fg-muted">{report.description}</p>

      {/* What you actually get, in one line, before you open it. */}
      {shape ? (
        <p className="mt-2 line-clamp-2 text-[11px] text-fg" title={shape}>
          {shape}
        </p>
      ) : null}

      <p className="mt-auto pt-2 text-[10px] text-fg-subtle">
        From the {report.snapshot_label} data set
        {report.grain_description ? ` · ${report.grain_description.toLowerCase()}` : ""}
      </p>
    </Link>
  );
}
