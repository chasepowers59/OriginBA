"use client";

import type { BuilderVisual } from "./BuilderChart";
import { visualGuardrail } from "@/lib/visualGuardrails";

export type VisualChoice = BuilderVisual | "table";

const VISUALS: { id: VisualChoice; label: string; glyph: string }[] = [
  { id: "bar", label: "Bar", glyph: "▊▋▍" },
  { id: "stacked-bar", label: "Stacked", glyph: "▣" },
  { id: "horizontal", label: "Horizontal", glyph: "▬" },
  { id: "line", label: "Line", glyph: "╱" },
  { id: "area", label: "Area", glyph: "◢" },
  { id: "stacked-area", label: "Stacked area", glyph: "◭" },
  { id: "pie", label: "Pie", glyph: "◕" },
  { id: "table", label: "Table", glyph: "▤" },
];

export function VisualPicker({
  value,
  onChange,
  categoryCount = 0,
  seriesCount = 0,
}: {
  value: VisualChoice;
  onChange: (v: VisualChoice) => void;
  /** Data shape for guardrails; 0 = unknown (never blocks). */
  categoryCount?: number;
  seriesCount?: number;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {VISUALS.map((v) => {
        const active = v.id === value;
        const blocked = visualGuardrail(v.id, { categoryCount, seriesCount });
        return (
          <button
            key={v.id}
            type="button"
            onClick={() => onChange(v.id)}
            disabled={Boolean(blocked)}
            title={blocked ?? undefined}
            className="flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: active ? "var(--chart-1)" : "var(--border)",
              background: active ? "color-mix(in srgb, var(--chart-1) 14%, transparent)" : "var(--surface-subtle)",
              color: active ? "var(--chart-1)" : "var(--foreground-muted)",
            }}
          >
            <span aria-hidden className="text-[11px] leading-none">{v.glyph}</span>
            {v.label}
          </button>
        );
      })}
    </div>
  );
}
