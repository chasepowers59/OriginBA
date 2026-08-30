"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { WORKSTREAM_DESCRIPTIONS, workstreamDisplayName } from "@/lib/businessLabels";
import { exploreUrl } from "@/lib/processGuide";
import { workstreamIcon } from "@/lib/workstreamIcons";
import type { BusinessProcess, SnapshotSummary, WorkstreamGroup } from "@/lib/types";
import { SnapshotCard } from "./HomeDashboard";

export function WorkstreamExplorer({
  workstreams,
}: {
  workstreams: WorkstreamGroup[];
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(workstreams.map((ws) => [ws.id, true])),
  );

  const toggle = (id: string) =>
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="space-y-4">
      {workstreams.map((ws) => {
        const isOpen = expanded[ws.id] ?? true;
        return (
          <section key={ws.id} className="glass-panel overflow-hidden">
            <button
              type="button"
              onClick={() => toggle(ws.id)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-white/[0.02]"
            >
              <div className="flex items-start gap-4">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-500/10 text-lg text-sky-300 ring-1 ring-sky-400/20">
                  {workstreamIcon(ws.id)}
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      href={`/workstream/${ws.id}`}
                      className="text-lg font-semibold text-white hover:text-sky-200"
                    >
                      {ws.label ?? workstreamDisplayName(ws.id)}
                    </Link>
                    <span className="chip">{ws.snapshot_count} snapshots</span>
                    <Link href={`/workstream/${ws.id}`} className="text-xs text-sky-400 hover:text-sky-300">
                      Dashboard →
                    </Link>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    {WORKSTREAM_DESCRIPTIONS[ws.id] ?? "Governed report domains"}
                  </p>
                </div>
              </div>
              <span className="shrink-0 text-slate-500">{isOpen ? "▾" : "▸"}</span>
            </button>
            {isOpen ? (
              <div className="border-t border-white/10 px-5 pb-5 pt-4">
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {ws.snapshots.map((snap) => (
                    <SnapshotCard key={snap.id} snap={snap} />
                  ))}
                </div>
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

export function WorkstreamSidebarNav({
  workstreams,
  activeId,
}: {
  workstreams: WorkstreamGroup[];
  activeId?: string;
}) {
  const searchParams = useSearchParams();
  return (
    <WorkstreamSidebar
      workstreams={workstreams}
      activeId={activeId}
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
}: {
  workstreams: WorkstreamGroup[];
  activeId?: string;
  activeProcessId?: string;
  activeReportId?: string;
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
      <div className="mb-4 space-y-1 border-b border-white/10 pb-4">
        <Link
          href="/dashboards"
          className="block rounded-xl px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-white/5 hover:text-white"
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
      <div className="max-h-[calc(100vh-320px)] space-y-3 overflow-y-auto pr-1">
        {filteredWorkstreams.map((ws) => {
        const wsOpen = expandedWs[ws.id] ?? true;
        const processes = ws.processes ?? [];
        return (
          <div key={ws.id}>
            <button
              type="button"
              onClick={() => setExpandedWs((p) => ({ ...p, [ws.id]: !wsOpen }))}
              className="mb-1 flex w-full items-center gap-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500"
            >
              <span className="text-sky-400">{workstreamIcon(ws.id)}</span>
              <Link
                href={`/workstream/${ws.id}`}
                onClick={(e) => e.stopPropagation()}
                className="flex-1 hover:text-sky-300"
              >
                {ws.label ?? workstreamDisplayName(ws.id)}
              </Link>
              <span className="text-slate-600">{wsOpen ? "▾" : "▸"}</span>
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
                        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs font-medium text-slate-400 hover:bg-white/5 hover:text-slate-200"
                      >
                        <span className="flex-1">{process.label}</span>
                        <span className="text-slate-600">{procOpen ? "▾" : "▸"}</span>
                      </button>
                      {procOpen ? (
                        <ul className="mt-1 space-y-0.5 border-l border-white/10 pl-3">
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
                                      ? "bg-gradient-to-r from-sky-500/20 to-indigo-500/20 text-white ring-1 ring-sky-400/30"
                                      : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
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
        {filteredWorkstreams.length === 0 ? (
          <p className="text-xs text-slate-500">No processes match your search.</p>
        ) : null}
      </div>
    </div>
  );
}

export function groupSnapshotsByWorkstream(
  snapshots: SnapshotSummary[],
  workstreamOrder: string[],
): WorkstreamGroup[] {
  const labels = new Map<string, string>();
  for (const snap of snapshots) {
    if (snap.workstream_label) labels.set(snap.workstream, snap.workstream_label);
  }
  const map = new Map<string, SnapshotSummary[]>();
  for (const snap of snapshots) {
    map.set(snap.workstream, [...(map.get(snap.workstream) ?? []), snap]);
  }
  return workstreamOrder
    .filter((id) => (map.get(id)?.length ?? 0) > 0)
    .map((id) => ({
      id,
      label: labels.get(id) ?? workstreamDisplayName(id),
      snapshot_count: map.get(id)?.length ?? 0,
      snapshots: map.get(id) ?? [],
    }));
}
