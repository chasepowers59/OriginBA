"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { WORKSTREAM_DESCRIPTIONS, workstreamDisplayName } from "@/lib/businessLabels";
import { exploreUrl } from "@/lib/processGuide";
import { workstreamIcon } from "@/lib/workstreamIcons";
import { groupByDataset } from "@/lib/workstreamDatasets";
import type { BusinessProcess, SnapshotSummary, WorkstreamGroup } from "@/lib/types";
import { SnapshotCard } from "./HomeDashboard";

export function WorkstreamSidebarNav({
  workstreams,
  activeId,
  filterMode,
}: {
  workstreams: WorkstreamGroup[];
  activeId?: string;
  /** On Library the rail FILTERS the page instead of navigating away from it. */
  filterMode?: boolean;
}) {
  const searchParams = useSearchParams();
  return (
    <WorkstreamSidebar
      workstreams={workstreams}
      activeId={activeId ?? (filterMode ? searchParams.get("workstream") ?? undefined : undefined)}
      filterMode={filterMode}
      activeProcessId={searchParams.get("process") ?? undefined}
      activeReportId={searchParams.get("report") ?? undefined}
    />
  );
}

function filterProcesses(processes: BusinessProcess[], q: string): BusinessProcess[] {
  if (!q) return processes;
  return processes
    .map((process) => ({
      ...process,
      reports: process.reports.filter(
        (report) =>
          process.label.toLowerCase().includes(q) ||
          process.description.toLowerCase().includes(q) ||
          report.title.toLowerCase().includes(q) ||
          report.snapshot_id.toLowerCase().includes(q),
      ),
    }))
    .filter((process) => process.reports.length > 0);
}

export function WorkstreamSidebar({
  workstreams,
  activeId,
  activeProcessId,
  activeReportId,
  filterMode,
}: {
  workstreams: WorkstreamGroup[];
  activeId?: string;
  activeProcessId?: string;
  activeReportId?: string;
  filterMode?: boolean;
}) {
  const [expandedWs, setExpandedWs] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(workstreams.map((ws) => [ws.id, true])),
  );
  const [expandedProcess, setExpandedProcess] = useState<Record<string, boolean>>({});
  const [query, setQuery] = useState("");

  const filteredWorkstreams = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return workstreams;
    return workstreams
      .map((ws) => ({
        ...ws,
        processes: filterProcesses(ws.processes ?? [], q),
      }))
      .filter((ws) => (ws.processes?.length ?? 0) > 0 || ws.label.toLowerCase().includes(q));
  }, [workstreams, query]);

  return (
    <div>
      <div className="mb-4 space-y-1 border-b border-edge-subtle pb-4">
        <Link
          href="/dashboards"
          className="block rounded-xl px-3 py-2 text-sm font-medium text-fg transition hover:bg-chip hover:text-heading"
        >
          Custom dashboards
        </Link>
      </div>
      <input
        type="search"
        placeholder="Search processes…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="input-modern mb-3 text-xs"
      />
      {filterMode && activeId ? (
        <Link
          href="/reports"
          className="mb-3 flex items-center justify-between rounded-lg bg-chip px-3 py-2 text-xs text-heading"
        >
          <span>Filtered to one workstream</span>
          <span className="text-fg-muted">Clear ×</span>
        </Link>
      ) : null}
      <div className="max-h-[calc(100vh-320px)] space-y-4 overflow-y-auto pr-1">
        {groupByDataset(filteredWorkstreams).map((dataset) => (
        <div key={dataset.id}>
          {/* C side / M side / assets / shared -- the shape of C2M, which a flat list
              of nine workstreams hid from anyone who did not already know it. */}
          <p
            className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle"
            title={dataset.hint}
          >
            {dataset.label}
          </p>
          <div className="space-y-3">
        {dataset.workstreams.map((ws) => {
        const wsOpen = expandedWs[ws.id] ?? true;
        const processes = ws.processes ?? [];
        return (
          <div key={ws.id}>
            <button
              type="button"
              onClick={() => setExpandedWs((p) => ({ ...p, [ws.id]: !wsOpen }))}
              className="mb-1 flex w-full items-center gap-2 text-left text-[11px] font-semibold uppercase tracking-wide text-fg-muted"
            >
              <span className="text-primary">{workstreamIcon(ws.id)}</span>
              <Link
                href={filterMode ? `/reports?workstream=${ws.id}` : `/workstream/${ws.id}`}
                onClick={(e) => e.stopPropagation()}
                aria-current={activeId === ws.id ? "true" : undefined}
                className={`flex-1 hover:text-primary ${
 activeId === ws.id ? "text-primary" : ""
 }`}
              >
                {ws.label ?? workstreamDisplayName(ws.id)}
                {typeof ws.snapshot_count === "number" ? (
                  <span className="ml-1 font-normal opacity-60">({ws.snapshot_count})</span>
                ) : null}
              </Link>
              <span className="text-fg-muted">{wsOpen ? "▾" : "▸"}</span>
            </button>
            {wsOpen ? (
              <ul className="space-y-2 pl-1">
                {processes.map((process) => {
                  const procKey = `${ws.id}:${process.id}`;
                  const procOpen = expandedProcess[procKey] ?? activeProcessId === process.id;
                  return (
                    <li key={process.id}>
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedProcess((p) => ({ ...p, [procKey]: !procOpen }))
                        }
                        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs font-medium text-fg-muted hover:bg-chip hover:text-heading"
                      >
                        <span className="flex-1">{process.label}</span>
                        <span className="text-fg-muted">{procOpen ? "▾" : "▸"}</span>
                      </button>
                      {procOpen ? (
                        <ul className="mt-1 space-y-0.5 border-l border-edge-subtle pl-3">
                          {process.reports.map((report) => {
                            const active =
                              activeId === report.snapshot_id &&
                              activeProcessId === process.id &&
                              (!report.report_id || activeReportId === report.report_id);
                            return (
                              <li key={`${report.snapshot_id}:${report.report_id ?? "browse"}`}>
                                <Link
                                  href={exploreUrl(report.snapshot_id, {
                                    processId: process.id,
                                    reportId: report.report_id,
                                  })}
                                  className={`block rounded-lg px-2 py-1.5 text-sm transition ${
 active
 ? "tint-active text-heading ring-1 ring-edge"
 : "text-fg-muted hover:bg-chip hover:text-heading"
 }`}
                                >
                                  <span className="font-medium">{report.title}</span>
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>
        );
      })}
          </div>
        </div>
        ))}
        {filteredWorkstreams.length === 0 ? (
          <p className="text-xs text-fg-muted">No processes match your search.</p>
        ) : null}
      </div>
    </div>
  );
}

