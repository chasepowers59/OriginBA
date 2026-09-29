"use client";

import { useEffect, useState } from "react";
import { fetchContentPack, fetchDashboards, fetchSavedViews, importContentPack } from "@/lib/api";
import { packFilename, packSummary, type PackImportResult } from "@/lib/contentPack";
import { FormError } from "@/components/Modal";
import { saveBlob } from "@/lib/format";

/**
 * Carry shared views and dashboards to another organization: export a pack here, switch to
 * the other organization, import it. Every item is checked against that organization's
 * report data first; anything it cannot run is listed and left out.
 */
export function ContentPackPanel() {
  const [folders, setFolders] = useState<string[]>([]);
  const [folder, setFolder] = useState("");
  const [pack, setPack] = useState<unknown>(null);
  const [preview, setPreview] = useState<PackImportResult | null>(null);
  const [done, setDone] = useState<PackImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([fetchSavedViews(), fetchDashboards()])
      .then(([v, d]) => {
        const names = [...v.views, ...d.dashboards].map((i) => i.folder).filter((f): f is string => Boolean(f));
        setFolders([...new Set(names)].sort());
      })
      .catch(() => setFolders([]));
  }, []);

  async function run<T>(work: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await work();
    } catch (err) {
      setError(err instanceof Error ? err.message : "That did not work.");
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    const data = await run(() => fetchContentPack(folder || null));
    if (!data) return;
    const org = String((data as { source_organization?: string }).source_organization ?? "portal");
    saveBlob(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
             packFilename(org, new Date().toISOString().slice(0, 10), folder || null));
  }

  async function onFile(file: File | undefined) {
    setPreview(null);
    setDone(null);
    if (!file) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      setError("That file is not a content pack.");
      return;
    }
    setPack(parsed);
    const result = await run(() => importContentPack(parsed, true));
    if (result) setPreview(result);
  }

  async function onImport() {
    const result = await run(() => importContentPack(pack, false));
    if (result) {
      setDone(result);
      setPreview(null);
    }
  }

  const shown = done ?? preview;
  const toAdd = preview ? preview.views.imported.length + preview.dashboards.imported.length : 0;

  return (
    <div className="space-y-6">
      <section className="glass-panel space-y-3 p-6">
        <h2 className="text-lg font-semibold text-heading">Export a content pack</h2>
        <p className="text-sm text-fg-muted">
          The views and dashboards shared with this organization, as one file. Private items stay here.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-semibold text-heading">
            Folder
            <select value={folder} onChange={(e) => setFolder(e.target.value)}
                    className="mt-1 block rounded-lg border border-edge-subtle bg-surface px-3 py-2 text-sm text-fg">
              <option value="">All shared views and dashboards</option>
              {folders.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>
          <button type="button" onClick={onExport} disabled={busy} className="btn-primary">Download pack</button>
        </div>
      </section>

      <section className="glass-panel space-y-3 p-6">
        <h2 className="text-lg font-semibold text-heading">Import a content pack</h2>
        <p className="text-sm text-fg-muted">
          Adds a pack&apos;s views and dashboards to the organization you are working in. You see what will be added
          before anything is saved; items this organization&apos;s data cannot run are left out, with the reason.
        </p>
        <label className="block text-xs font-semibold text-heading">
          Pack file
          <input type="file" accept="application/json,.json" onChange={(e) => onFile(e.target.files?.[0])}
                 className="mt-1 block text-sm text-fg" />
        </label>
        {error ? <FormError>{error}</FormError> : null}
        {shown ? (
          <div className="space-y-3" aria-live="polite">
            <p className="text-sm font-medium text-heading">{packSummary(shown)}</p>
            {(["views", "dashboards"] as const).map((kind) => (
              <div key={kind} className="grid gap-3 md:grid-cols-2">
                {shown[kind].imported.length ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
                      {kind === "views" ? "Views" : "Dashboards"} {shown.dry_run ? "to add" : "added"}
                    </p>
                    <ul className="mt-1 list-disc pl-5 text-sm text-fg">
                      {shown[kind].imported.map((t) => <li key={t}>{t}</li>)}
                    </ul>
                  </div>
                ) : null}
                {shown[kind].skipped.length ? (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
                      {kind === "views" ? "Views" : "Dashboards"} left out
                    </p>
                    <ul className="mt-1 list-disc pl-5 text-sm text-fg">
                      {shown[kind].skipped.map((s) => <li key={s.title}>{s.title}: {s.reason}</li>)}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))}
            {preview && toAdd ? (
              <button type="button" onClick={onImport} disabled={busy} className="btn-primary">
                {busy ? "Importing…" : `Add ${toAdd} item${toAdd === 1 ? "" : "s"}`}
              </button>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
