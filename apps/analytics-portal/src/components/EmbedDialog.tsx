"use client";

import { useState } from "react";
import { createEmbedToken } from "@/lib/api";
import { EMBED_LIFETIMES, embedLink, embedSnippet } from "@/lib/embed";
import { FormError, Modal } from "@/components/Modal";
import { formatDateTime } from "@/lib/format";

/**
 * A signed, expiring link to one organization-wide saved view, for another site to frame.
 * The link shows this view only, with its creator's access; the sites allowed to frame it
 * are the portal's EMBED_ALLOWED_ORIGINS.
 */
export function EmbedDialog({ viewId, title, onClose }: { viewId: string; title: string; onClose: () => void }) {
  const [minutes, setMinutes] = useState<number>(EMBED_LIFETIMES[2].minutes);
  const [made, setMade] = useState<{ token: string; expires_at: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const origin = typeof window === "undefined" ? "" : window.location.origin;

  async function onCreate() {
    setBusy(true);
    setError(null);
    try {
      setMade(await createEmbedToken(viewId, minutes));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the embed link.");
    } finally {
      setBusy(false);
    }
  }

  async function copy(label: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
    } catch {
      setCopied(null);
    }
  }

  return (
    <Modal title="Embed" subtitle={title} onClose={onClose}>
      <p className="mt-3 text-xs text-fg-muted">
        Anyone with the link sees this view&apos;s rows, as you see them, until it expires. Only sites your
        administrator allows can show it in a frame.
      </p>
      {made ? (
        <div className="mt-4 space-y-3">
          {[
            { label: "Link", text: embedLink(origin, made.token) },
            { label: "Frame snippet", text: embedSnippet(origin, made.token, title) },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-heading" htmlFor={`embed-${item.label}`}>{item.label}</label>
                <button type="button" onClick={() => copy(item.label, item.text)}
                        className="text-xs text-fg-muted hover:text-primary">
                  {copied === item.label ? "Copied" : "Copy"}
                </button>
              </div>
              <textarea id={`embed-${item.label}`} readOnly value={item.text} rows={item.label === "Link" ? 2 : 3}
                        onFocus={(e) => e.currentTarget.select()}
                        className="mt-1 w-full break-all rounded-lg border border-edge-subtle bg-surface px-3 py-2 font-mono text-xs text-fg" />
            </div>
          ))}
          <p className="text-xs text-fg-muted">Expires {formatDateTime(made.expires_at)}.</p>
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          <label className="block text-xs font-semibold text-heading" htmlFor="embed-lifetime">Link lasts</label>
          <select id="embed-lifetime" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}
                  className="w-full rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg">
            {EMBED_LIFETIMES.map((l) => <option key={l.minutes} value={l.minutes}>{l.label}</option>)}
          </select>
          {error ? <FormError>{error}</FormError> : null}
          <button type="button" onClick={onCreate} disabled={busy} className="btn-primary w-full">
            {busy ? "Creating…" : "Create embed link"}
          </button>
        </div>
      )}
    </Modal>
  );
}
