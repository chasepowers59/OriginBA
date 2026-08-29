"use client";

import { useMemo, useState } from "react";
import type { BuilderQuestion } from "@/lib/types";
import { workstreamDisplayName } from "@/lib/businessLabels";

/** "Start from a question": the 78 governed premade reports as a searchable gallery.
 *  Picking one prefills the builder shelves, then the user tweaks by dragging. */
export function QuestionGallery({
  questions,
  onPick,
  onClose,
}: {
  questions: BuilderQuestion[];
  onPick: (q: BuilderQuestion) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");

  const groups = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const match = (x: BuilderQuestion) =>
      !needle ||
      x.title.toLowerCase().includes(needle) ||
      x.description.toLowerCase().includes(needle) ||
      x.snapshot_label.toLowerCase().includes(needle);
    const g = new Map<string, BuilderQuestion[]>();
    for (const item of questions) {
      if (!match(item)) continue;
      const arr = g.get(item.workstream) ?? [];
      arr.push(item);
      g.set(item.workstream, arr);
    }
    return [...g.entries()];
  }, [questions, q]);

  const total = groups.reduce((n, [, arr]) => n + arr.length, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-auto p-4 sm:p-8"
      style={{ background: "color-mix(in srgb, var(--background) 70%, transparent)", backdropFilter: "blur(4px)" }}
      onClick={onClose}
    >
      <div
        className="glass-panel w-full max-w-3xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="portal-heading text-lg font-bold">Start from a question</h2>
            <p className="text-xs" style={{ color: "var(--foreground-subtle)" }}>
              {total} governed business questions · pick one, then refine by dragging
            </p>
          </div>
          <button type="button" onClick={onClose} className="btn-ghost text-sm">Close</button>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search questions… (billing, arrears, payments, meters…)"
          className="input-modern mt-4 w-full text-sm"
          autoFocus
        />
        <div className="mt-4 max-h-[62vh] space-y-5 overflow-auto pr-1">
          {groups.map(([ws, items]) => (
            <div key={ws}>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--foreground-subtle)" }}>
                {workstreamDisplayName(ws)} · {items.length}
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {items.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onPick(item)}
                    className="group rounded-xl border p-3 text-left transition"
                    style={{ borderColor: "var(--border)", background: "var(--surface-subtle)" }}
                  >
                    <p className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{item.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs" style={{ color: "var(--foreground-subtle)" }}>
                      {item.description || item.snapshot_label}
                    </p>
                    <p className="mt-1.5 text-[10px]" style={{ color: "var(--chart-1)" }}>{item.snapshot_label}</p>
                  </button>
                ))}
              </div>
            </div>
          ))}
          {!total ? (
            <p className="py-8 text-center text-sm" style={{ color: "var(--foreground-subtle)" }}>
              No questions match “{q}”.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
