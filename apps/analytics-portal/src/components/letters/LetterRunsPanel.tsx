"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { approveLetterRun, cancelLetterRun, createLetterRun, fetchLetterRuns, releaseLetterRun } from "@/lib/api";
import { formatDate, formatDateTime, formatNumber, saveBlob } from "@/lib/format";
import type { Filters } from "@/lib/letters";
import {
  createRunBlocker,
  runActions,
  runErrorMessage,
  runFilters,
  runStatus,
  type LetterRun,
  type RunPermissions,
} from "@/lib/letterRuns";

function Who({ email, at }: { email: string | null; at: string | null }) {
  if (!email) return <span className="text-fg-subtle">—</span>;
  return (
    <>
      <span className="block text-heading">{email}</span>
      <span className="block text-xs text-fg-muted">{formatDateTime(at)}</span>
    </>
  );
}

/**
 * Runs: the letters shown above frozen into a list, approved by someone other than its creator,
 * then released as one print file. `shown` is the number of letters on screen (null while loading).
 */
export function LetterRunsPanel({ dates, filters, shown }: {
  dates: { from: string; to: string } | null;
  filters: Filters;
  shown: number | null;
}) {
  const { can, user } = useAuth();
  const perms: RunPermissions = {
    generate: can("letters:generate"), approve: can("letters:approve"), release: can("letters:release"),
    admin: user?.role === "admin",
  };
  const [runs, setRuns] = useState<LetterRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(
    () => fetchLetterRuns().then((r) => setRuns(r.runs)).catch((e) => setError(runErrorMessage(e))),
    [],
  );
  useEffect(() => {
    void reload();
  }, [reload]);

  const act = async (key: string, step: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try {
      await step();
    } catch (e) {
      setError(runErrorMessage(e));
    } finally {
      setBusy(null);
    }
  };
  const replace = (run: LetterRun) => setRuns((rs) => (rs ?? []).map((r) => (r.id === run.id ? run : r)));

  const create = () => act("create", async () => {
    const run = await createLetterRun(dates!.from, dates!.to, runFilters(filters));
    setRuns((rs) => [run, ...(rs ?? [])]);
  });
  const release = (run: LetterRun) => act(run.id, async () => {
    saveBlob(await releaseLetterRun(run.id), `letter-run-${run.from}-${run.id.slice(0, 8)}.pdf`);
    await reload();
  });

  const blocker = shown === null ? null : createRunBlocker(filters, shown);

  return (
    <section className="glass-panel space-y-3 p-4" aria-label="Runs">
      <div className="flex flex-wrap items-center gap-3">
        <div className="mr-auto">
          <h2 className="font-semibold text-heading">Runs</h2>
          <p className="text-xs text-fg-muted">
            A run freezes a list of letters. Someone other than its creator approves it, then it is released as one
            print file. A letter that changes in the customer system after the run is created stops the release.
          </p>
        </div>
        {perms.generate && dates && shown !== null ? (
          <div className="flex items-center gap-2">
            {blocker ? <p className="text-xs text-fg-muted">{blocker}</p> : null}
            <button type="button" className="btn-primary" disabled={!!blocker || busy === "create"} onClick={create}>
              Create run from {shown === 1 ? "this letter" : `these ${formatNumber(shown)} letters`}
            </button>
          </div>
        ) : null}
      </div>

      {error ? <p role="alert" className="rounded-lg bg-over-bg px-3 py-2 text-sm text-over">{error}</p> : null}

      {runs === null ? (
        error ? null : <div role="status" aria-label="Loading runs" className="loading-shimmer h-24 rounded-xl" />
      ) : runs.length === 0 ? (
        <p className="p-4 text-center text-sm text-fg-muted">No runs yet.</p>
      ) : (
        <div className="overflow-auto rounded-xl border border-edge-subtle">
          <table className="min-w-full text-left text-sm" aria-label="Letter runs">
            <thead className="border-b border-edge-subtle bg-surface-solid">
              <tr className="text-fg-muted">
                {["Status", "Letters", "Letter dates", "Created", "Approved", ""].map((h) => (
                  <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const s = runStatus(run.status);
                const a = runActions(run, perms);
                const reason = a.approve.reason ? `four-eyes-${run.id}` : undefined;
                return (
                  <tr key={run.id} className="border-b border-edge-subtle align-top last:border-0">
                    <td className="px-3 py-2">
                      <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${s.tone}`}>{s.label}</span>
                      {run.status === "released" && run.pages !== null ? (
                        <span className="mt-1 block text-xs text-fg-muted">
                          {formatNumber(run.pages)} pages, {run.released_by} · {formatDateTime(run.released_at)}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">
                      <span className="tabular-nums text-heading">{formatNumber(run.counts.letters)}</span>
                      <span className="block text-xs text-fg-muted">
                        {run.counts.by_kind.map((k) => `${k.label} ${formatNumber(k.count)}`).join(" · ")}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 tabular-nums text-heading">
                      {formatDate(run.from)} – {formatDate(run.to)}
                    </td>
                    <td className="px-3 py-2"><Who email={run.created_by} at={run.created_at} /></td>
                    <td className="px-3 py-2"><Who email={run.approved_by} at={run.approved_at} /></td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap justify-end gap-1.5">
                        {a.approve.show ? (
                          <button type="button" className="btn-primary px-3 py-1.5 text-xs" aria-describedby={reason}
                            disabled={!a.approve.enabled || busy === run.id}
                            onClick={() => act(run.id, async () => replace(await approveLetterRun(run.id)))}>
                            Approve
                          </button>
                        ) : null}
                        {a.release.show ? (
                          <button type="button" className="btn-primary px-3 py-1.5 text-xs" disabled={busy === run.id}
                            onClick={() => release(run)}>
                            {busy === run.id ? "Preparing…" : a.release.label}
                          </button>
                        ) : null}
                        {a.cancel.show ? (
                          <button type="button" className="btn-ghost px-3 py-1.5 text-xs" disabled={busy === run.id}
                            onClick={() => act(run.id, async () => replace(await cancelLetterRun(run.id)))}>
                            Cancel run
                          </button>
                        ) : null}
                      </div>
                      {a.approve.reason ? (
                        <p id={reason} className="ml-auto mt-1 max-w-[14rem] text-right text-xs text-fg-muted">{a.approve.reason}</p>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
