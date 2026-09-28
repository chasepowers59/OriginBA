"use client";

import { useState } from "react";
import { describeRules, parseRuleInput, type RowRule } from "@/lib/rowRules";

/**
 * Which rows a user may see: "All rows", or a rule like "Service Type is Water". An
 * administrator sees every row by definition, so the cell says so instead of offering it.
 */
export function RowRulesCell({ user, onSave }: {
  user: { role: string; row_rules?: RowRule[] | null };
  onSave: (rules: RowRule[]) => void;
}) {
  const [editing, setEditing] = useState(false);
  const current = user.row_rules?.[0];
  const [field, setField] = useState(current?.field ?? "");
  const [values, setValues] = useState(current?.values.join(", ") ?? "");

  if (user.role === "admin") return <span className="text-xs portal-text-subtle">Every row</span>;
  if (!editing) {
    return (
      <button type="button" className="btn-ghost text-xs" onClick={() => setEditing(true)}
              title="Limit this person to part of the organization's data">
        {describeRules(user.row_rules)}
      </button>
    );
  }
  return (
    <div className="flex min-w-[14rem] flex-col gap-1">
      <input className="input-modern py-1 text-xs" placeholder="Column, e.g. Service Type" value={field}
             onChange={(e) => setField(e.target.value)} aria-label="Column the rows are limited by" />
      <input className="input-modern py-1 text-xs" placeholder="Values, comma-separated" value={values}
             onChange={(e) => setValues(e.target.value)} aria-label="Values the person may see" />
      <div className="flex gap-1">
        <button type="button" className="btn-primary px-2 py-1 text-xs"
                onClick={() => { onSave(parseRuleInput(field, values)); setEditing(false); }}>Save</button>
        <button type="button" className="btn-ghost px-2 py-1 text-xs"
                onClick={() => { onSave([]); setEditing(false); }}>All rows</button>
        <button type="button" className="btn-ghost px-2 py-1 text-xs" onClick={() => setEditing(false)}>Cancel</button>
      </div>
    </div>
  );
}
