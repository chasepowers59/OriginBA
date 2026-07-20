"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { loadSavedViews, removeViewRemote } from "@/lib/savedViews";
import type { SavedFavorite } from "@/lib/favorites";

export function FavoritesPanel({ compact }: { compact?: boolean }) {
  const [favorites, setFavorites] = useState<SavedFavorite[]>([]);
  const [loading, setLoading] = useState(true);

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
      <div className="glass-panel-subtle p-4 text-sm text-slate-500">
        Save reports you run often — they sync to your client workspace for one-click access.
      </div>
    );
  }

  return (
    <div className={compact ? "space-y-2" : "glass-panel p-4"}>
      {!compact ? (
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-slate-500">
          Saved views
        </p>
      ) : null}
      <ul className="space-y-2">
        {favorites.map((fav) => (
          <li
            key={fav.id}
            className="flex items-center gap-2 rounded-xl border border-white/5 bg-slate-950/30 px-3 py-2"
          >
            <Link
              href={`/explore/${fav.snapshotId}?favorite=${fav.id}`}
              className="min-w-0 flex-1 text-sm text-slate-200 hover:text-sky-300"
            >
              <span className="block truncate font-medium">{fav.title}</span>
              <span className="block truncate text-xs text-slate-500">{fav.snapshotLabel}</span>
            </Link>
            <button
              type="button"
              onClick={async () => {
                await removeViewRemote(fav.id);
                refresh();
              }}
              className="shrink-0 text-xs text-slate-500 hover:text-red-300"
              title="Remove saved view"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
