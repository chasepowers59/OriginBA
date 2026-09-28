"use client";

import { useEffect, useState } from "react";
import { fetchScopeOptions } from "@/lib/api";
import { optionsWithCurrent } from "@/lib/builderFilters";

/**
 * Value picker for a filter pill: fetches the field's distinct values (governed, capped
 * at 100) so users pick from what actually exists instead of typing blind. Falls back
 * to a free-text input when the list is unavailable or the value set is capped-out.
 */
export function FilterValuePicker({
  snapshotId,
  field,
  value,
  onChange,
}: {
  snapshotId: string;
  field: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [values, setValues] = useState<string[] | null>(null);
  const [failed, setFailed] = useState(false);
  // Why the list is unavailable, when the API declined rather than errored.
  const [declined, setDeclined] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setValues(null);
    setFailed(false);
    fetchScopeOptions(snapshotId, field)
      .then((r) => {
        if (!active) return;
        // enumerable === false means the canvas is too large to list values from;
        // absent means an older API, which always enumerated.
        setDeclined(r.enumerable === false ? r.reason ?? "Too many rows to list values." : null);
        setValues(r.values ?? []);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [snapshotId, field]);

  // Free text when the list is unavailable — because the fetch failed, because the
  // column has no values, or because the canvas is too large to list from. The filter
  // works identically either way; only the convenience of picking is lost. `title`
  // carries the reason so declining is explained rather than mysterious.
  if (declined || failed || (values && values.length === 0)) {
    return (
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="= value"
        title={declined ?? undefined}
        className="w-24 rounded bg-transparent text-[10px]"
        style={{ color: "var(--chart-4)" }}
      />
    );
  }
  if (values === null) {
    return (
      <span className="text-[10px]" style={{ color: "var(--foreground-subtle)" }}>
        loading…
      </span>
    );
  }
  // The list is capped at 100, so a restored filter's value is often not in it. A
  // select whose value matches no option shows "choose value…" while the filter is
  // still applied — an empty chart with nothing to explain it.
  const options = optionsWithCurrent(values, value) ?? [];
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="max-w-[150px] truncate rounded border-none bg-transparent text-[10px] outline-none"
      style={{ color: "var(--chart-4)" }}
    >
      <option value="">choose value…</option>
      {options.map((v) => (
        <option key={v} value={v}>
          {v}
        </option>
      ))}
    </select>
  );
}
