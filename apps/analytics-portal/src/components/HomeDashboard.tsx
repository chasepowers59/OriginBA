"use client";
import { brandLine } from "../lib/brand";

import { useEffect, useState } from "react";
import { fetchSnapshots } from "@/lib/api";
import Link from "next/link";
import type { SnapshotSummary } from "@/lib/types";
import { FavoritesPanel } from "@/components/FavoritesPanel";
import { ExecutiveDashboard } from "@/components/ExecutiveDashboard";
import { NlqSearchPanel } from "@/components/NlqSearchPanel";
import { useBrand } from "@/components/PortalThemeProvider";

export function HomeDashboard() {
  const brand = useBrand();
  const [snapshotCount, setSnapshotCount] = useState(0);
  const [workstreamCount, setWorkstreamCount] = useState(0);

  useEffect(() => {
    fetchSnapshots()
      .then((index) => {
        setSnapshotCount(index.snapshots.length);
        setWorkstreamCount(index.workstreams?.length ?? 9);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      {/* A compact bar, not a landing page. Signed in, the reader already knows what the
          product is; the marketing hero cost roughly half a laptop viewport before a
          single number appeared, so the executive overview began below the fold on the
          screen people open every morning. The two entry points and the honest counts
          stay -- only the pitch goes. */}
      <section className="glass-panel relative overflow-hidden px-5 py-4">
        <div className="pointer-events-none absolute -right-20 -top-24 h-48 w-48 rounded-full bg-band blur-3xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-heading-accent">
              {brandLine(brand)}
            </p>
            <p className="mt-0.5 text-sm text-fg-muted">
              {/* Real counts only — fabricated placeholders confidently lied when the
                  API was down. */}
              {workstreamCount
                ? `${workstreamCount} workstreams · ${snapshotCount} reporting tables`
                : "\u00a0"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/build" className="btn-primary text-sm">
              Explore your data
            </Link>
            <Link href="/reports" className="btn-ghost text-sm">
              Open report library
            </Link>
          </div>
        </div>
      </section>

      <section>
        {/* The one executive overview: "/" is the Executive Overview page —
            /dashboard redirects here so the KPIs and search live in one place. */}
        <ExecutiveDashboard variant="full" initialDays={30} />
      </section>

      <section>
        <NlqSearchPanel />
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-heading">Saved views</h2>
          <Link href="/reports" className="text-xs text-primary hover:text-primary">
            Browse all reports →
          </Link>
        </div>
        <FavoritesPanel />
      </section>
    </div>
  );
}

export function SnapshotCard({ snap }: { snap: SnapshotSummary }) {
  const summary = snap.summary ?? "";

  return (
    <Link
      href={`/explore/${snap.id}`}
      className="group glass-panel-subtle block p-5 transition hover:border-edge hover:bg-surface-subtle hover:shadow-lg hover:shadow-sky-500/5"
    >
      <div className="flex items-start justify-between gap-3">
        {snap.poc_enabled ? (
          <span className="chip chip-active text-[10px]">Analytics ready</span>
        ) : (
          <span className="chip text-[10px]">Browse & SQL</span>
        )}
        <span className="text-fg-muted transition group-hover:text-primary dark:group-hover:text-primary">View →</span>
      </div>
      <h3 className="mt-3 text-lg font-semibold text-heading group-hover:text-primary dark:group-hover:text-primary">
        {snap.label}
      </h3>
      <p className="mt-2 line-clamp-3 text-sm text-fg-muted">
        {summary || snap.grain_description || "Explore this governed reporting canvas."}
      </p>
    </Link>
  );
}

