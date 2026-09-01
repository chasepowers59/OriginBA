"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { loadSavedViews, removeViewRemote } from "@/lib/savedViews";
import type { SavedFavorite } from "@/lib/favorites";
import { ScheduleDialog } from "@/components/ScheduleDialog";
import { NotesDialog } from "@/components/NotesDialog";

export function FavoritesPanel({ compact }: { compact?: boolean }) {
  const [favorites, setFavorites] = useState<SavedFavorite[]>([]);
  const [loading, setLoading] = useState(true);
  const [scheduling, setScheduling] = useState<SavedFavorite | null>(null);
  const [noting, setNoting] = useState<SavedFavorite | null>(null);

  const refresh = () => {
    loadSavedViews()
      .then(setFavorites)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  if (loading) {
    return compact ? null : (
      <div className="glass-panel-subtle loading-shimmer h-20 rounded-xl" />
    );
  }

  if (!favorites.length) {
    if (compact) return null;
    return (
      <div className="glass-panel-subtle p-4 text-sm text-fg-muted">
        Save reports you run often — they sync to your client workspace for one-click
        access.{" "}
        <Link href="/build" className="text-sky-600 hover:underline dark:text-sky-300">
          Build your first view →
        </Link>
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-2" : "glass-panel p-4"}>
      {!compact ? (
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
          Saved views
        </p>
      ) : null}
      <ul className="space-y-2">
        {favorites.map((fav) => (
          <li
            key={fav.id}
            className="flex items-center gap-2 rounded-xl border border-edge-subtle bg-surface-subtle px-3 py-2"
          >
            <Link
              href={fav.kind === "custom" ? `/build?view=${fav.id}` : `/explore/${fav.snapshotId}?favorite=${fav.id}`}
              className="min-w-0 flex-1 text-sm text-heading hover:text-sky-600 dark:hover:text-sky-300"
            >
              <span className="block truncate font-medium">{fav.title}</span>
              <span className="block truncate text-xs text-fg-muted">{fav.snapshotLabel}</span>
            </Link>
            <button
              type="button"
              onClick={() => setNoting(fav)}
              className="shrink-0 text-xs text-fg-muted hover:text-sky-600 dark:hover:text-sky-300"
              title="Notes on this view"
            >
              Notes
            </button>
            <button
              type="button"
              onClick={() => setScheduling(fav)}
              className="shrink-0 text-xs text-fg-muted hover:text-sky-600 dark:hover:text-sky-300"
              title="Email this view on a schedule"
            >
              Schedule
            </button>
            <button
              type="button"
              onClick={async () => {
                await removeViewRemote(fav.id);
                refresh();
              }}
              className="shrink-0 text-xs text-fg-muted hover:text-red-600 dark:hover:text-red-300"
              title="Remove saved view"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      {scheduling ? (
        <ScheduleDialog
          savedViewId={scheduling.id}
          viewTitle={scheduling.title}
          onClose={() => setScheduling(null)}
        />
      ) : null}
      {noting ? (
        <NotesDialog
          targetType="saved_view"
          targetId={noting.id}
          title={noting.title}
          onClose={() => setNoting(null)}
        />
      ) : null}
    </div>
  );
}
