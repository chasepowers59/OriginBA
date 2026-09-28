"use client";

import { useEffect, useId, useState } from "react";
import { fetchDashboards, fetchSavedViews } from "@/lib/api";
import { folderNames } from "@/lib/folders";

/** A folder to save into, suggesting the folders already in use; blank means no folder. */
export function FolderInput({ kind, value, onChange }: {
  kind: "views" | "dashboards";
  value: string;
  onChange: (v: string) => void;
}) {
  const listId = useId();
  const [suggestions, setSuggestions] = useState<string[]>([]);
  useEffect(() => {
    const load = kind === "views"
      ? fetchSavedViews().then((r) => r.views)
      : fetchDashboards().then((r) => r.dashboards);
    load.then((items) => setSuggestions(folderNames(items))).catch(() => setSuggestions([]));
  }, [kind]);
  return (
    <>
      <input type="text" list={listId} value={value} maxLength={80} placeholder="Folder (optional)"
             aria-label="Folder" onChange={(e) => onChange(e.target.value)}
             className="input-modern w-40 py-1 text-xs" />
      <datalist id={listId}>{suggestions.map((f) => <option key={f} value={f} />)}</datalist>
    </>
  );
}
