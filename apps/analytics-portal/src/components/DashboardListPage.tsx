"use client";

/**
 * The Dashboards landing: a LIST of the org's saved boards. Before this existed,
 * /dashboards opened a blank editor and a saved board was only reachable via a
 * browser bookmark — "my dashboard was deleted" energy.
 */
import Link from "next/link";
import { useEffect, useState } from "react";
import { deleteDashboard, fetchDashboards } from "@/lib/api";
import { tileSummary } from "@/lib/dashboardCard";
import { formatTimeBucket } from "@/lib/timeBucketLabel";
import type { SavedDashboard } from "@/lib/types";

export function DashboardListPage() {
  const [boards, setBoards] = useState<SavedDashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Two-step delete: a board is somebody's saved work, so the first click asks.
  const [confirming, setConfirming] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () =>
    fetchDashboards()
      .then((r) => setBoards(r.dashboards))
      .catch(() => setError("Couldn't load your dashboards."));

  useEffect(() => {
    void load();
  }, []);

  const remove = async (id: string) => {
    setBusy(id);
    try {
      await deleteDashboard(id);
      await load();
    } catch {
      setError("Couldn't delete that dashboard.");
    } finally {
      setBusy(null);
      setConfirming(null);
    }
  };

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
          {boards.map((b) => {
            const contents = tileSummary(b.tiles);
            return (
              <div key={b.id} className="glass-panel group flex flex-col p-5 transition hover:border-edge">
                <Link href={`/dashboards/${b.id}`} className="flex-1">
                  <p className="font-semibold text-heading group-hover:text-primary dark:group-hover:text-primary">
                    {b.title}
                  </p>
                  {/* What is actually on it — the card used to say only "4 tiles", which
                      tells two boards apart from each other not at all. */}
                  {contents ? (
                    <p className="mt-1 line-clamp-2 text-xs text-fg">{contents}</p>
                  ) : null}
                  <p className="mt-2 text-[11px] text-fg-subtle">
                    {b.tiles?.length ?? 0} tile{(b.tiles?.length ?? 0) === 1 ? "" : "s"} · last{" "}
                    {b.days} days
                    {b.updated_at ? ` · updated ${formatTimeBucket(b.updated_at, "day")}` : ""}
                  </p>
                </Link>
                <div className="mt-3 flex justify-end border-t border-edge-subtle pt-2">
                  {confirming === b.id ? (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-fg-muted">Delete this dashboard?</span>
                      <button
                        type="button"
                        onClick={() => void remove(b.id)}
                        disabled={busy === b.id}
                        className="rounded-md bg-over-bg px-2 py-1 font-medium text-over disabled:opacity-60"
                      >
                        {busy === b.id ? "Deleting…" : "Delete"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirming(null)}
                        className="btn-ghost px-2 py-1"
                      >
                        Keep
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirming(b.id)}
                      className="btn-ghost px-2 py-1 text-xs"
                      aria-label={`Delete ${b.title}`}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
