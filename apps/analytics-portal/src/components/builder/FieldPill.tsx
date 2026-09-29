"use client";

import { useDraggable } from "@dnd-kit/core";
import { fieldGlyph } from "@/lib/builderShelves";
import type { FieldDef } from "@/lib/types";

/**
 * One readable tone, not three series colours. The glyph already says the role
 * unambiguously, and the palette has no third hue that is BOTH legible as 9px text and
 * distinct from the other two: chart-3 was 2.86:1 on the light ground, and darkening it
 * to 4.5 lands 1.2:1 from chart-1 — readable but indistinguishable from the measure
 * badge. Colour that fails contrast and cannot stay distinct is doing no work.
 */
const ROLE_TONE: Record<string, string> = {
  dimension: "var(--foreground-muted)",
  measure: "var(--foreground-muted)",
  date: "var(--foreground-muted)",
};

/** The pill's face: grip, role badge, label, trusted mark. Shared by the pill in the data pane
 *  and the copy that follows the cursor while it is dragged, so the two never drift apart. */
function PillFace({ field, trusted }: { field: FieldDef; trusted?: boolean }) {
  const tone = ROLE_TONE[field.role] ?? "var(--foreground-muted)";
  return (
    <>
      <span aria-hidden className="shrink-0 text-[10px] leading-none" style={{ color: "var(--foreground-subtle)" }}>
        ⠿
      </span>
      <span
        className="grid h-4 w-5 shrink-0 place-items-center rounded text-[9px] font-bold"
        style={{ background: `color-mix(in srgb, ${tone} 20%, transparent)`, color: tone }}
      >
        {fieldGlyph(field)}
      </span>
      <span className="truncate">{field.label}</span>
      {trusted ? (
        <span className="ml-auto shrink-0 text-[9px] font-semibold" style={{ color: "var(--chart-1)" }}>
          ✓
        </span>
      ) : null}
    </>
  );
}

const PILL_CLASS = "group flex w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs";

/** A draggable column from the data pane. `origin` distinguishes a palette source
 *  (drag to add) from a chip already sitting on a shelf. */
export function FieldPill({
  field,
  trusted,
  dragId,
  onActivate,
}: {
  field: FieldDef;
  trusted?: boolean;
  dragId: string;
  /** Click / Enter fallback: adds the field to its role-appropriate shelf, so the
   *  palette works without drag-and-drop (and for keyboard users). */
  onActivate?: (field: FieldDef) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: dragId,
    data: { field, trusted },
  });
  return (
    <button
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={onActivate ? () => onActivate(field) : undefined}
      type="button"
      className={`${PILL_CLASS} transition`}
      style={{
        cursor: "grab",
        // the copy under the cursor is the field now; its place in the list keeps an outline
        opacity: isDragging ? 0.35 : 1,
        borderColor: isDragging ? "var(--chart-2)" : "var(--border-subtle)",
        borderStyle: isDragging ? "dashed" : "solid",
        background: "var(--surface-subtle)",
        color: "var(--foreground)",
      }}
      title={`${field.description || field.label} — click to add, or drag to a shelf`}
    >
      <PillFace field={field} trusted={trusted} />
    </button>
  );
}

/** What follows the cursor while a field is dragged (VisualBuilder's DragOverlay). dnd-kit
 *  moves nothing by itself: without this the pill only faded in place and the drag looked
 *  empty (Chase, 2026-09-29). */
export function FieldDragPreview({ field, trusted }: { field: FieldDef; trusted?: boolean }) {
  return (
    <div
      data-testid="field-drag-preview"
      className={`${PILL_CLASS} w-64 shadow-lg`}
      style={{
        cursor: "grabbing",
        borderColor: "var(--chart-2)",
        background: "var(--surface-solid)",
        color: "var(--foreground)",
      }}
    >
      <PillFace field={field} trusted={trusted} />
    </div>
  );
}
