"use client";

import { useDraggable } from "@dnd-kit/core";
import type { FieldDef } from "@/lib/types";

const ROLE_GLYPH: Record<string, string> = { dimension: "Abc", measure: "#", date: "📅" };
const ROLE_TONE: Record<string, string> = {
  dimension: "var(--chart-2)",
  measure: "var(--chart-1)",
  date: "var(--chart-3)",
};

/** A draggable column from the data pane. `origin` distinguishes a palette source
 *  (drag to add) from a chip already sitting on a shelf. */
export function FieldPill({
  field,
  trusted,
  dragId,
}: {
  field: FieldDef;
  trusted?: boolean;
  dragId: string;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: dragId,
    data: { field },
  });
  const tone = ROLE_TONE[field.role] ?? "var(--foreground-muted)";
  return (
    <button
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      type="button"
      className="group flex w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition"
      style={{
        cursor: "grab",
        opacity: isDragging ? 0.4 : 1,
        borderColor: "var(--border-subtle)",
        background: "var(--surface-subtle)",
        color: "var(--foreground)",
      }}
      title={field.description || field.label}
    >
      <span
        className="grid h-4 w-5 shrink-0 place-items-center rounded text-[9px] font-bold"
        style={{ background: `color-mix(in srgb, ${tone} 20%, transparent)`, color: tone }}
      >
        {ROLE_GLYPH[field.role] ?? "?"}
      </span>
      <span className="truncate">{field.label}</span>
      {trusted ? (
        <span className="ml-auto shrink-0 text-[9px] font-semibold" style={{ color: "var(--chart-1)" }}>
          ✓
        </span>
      ) : null}
    </button>
  );
}
