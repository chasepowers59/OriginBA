"use client";

import { useEffect, useState } from "react";
import {
  createAnnotation,
  deleteAnnotation,
  fetchAnnotations,
  type Annotation,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { FormError, Modal } from "@/components/Modal";

/**
 * Notes pinned to a report artifact — the "why" next to the number. Anyone in
 * the org can read and add; the author (or an admin) can remove.
 */
export function NotesDialog({
  targetType,
  targetId,
  title,
  onClose,
}: {
  targetType: "saved_view" | "dashboard" | "dashboard_tile";
  targetId: string;
  title: string;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const [notes, setNotes] = useState<Annotation[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = () => {
    fetchAnnotations(targetType, targetId)
      .then((r) => setNotes(r.annotations))
      .catch(() => setNotes([]));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(refresh, [targetType, targetId]);

  async function onAdd() {
    setBusy(true);
    setError(null);
    try {
      await createAnnotation({
        target_type: targetType,
        target_id: targetId,
        text,
      });
      setText("");
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the note.");
    } finally {
      setBusy(false);
    }
  }

  const canRemove = (n: Annotation) =>
    user?.role === "admin" || n.author_email === user?.email;

  return (
    <Modal title="Notes" subtitle={title} onClose={onClose}>
      {notes.length ? (
        <ul className="mt-3 space-y-2">
          {notes.map((n) => (
            <li
              key={n.id}
              className="rounded-lg border border-edge-subtle bg-surface-subtle px-3 py-2"
            >
              <p className="whitespace-pre-wrap text-sm text-fg">{n.text}</p>
              <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-fg-muted">
                <span className="truncate">
                  {n.author_email} · {new Date(n.created_at).toLocaleString()}
                </span>
                {canRemove(n) ? (
                  <button
                    type="button"
                    onClick={async () => {
                      await deleteAnnotation(n.id);
                      refresh();
                    }}
                    className="shrink-0 hover:text-red-600 dark:hover:text-red-300"
                  >
                    Remove
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-fg-muted">
          No notes yet — record what you found so the next reader doesn&apos;t
          re-investigate.
        </p>
      )}

      <div className="mt-4 space-y-2 border-t border-edge-subtle pt-3">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="e.g. Spike traced to the CYCLE3 rebill batch — expected to normalize next period."
          className="w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg"
        />
        {error ? <FormError>{error}</FormError> : null}
        <button
          type="button"
          onClick={onAdd}
          disabled={busy || !text.trim()}
          className="btn-primary w-full"
        >
          {busy ? "Saving…" : "Add note"}
        </button>
      </div>
    </Modal>
  );
}
