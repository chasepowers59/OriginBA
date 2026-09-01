"use client";

/**
 * The Dashboards landing: a LIST of the org's saved boards. Before this existed,
 * /dashboards opened a blank editor and a saved board was only reachable via a
 * browser bookmark — "my dashboard was deleted" energy.
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchDashboards } from "@/lib/api";
import type { SavedDashboard } from "@/lib/types";

export function DashboardListPage() {
  const [boards, setBoards] = useState<SavedDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboards()
      .then((r) => setBoards(r.dashboards))
      .catch(() => setError("Couldn't load your dashboards."));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">
            Dashboards
          </p>
          <h1 className="portal-heading mt-1 text-2xl font-bold">My dashboards</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Pinboards of up to four visuals, saved to the server and shared across your sessions.
          </p>
        </div>
        <Link href="/dashboards/new" className="btn-primary text-sm">
          + New dashboard
        </Link>
      </div>

      {error ? (
        <div className="glass-panel p-8 text-center text-sm text-fg-muted">
          {error}{" "}
          <button type="button" onClick={() => location.reload()} className="text-primary hover:underline dark:text-primary">
            Retry
          </button>
        </div>
      ) : boards === null ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="loading-shimmer h-32 rounded-2xl" />
          ))}
        </div>
      ) : boards.length === 0 ? (
        <div className="glass-panel p-10 text-center">
          <p className="text-sm font-medium text-heading">No dashboards yet</p>
          <p className="mx-auto mt-2 max-w-md text-sm text-fg-muted">
            Build one from a starter template, or pin a report from the Library or Explore.
          </p>
          <Link href="/dashboards/new" className="btn-primary mt-4 inline-block text-sm">
            Create your first dashboard
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {boards.map((b) => (
            <Link
              key={b.id}
              href={`/dashboards/${b.id}`}
              className="glass-panel group block p-5 transition hover:border-edge"
            >
              <p className="font-semibold text-heading group-hover:text-primary dark:group-hover:text-primary">
                {b.title}
              </p>
              <p className="mt-1 text-xs text-fg-muted">
                {b.tiles?.length ?? 0} tile{(b.tiles?.length ?? 0) === 1 ? "" : "s"} · last {b.days} days
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
