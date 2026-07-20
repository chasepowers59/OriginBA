"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { workstreamDisplayName } from "@/lib/businessLabels";
import { workstreamIcon } from "@/lib/workstreamIcons";

export function SidebarNav({
  snapshots,
  activeId,
}: {
  snapshots: {
    id: string;
    label: string;
    workstream: string;
    workstream_label?: string;
  }[];
  activeId?: string;
}) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return snapshots;
    return snapshots.filter(
      (s) =>
        s.label.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q) ||
        s.workstream.toLowerCase().includes(q) ||
        (s.workstream_label ?? "").toLowerCase().includes(q),
    );
  }, [snapshots, query]);

  const grouped = filtered.reduce<Record<string, typeof snapshots>>((acc, snap) => {
    acc[snap.workstream] = acc[snap.workstream] ?? [];
    acc[snap.workstream].push(snap);
    return acc;
  }, {});

  return (
    <div className="glass-panel p-4">
      <div className="mb-4">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-sky-400/80">
          Report domains
        </p>
        <input
          type="search"
          placeholder="Search by name or area…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="input-modern"
        />
      </div>
      <div className="max-h-[calc(100vh-280px)] space-y-4 overflow-y-auto pr-1">
        {Object.entries(grouped).map(([workstream, items]) => (
          <div key={workstream}>
            <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              <span className="text-sky-400">{workstreamIcon(workstream)}</span>
              {items[0]?.workstream_label ?? workstreamDisplayName(workstream)}
            </div>
            <ul className="space-y-1">
              {items.map((snap) => {
                const active = activeId === snap.id;
                return (
                  <li key={snap.id}>
                    <Link
                      href={`/explore/${snap.id}`}
                      className={`group block rounded-xl px-3 py-2.5 text-sm transition ${
                        active
                          ? "bg-gradient-to-r from-sky-500/20 to-indigo-500/20 text-white ring-1 ring-sky-400/30"
                          : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                      }`}
                    >
                      <span className="font-medium">{snap.label}</span>
                      {active ? (
                        <span className="mt-1 block text-[10px] text-sky-300/80">Currently viewing</span>
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        {filtered.length === 0 ? (
          <p className="text-sm text-slate-500">No report domains match your search.</p>
        ) : null}
      </div>
    </div>
  );
}
