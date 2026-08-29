"use client";

import type { BuilderVisual } from "./BuilderChart";

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
}: {
  value: VisualChoice;
  onChange: (v: VisualChoice) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {VISUALS.map((v) => {
        const active = v.id === value;
        return (
          <button
            key={v.id}
            type="button"
            onClick={() => onChange(v.id)}
            className="flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition"
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
