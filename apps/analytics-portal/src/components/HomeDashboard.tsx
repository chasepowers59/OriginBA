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
      <section className="glass-panel relative overflow-hidden p-8 md:p-10">
        <div className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-sky-500/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 left-1/3 h-48 w-48 rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
            {brandLine(brand)}
          </p>
          <h1 className="mt-2 max-w-2xl text-4xl font-bold tracking-tight text-heading md:text-5xl">
            Governed analytics across{" "}
            <span className="bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
              every utility workstream
            </span>
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-fg-muted">
            {brand.tagline}. Explore any reporting table yourself, start from a governed
            report pack for billing close, payments, operations and collections, or ask a
            question in plain language.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/build" className="btn-primary">
              Explore your data
            </Link>
            <Link href="/reports" className="btn-ghost">
              Open report library
            </Link>
          </div>
          <p className="mt-4 text-xs text-fg-muted">
            {/* Real counts only — fabricated placeholders confidently lied when the API was down. */}
            {workstreamCount ? `${workstreamCount} workstreams · ${snapshotCount} reporting tables` : "\u00a0"}
          </p>
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
          <Link href="/reports" className="text-xs text-sky-600 dark:text-sky-400 hover:text-sky-600 dark:hover:text-sky-300">
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
      className="group glass-panel-subtle block p-5 transition hover:border-sky-400/30 hover:bg-surface-subtle hover:shadow-lg hover:shadow-sky-500/5"
    >
      <div className="flex items-start justify-between gap-3">
        {snap.poc_enabled ? (
          <span className="chip chip-active text-[10px]">Analytics ready</span>
        ) : (
          <span className="chip text-[10px]">Browse & SQL</span>
        )}
        <span className="text-fg-muted transition group-hover:text-sky-600 dark:group-hover:text-sky-400">View →</span>
      </div>
      <h3 className="mt-3 text-lg font-semibold text-heading group-hover:text-sky-700 dark:group-hover:text-sky-100">
        {snap.label}
      </h3>
      <p className="mt-2 line-clamp-3 text-sm text-fg-muted">
        {summary || snap.grain_description || "Explore this governed reporting canvas."}
      </p>
    </Link>
  );
}

