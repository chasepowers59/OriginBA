"use client";

import { useMemo, useState } from "react";
import type { FieldDef, SnapshotMetadata, SnapshotSummary } from "@/lib/types";
import { workstreamDisplayName } from "@/lib/businessLabels";
import { FieldPill } from "./FieldPill";

/**
 * The left "Data" pane, table-first (the way analysts think): a workstream-grouped list
 * of reporting canvases; clicking one expands its columns beneath it as draggable
 * pills, grouped by role. One canvas is active at a time — the builder queries a single
 * canvas, and switching resets the shelves (handled by the caller's loadCanvas).
 */
export function FieldPalette({
  grouped,
  activeId,
  meta,
  onSelect,
}: {
  grouped: [string, SnapshotSummary[]][];
  activeId: string;
  meta: SnapshotMetadata | null;
  onSelect: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();

  const trusted = useMemo(
    () => new Set(meta?.trusted_measures ?? []),
    [meta?.trusted_measures],
  );

  const fields: FieldDef[] = useMemo(() => {
    if (!meta) return [];
    if (meta.fields?.length) return meta.fields;
    const out: FieldDef[] = [];
    for (const d of meta.dimensions ?? []) out.push({ id: d.id, label: d.label, type: "text", role: "dimension" });
    for (const m of meta.measures ?? []) if (m.id !== "*") out.push({ id: m.id, label: m.label, type: "number", role: "measure" });
    for (const d of meta.date_fields ?? []) out.push({ id: d.id, label: d.label, type: "date", role: "date" });
    return out;
  }, [meta]);

  const fieldGroups = useMemo(() => {
    const match = (f: FieldDef) =>
      !needle || f.label.toLowerCase().includes(needle) || f.id.toLowerCase().includes(needle);
    const by = (role: string) => fields.filter((f) => f.role === role && match(f));
    return [
      { role: "dimension", label: "Dimensions", items: by("dimension") },
      { role: "measure", label: "Measures", items: by("measure") },
      { role: "date", label: "Dates", items: by("date") },
    ].filter((g) => g.items.length);
  }, [fields, needle]);

  // When searching, keep a canvas visible if ITS name matches, or if it is active and
  // any of its columns match (so a column search doesn't hide the open table).
  const visibleGroups = useMemo(() => {
    if (!needle) return grouped;
    return grouped
      .map(
        ([ws, snaps]) =>
          [
            ws,
            snaps.filter(
              (s) =>
                s.label.toLowerCase().includes(needle) ||
                (s.id === activeId && fieldGroups.length > 0),
            ),
          ] as [string, SnapshotSummary[]],
      )
      .filter(([, snaps]) => snaps.length);
  }, [grouped, needle, activeId, fieldGroups.length]);

  return (
    <div className="flex h-full flex-col gap-3">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--foreground-subtle)" }}>
          Data
        </p>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search tables & columns…"
          className="input-modern mt-2 w-full text-xs"
        />
      </div>
      <div className="flex-1 space-y-3 overflow-auto pr-1">
        {visibleGroups.map(([ws, snaps]) => (
          <div key={ws}>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--foreground-subtle)" }}>
              {workstreamDisplayName(ws)}
            </p>
            <div className="space-y-0.5">
              {snaps.map((s) => {
                const active = s.id === activeId;
                return (
                  <div key={s.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(s.id)}
                      aria-expanded={active}
                      className={`flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-left text-xs font-medium transition ${
                        active
                          ? "bg-chip text-heading ring-1 ring-edge-subtle"
                          : "text-fg-muted hover:bg-chip hover:text-heading"
                      }`}
                    >
                      <span aria-hidden className={`text-[9px] transition ${active ? "rotate-90" : ""}`}>
                        ▶
                      </span>
                      {s.label}
                    </button>
                    {active ? (
                      <div className="ml-3 mt-1.5 space-y-3 border-l border-edge-subtle pl-2">
                        {!meta ? (
                          <p className="py-1 text-[11px]" style={{ color: "var(--foreground-subtle)" }}>
                            Loading columns…
                          </p>
                        ) : (
                          fieldGroups.map((g) => (
                            <div key={g.role}>
                              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--foreground-subtle)" }}>
                                {g.label} · {g.items.length}
                              </p>
                              <div className="space-y-1.5">
                                {g.items.map((f) => (
                                  <FieldPill key={f.id} field={f} trusted={trusted.has(f.id)} dragId={`palette:${f.id}`} />
                                ))}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
        {!visibleGroups.length ? (
          <p className="text-xs" style={{ color: "var(--foreground-subtle)" }}>
            Nothing matches “{q}”.
          </p>
        ) : null}
      </div>
    </div>
  );
}
