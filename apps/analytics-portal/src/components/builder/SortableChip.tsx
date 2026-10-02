"use client";

import type { ReactNode } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

/** A field sitting on a shelf. Its grip drags it to a new place on the same shelf (Chase,
 *  2026-10-01: fields on a shelf could not be rearranged); the grip is the only handle, so
 *  the chip's own selects and buttons keep working. Keyboard: focus the grip, Space, arrows. */
export function SortableChip({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  const { setNodeRef, attributes, listeners, transform, transition, isDragging } = useSortable({ id });
  return (
    <span
      ref={setNodeRef}
      data-testid="shelf-chip"
      className="chip flex items-center gap-1.5"
      style={{ transform: CSS.Translate.toString(transform), transition, opacity: isDragging ? 0.6 : 1, zIndex: isDragging ? 1 : undefined }}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        aria-label={`Move ${label}`}
        title="Drag to reorder"
        className="-my-1 -ml-1 cursor-grab touch-none rounded px-0.5 text-[10px] leading-none active:cursor-grabbing"
        style={{ color: "var(--foreground-subtle)" }}
      >
        ⠿
      </button>
      {children}
    </span>
  );
}
