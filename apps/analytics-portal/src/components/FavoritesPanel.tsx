"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { loadSavedViews, removeViewRemote } from "@/lib/savedViews";
import type { SavedFavorite } from "@/lib/favorites";
import { ScheduleDialog } from "@/components/ScheduleDialog";
import { NotesDialog } from "@/components/NotesDialog";
import { EmbedDialog } from "@/components/EmbedDialog";
import { useAuth } from "@/components/AuthProvider";
import { ownershipLabel } from "@/lib/ownership";
import { groupByFolder } from "@/lib/folders";
import { moveSavedView } from "@/lib/api";

export function FavoritesPanel({ compact }: { compact?: boolean }) {
  const [favorites, setFavorites] = useState<SavedFavorite[]>([]);
  const [loading, setLoading] = useState(true);
  const [scheduling, setScheduling] = useState<SavedFavorite | null>(null);
  const [noting, setNoting] = useState<SavedFavorite | null>(null);
  const [embedding, setEmbedding] = useState<SavedFavorite | null>(null);
  const { user } = useAuth();

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
        <Link href="/build" className="text-primary underline underline-offset-2 dark:text-primary">
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
      <div className="space-y-4">
      {groupByFolder(favorites).map((group) => (
      <section key={group.folder ?? "__unfiled"} aria-label={group.folder ?? "Not in a folder"}>
      {group.folder || groupByFolder(favorites).length > 1 ? (
        <p className="mb-1.5 text-xs font-semibold text-heading">{group.folder ?? "Not in a folder"}</p>
      ) : null}
      <ul className="space-y-2">
        {group.items.map((fav) => (
          <li
            key={fav.id}
            className="flex items-center gap-2 rounded-xl border border-edge-subtle bg-surface-subtle px-3 py-2"
          >
            <Link
              href={fav.kind === "custom" ? `/build?view=${fav.id}` : `/explore/${fav.snapshotId}?favorite=${fav.id}`}
              className="min-w-0 flex-1 text-sm text-heading hover:text-primary"
            >
              <span className="block truncate font-medium">{fav.title}</span>
              <span className="block truncate text-xs text-fg-muted">
                {fav.snapshotLabel}
                {ownershipLabel(fav, user?.email) ? ` · ${ownershipLabel(fav, user?.email)}` : ""}
              </span>
            </Link>
            <button
              type="button"
              onClick={() => setNoting(fav)}
              className="shrink-0 text-xs text-fg-muted hover:text-primary"
              title="Notes on this view"
            >
              Notes
            </button>
            <button
              type="button"
              onClick={() => setScheduling(fav)}
              className="shrink-0 text-xs text-fg-muted hover:text-primary"
              title="Email this view on a schedule"
            >
              Schedule
            </button>
            {fav.canEdit !== false && fav.visibility !== "private" ? (
              <button
                type="button"
                onClick={() => setEmbedding(fav)}
                className="shrink-0 text-xs text-fg-muted hover:text-primary"
                title="Show this view in another site"
              >
                Embed
              </button>
            ) : null}
            {fav.canEdit !== false ? (
              <button
                type="button"
                onClick={async () => {
                  const next = window.prompt("Move to folder (leave empty for no folder)", fav.folder ?? "");
                  if (next === null) return;
                  await moveSavedView(fav.id, next.trim());
                  refresh();
                }}
                className="shrink-0 text-xs text-fg-muted hover:text-primary"
                title="Move to another folder"
              >
                Move
              </button>
            ) : null}
            {fav.canEdit !== false ? (
              <button
                type="button"
                onClick={async () => {
                  await removeViewRemote(fav.id);
                  refresh();
                }}
                className="shrink-0 text-xs text-fg-muted hover:text-over dark:hover:text-over"
                title="Remove saved view"
              >
                Remove
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      </section>
      ))}
      </div>
      {scheduling ? (
        <ScheduleDialog
          savedViewId={scheduling.id}
          viewTitle={scheduling.title}
          onClose={() => setScheduling(null)}
        />
      ) : null}
      {embedding ? (
        <EmbedDialog viewId={embedding.id} title={embedding.title} onClose={() => setEmbedding(null)} />
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
