"use client";

import { useState } from "react";
import { answerPrompts, unanswered, type ShelfFilter } from "@/lib/builderFilters";
import { FilterValuePicker } from "./FilterValuePicker";

/**
 * The values a saved view asks for before it runs (Jaspersoft's input controls): one input
 * per asked-for filter, prefilled with the value it was saved with. A date asks for a
 * range; anything else offers the canvas's own values with free text as the fallback.
 */
export function ReportParameters({ snapshotId, fils, onRun }: {
  snapshotId: string;
  fils: ShelfFilter[];
  onRun: (answered: ShelfFilter[]) => void;
}) {
  const asked = fils.filter((f) => f.prompt);
  const [answers, setAnswers] = useState<Record<string, unknown>>(
    () => Object.fromEntries(asked.map((f) => [f.field, f.value])));
  const [missing, setMissing] = useState<string[]>([]);
  const set = (field: string, value: unknown) => setAnswers((a) => ({ ...a, [field]: value }));

  const run = () => {
    const answered = answerPrompts(fils, answers);
    const blank = unanswered(answered);
    setMissing(blank);
    if (!blank.length) onRun(answered);
  };

  return (
    <section className="glass-panel space-y-3 p-4" aria-label="Report parameters">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-heading-accent">Report parameters</p>
        <p className="text-sm text-fg-muted">This view asks for these values before it runs.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {asked.map((f) => {
          const value = answers[f.field];
          const range = Array.isArray(value) ? (value as string[]) : ["", ""];
          return (
            <div key={f.field} className="text-xs text-fg-muted">
              <p className={`mb-1 font-medium ${missing.includes(f.field) ? "text-over" : ""}`}>
                {f.label}{missing.includes(f.field) ? " (needed)" : ""}
              </p>
              {f.role === "date" ? (
                <div className="flex items-center gap-2">
                  <input type="date" aria-label={`${f.label} from`} className="input-modern"
                         value={range[0] ?? ""} onChange={(e) => set(f.field, [e.target.value, range[1] ?? ""])} />
                  <span>to</span>
                  <input type="date" aria-label={`${f.label} to`} className="input-modern"
                         value={range[1] ?? ""} onChange={(e) => set(f.field, [range[0] ?? "", e.target.value])} />
                </div>
              ) : (
                <FilterValuePicker snapshotId={snapshotId} field={f.field} value={String(value ?? "")}
                                   onChange={(v) => set(f.field, v)} />
              )}
            </div>
          );
        })}
      </div>
      <button type="button" className="btn-primary" onClick={run}>Run report</button>
    </section>
  );
}
