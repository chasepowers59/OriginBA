"use client";

/** 'Only me' beside a Save button: unchecked, the item is shared with the organization. */
export function VisibilityToggle({ privateOnly, onChange }: { privateOnly: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-fg-muted" title="Private items are listed only for you">
      <input type="checkbox" checked={privateOnly} onChange={(e) => onChange(e.target.checked)} />
      Only me
    </label>
  );
}
