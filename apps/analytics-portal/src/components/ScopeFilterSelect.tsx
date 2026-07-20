"use client";

import { useEffect, useState } from "react";
import { fetchScopeOptions } from "@/lib/api";
import type { ScopeFilterDef } from "@/lib/types";

type ScopeFilterSelectProps = {
  snapshotId: string;
  filters: ScopeFilterDef[];
  selectedField: string;
  selectedValue: string;
  onFieldChange: (field: string) => void;
  onValueChange: (value: string) => void;
};

export function ScopeFilterSelect({
  snapshotId,
  filters,
  selectedField,
  selectedValue,
  onFieldChange,
  onValueChange,
}: ScopeFilterSelectProps) {
  const [options, setOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const field = selectedField || filters[0]?.field || "";

  useEffect(() => {
    if (!field) {
      setOptions([]);
      return;
    }
    setLoading(true);
    fetchScopeOptions(snapshotId, field)
      .then((res) => setOptions(res.values))
      .catch(() => setOptions([]))
      .finally(() => setLoading(false));
  }, [snapshotId, field]);

  if (!filters.length) return null;

  return (
    <div className="glass-panel space-y-3 p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
        Organization filter
      </p>
      <p className="text-xs text-slate-600">Optional — narrow results by division or business unit</p>
      <label className="block text-xs text-slate-500">
        Filter type
        <select
          value={field}
          onChange={(e) => {
            onFieldChange(e.target.value);
            onValueChange("");
          }}
          className="input-modern mt-1"
        >
          {filters.map((f) => (
            <option key={f.field} value={f.field}>
              {f.label}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-xs text-slate-500">
        Value
        <select
          value={selectedValue}
          onChange={(e) => onValueChange(e.target.value)}
          className="input-modern mt-1"
          disabled={loading}
        >
          <option value="">All organizations</option>
          {options.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
