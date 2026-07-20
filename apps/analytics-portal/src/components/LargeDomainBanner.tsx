"use client";

import Link from "next/link";
import { formatNumber } from "@/lib/format";

export function LargeDomainBanner({
  snapshotId,
  snapshotLabel,
  rowCount,
  grainDescription,
}: {
  snapshotId: string;
  snapshotLabel: string;
  rowCount?: number | null;
  grainDescription?: string;
}) {
  return (
    <div className="glass-panel border-amber-400/25 bg-gradient-to-r from-amber-500/10 to-orange-500/5 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-amber-300">
            Large governed domain
          </p>
          <h3 className="mt-1 text-lg font-semibold text-white">{snapshotLabel}</h3>
          <p className="mt-2 text-sm text-amber-100/90">
            This snapshot has{" "}
            {rowCount != null ? (
              <strong>{formatNumber(rowCount)}</strong>
            ) : (
              "millions of"
            )}{" "}
            rows. Row preview is skipped in the portal so analysis stays fast — use a{" "}
            <strong>30-day default period</strong>, premade reports, or the data model tab
            instead of loading sample rows.
          </p>
          {grainDescription ? (
            <p className="mt-2 text-xs text-amber-200/70">{grainDescription}</p>
          ) : null}
        </div>
        <Link
          href={`/explore/${snapshotId}?tab=model`}
          className="btn-primary shrink-0 text-xs"
        >
          View field catalog →
        </Link>
      </div>
    </div>
  );
}
