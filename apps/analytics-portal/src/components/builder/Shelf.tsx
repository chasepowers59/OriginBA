"use client";

import type { ReactNode } from "react";
import { useDroppable } from "@dnd-kit/core";

/** A drop target (Columns / Values / Filters). Highlights while a compatible field
 *  is dragged over it; the parent decides what a drop does. */
export function Shelf({
  id,
  label,
  hint,
  accent,
  children,
  empty,
}: {
  id: string;
  label: string;
  hint: string;
  accent: string;
  children: ReactNode;
  empty: boolean;
}) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: accent }}>
          {label}
        </span>
        <span className="text-[10px]" style={{ color: "var(--foreground-subtle)" }}>
          {hint}
        </span>
      </div>
      <div
        ref={setNodeRef}
        className="flex min-h-[46px] flex-wrap items-center gap-2 rounded-xl border border-dashed p-2 transition"
        style={{
          borderColor: isOver ? accent : "var(--border)",
          background: isOver ? `color-mix(in srgb, ${accent} 10%, transparent)` : "var(--surface-subtle)",
        }}
      >
        {empty ? (
          <span className="px-1 text-xs" style={{ color: "var(--foreground-subtle)" }}>
            Drag a field here
          </span>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
