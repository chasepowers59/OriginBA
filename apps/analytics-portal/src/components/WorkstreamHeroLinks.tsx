"use client";

import Link from "next/link";
import type { SnapshotSummary, WorkstreamGroup } from "@/lib/types";

export function WorkstreamHeroLinks({
  workstreamId,
  workstreams,
}: {
  workstreamId: string;
  workstreams: WorkstreamGroup[];
}) {
  const ws = workstreams.find((w) => w.id === workstreamId);
  const featured = ws?.featured ?? [];
  const snapshots = ws?.snapshots ?? [];
  const top = featured.length
    ? featured
    : snapshots.slice(0, 3).map((s) => ({ snapshot_id: s.id, report_id: "" }));

  if (!top.length) return null;

  return (
    <div className="glass-panel p-5">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-sky-400/80">
        Start here
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {top.map((item) => {
          const snap = snapshots.find((s) => s.id === item.snapshot_id);
          const label = snap?.label ?? item.snapshot_id;
          const reportQs = item.report_id ? `?report=${item.report_id}` : "";
          return (
            <div
              key={item.snapshot_id}
              className="rounded-xl border border-edge-subtle bg-surface-subtle p-4"
            >
              <p className="font-medium text-heading">{label}</p>
              <p className="mt-1 text-xs text-fg-muted">{snap?.grain_description ?? snap?.summary}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  href={`/explore/${item.snapshot_id}${reportQs}`}
                  className="text-xs text-sky-400 hover:text-sky-300"
                >
                  Run report →
                </Link>
                <Link
                  href={`/explore/${item.snapshot_id}?tab=model`}
                  className="text-xs text-fg-muted hover:text-heading"
                >
                  Data model
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
