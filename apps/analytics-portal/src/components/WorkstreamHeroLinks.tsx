"use client";

import Link from "next/link";
import { featuredCanvases } from "@/lib/featuredCanvases";
import type { WorkstreamGroup } from "@/lib/types";

export function WorkstreamHeroLinks({
  workstreamId,
  workstreams,
}: {
  workstreamId: string;
  workstreams: WorkstreamGroup[];
}) {
  const ws = workstreams.find((w) => w.id === workstreamId);
  const top = featuredCanvases(ws?.featured, ws?.snapshots);

  if (!top.length) return null;

  return (
    <div className="glass-panel p-5">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-heading-accent">
        Start here
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        {top.map((item) => {
          const reportQs = item.reportId ? `?report=${item.reportId}` : "";
          return (
            <div
              key={item.snapshotId}
              className="rounded-xl border border-edge-subtle bg-surface-subtle p-4"
            >
              <p className="font-medium text-heading">{item.label}</p>
              <p className="mt-1 text-xs text-fg-muted">{item.description}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  href={`/explore/${item.snapshotId}${reportQs}`}
                  className="text-xs text-primary hover:text-primary"
                >
                  Run report →
                </Link>
                <Link
                  href={`/explore/${item.snapshotId}?tab=model`}
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
