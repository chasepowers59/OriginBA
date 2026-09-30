"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { useSearchParams } from "next/navigation";
import { fetchReportLibrary } from "@/lib/api";
import { folderToShow, libraryHref, searchLibrary, shapeLine, splitFolder, type SearchGroup } from "@/lib/libraryLayout";
import type { ReportLibraryEntry, ReportLibraryFolder } from "@/lib/types";

/**
 * The library is where somebody who does not know the data goes to find a question
 * already answered. It is a folder tree: the rail lists the folders, the selected folder
 * leads with the few reports to start with and keeps the rest folded underneath, and one
 * search box looks across every folder. Folder and search ride in the URL (?folder=, ?q=)
 * so a shared link and Back restore the view.
 */
export function ReportLibrary() {
  const params = useSearchParams();
  const requested = params.get("folder");
  const urlQuery = params.get("q") ?? "";
  const [folders, setFolders] = useState<ReportLibraryFolder[]>([]);
  const [query, setQuery] = useState(urlQuery);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReportLibrary()
      .then((data) => setFolders(data.folders ?? []))
      .catch(() => setError("Couldn't load the report library."))
      .finally(() => setLoading(false));
  }, []);

  // Only Back and Forward change ?q under the box. Syncing from the router's search params
  // instead reverted a fast typist: the router applies each keystroke's URL in a transition,
  // so an older value lands after newer keystrokes.
  useEffect(() => {
    const restore = () => setQuery(new URLSearchParams(window.location.search).get("q") ?? "");
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  const folder = folderToShow(folders, requested);
  const results = useMemo(() => searchLibrary(folders, query), [folders, query]);
  const searching = query.trim().length > 0;
  const totalReports = folders.reduce((n, f) => n + f.reports.length, 0);

  function onSearch(value: string) {
    setQuery(value);
    // replaceState, not a navigation: a keystroke is not a history entry, and a router
    // navigation would re-render the server page on every letter.
    window.history.replaceState(null, "", libraryHref({ folder: requested, q: value }));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">Utility analytics</p>
          <h1 className="mt-1 text-2xl font-bold text-heading">Report library</h1>
          <p className="mt-2 max-w-2xl text-sm text-fg-muted">
            Governed reports, each opening with the right period and chart. Start with a folder&apos;s
            essentials, or search every folder at once.
          </p>
        </div>
        {folders.length ? (
          <div className="w-full max-w-sm">
            <input
              type="search"
              value={query}
              onChange={(e) => onSearch(e.target.value)}
              placeholder="Search all reports — try arrears, meter, cycle…"
              aria-label="Search the report library"
              className="input-modern"
            />
            <p className="mt-1.5 text-xs text-fg-muted" aria-live="polite">
              {searching
                ? `${results.reduce((n, g) => n + g.reports.length, 0)} of ${totalReports} reports match`
                : `${totalReports} reports in ${folders.length} folders`}
            </p>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="loading-shimmer h-48 rounded-2xl" />
      ) : error || !folder ? (
        <div className="glass-panel p-8 text-center text-sm text-fg-muted">
          {error ?? "No reports are available for this organization yet."}{" "}
          <button type="button" onClick={() => location.reload()} className="text-primary hover:underline">
            Retry
          </button>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <FolderRail folders={folders} current={searching ? null : folder.id} onPick={() => setQuery("")} />
          <div className="min-w-0">
            {searching ? (
              <SearchResults query={query.trim()} results={results} onClear={() => onSearch("")} />
            ) : (
              <FolderView folder={folder} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * A real link (copy it, open it in a tab) that, on a plain click, changes the URL in place:
 * a router navigation would refetch the server-rendered page just to move a highlight.
 */
function inPlace(href: string, then?: () => void) {
  return (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    window.history.pushState(null, "", href);
    then?.();
  };
}

function FolderRail({ folders, current, onPick }: {
  folders: ReportLibraryFolder[];
  current: string | null;
  /** a folder click leaves search: its link carries no ?q */
  onPick: () => void;
}) {
  return (
    <nav aria-label="Report folders" className="glass-panel self-start p-3 lg:sticky lg:top-24">
      <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-heading-accent">Folders</p>
      <ul className="space-y-0.5">
        {folders.map((f) => {
          const active = f.id === current;
          const href = libraryHref({ folder: f.id });
          return (
            <li key={f.id}>
              <a
                href={href}
                onClick={inPlace(href, onPick)}
                aria-current={active ? "page" : undefined}
                className={`flex items-baseline justify-between gap-3 rounded-lg px-3 py-2 text-sm transition ${
                  active ? "tint-active font-medium text-heading" : "text-fg-muted hover:bg-chip hover:text-heading"
                }`}
              >
                <span>{f.title}</span>
                <span className="text-xs tabular-nums text-fg-subtle">{f.report_count}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function FolderView({ folder }: { folder: ReportLibraryFolder }) {
  const { essentials, more } = splitFolder(folder);
  return (
    <section aria-labelledby="library-folder-title" className="glass-panel p-6">
      <h2 id="library-folder-title" className="text-xl font-semibold text-heading">{folder.title}</h2>
      {folder.description ? <p className="mt-1 text-sm text-fg-muted">{folder.description}</p> : null}

      {essentials.length ? (
        <>
          <h3 className="mb-3 mt-6 text-[11px] font-semibold uppercase tracking-widest text-heading-accent">
            Start here
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {essentials.map((r) => (
              <EssentialCard key={`${r.snapshot_id}-${r.report_id}`} report={r} />
            ))}
          </div>
        </>
      ) : null}

      {more.length ? (
        // keyed on the folder so moving to another folder starts it folded again; open
        // outright when access left this folder with no essentials to lead with
        <details key={folder.id} open={!essentials.length} className="group/more mt-6 border-t border-edge-subtle pt-4">
          <summary className="flex cursor-pointer list-none items-center gap-2 rounded-lg text-sm font-medium text-heading [&::-webkit-details-marker]:hidden">
            <ChevronRight
              aria-hidden
              className="h-4 w-4 text-fg-muted transition-transform group-open/more:rotate-90 motion-reduce:transition-none"
            />
            {essentials.length ? "More in this folder" : "Reports in this folder"}
            <span className="font-normal text-fg-muted">({more.length})</span>
          </summary>
          <ul className="mt-2 divide-y divide-edge-subtle">
            {more.map((r) => (
              <li key={`${r.snapshot_id}-${r.report_id}`}>
                <ReportRow report={r} />
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

function SearchResults({ query, results, onClear }: { query: string; results: SearchGroup[]; onClear: () => void }) {
  if (!results.length) {
    return (
      <div className="glass-panel p-8 text-center">
        <p className="text-sm text-heading">No report matches “{query}”.</p>
        <p className="mt-1 text-xs text-fg-muted">Try a broader word, or build the question yourself.</p>
        <div className="mt-3 flex justify-center gap-2">
          <button type="button" onClick={onClear} className="btn-ghost text-xs">
            Clear search
          </button>
          <Link href="/build" className="btn-ghost text-xs">
            Open Build
          </Link>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {results.map(({ folder, reports }) => (
        <section key={folder.id} aria-label={folder.title} className="glass-panel p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-base font-semibold text-heading">{folder.title}</h2>
            <span className="text-xs text-fg-muted">
              {reports.length} of {folder.report_count}
            </span>
          </div>
          <ul className="mt-2 divide-y divide-edge-subtle">
            {reports.map((r) => (
              <li key={`${r.snapshot_id}-${r.report_id}`}>
                <ReportRow report={r} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function EssentialCard({ report }: { report: ReportLibraryEntry }) {
  const shape = shapeLine(report);
  return (
    <Link
      href={report.explore_url}
      className="group/report flex flex-col rounded-xl border border-edge-subtle bg-surface-subtle p-4 transition hover:border-edge motion-reduce:transition-none"
    >
      <h4 className="font-medium text-heading group-hover/report:text-primary">{report.title}</h4>
      <p className="mt-1.5 line-clamp-3 text-sm text-fg-muted">{report.description}</p>
      {shape ? <p className="mt-auto pt-3 text-xs text-fg-subtle">{shape}</p> : null}
    </Link>
  );
}

function ReportRow({ report }: { report: ReportLibraryEntry }) {
  return (
    <Link
      href={report.explore_url}
      className="group/report flex items-center justify-between gap-4 rounded-lg px-2 py-2.5 transition hover:bg-chip motion-reduce:transition-none"
    >
      <span className="min-w-0">
        <span className="block text-sm font-medium text-heading group-hover/report:text-primary">{report.title}</span>
        {report.description ? (
          <span className="block truncate text-xs text-fg-muted" title={report.description}>
            {report.description}
          </span>
        ) : null}
      </span>
      <ChevronRight aria-hidden className="h-4 w-4 shrink-0 text-fg-subtle group-hover/report:text-primary" />
    </Link>
  );
}
