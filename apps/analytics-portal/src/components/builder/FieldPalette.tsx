"use client";

import { useMemo, useState } from "react";
import type { FieldDef, SnapshotMetadata } from "@/lib/types";
import { FieldPill } from "./FieldPill";

/** The left "Data" pane: every column of the chosen canvas, grouped by role, each a
 *  draggable pill. Fields come from metadata.fields[] (role = dimension|measure|date);
 *  if a canvas predates the fields[] catalog we synthesize from dimensions/measures. */
export function FieldPalette({ meta }: { meta: SnapshotMetadata }) {
  const [q, setQ] = useState("");
  const trusted = useMemo(
    () => new Set(meta.trusted_measures ?? []),
    [meta.trusted_measures],
  );

  const fields: FieldDef[] = useMemo(() => {
    if (meta.fields?.length) return meta.fields;
    const out: FieldDef[] = [];
    for (const d of meta.dimensions ?? []) out.push({ id: d.id, label: d.label, type: "text", role: "dimension" });
    for (const m of meta.measures ?? []) if (m.id !== "*") out.push({ id: m.id, label: m.label, type: "number", role: "measure" });
    for (const d of meta.date_fields ?? []) out.push({ id: d.id, label: d.label, type: "date", role: "date" });
    return out;
  }, [meta]);

  const groups = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const match = (f: FieldDef) => !needle || f.label.toLowerCase().includes(needle) || f.id.toLowerCase().includes(needle);
    const by = (role: string) => fields.filter((f) => f.role === role && match(f));
    return [
      { role: "dimension", label: "Dimensions", items: by("dimension") },
      { role: "measure", label: "Measures", items: by("measure") },
      { role: "date", label: "Dates", items: by("date") },
    ].filter((g) => g.items.length);
  }, [fields, q]);

  return (
    <div className="flex h-full flex-col gap-3">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--foreground-subtle)" }}>
          Data · {meta.label}
        </p>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search columns…"
          className="input-modern mt-2 w-full text-xs"
        />
      </div>
      <div className="flex-1 space-y-4 overflow-auto pr-1">
        {groups.map((g) => (
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
        ))}
        {!groups.length ? (
          <p className="text-xs" style={{ color: "var(--foreground-subtle)" }}>
            No columns match “{q}”.
          </p>
        ) : null}
      </div>
    </div>
  );
}
