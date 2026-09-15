"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { askAssistant, fetchAssistantStatus, fetchIntegrity } from "@/lib/api";
import { WORKSPACE_SQL_KEY, appendTurns, cell, integrityHeadline, integrityLabel, summarise, threadFor, type Turn } from "@/lib/assistant";
import type { AssistantQuery, AssistantResponse, AssistantStatus, IntegrityOverview } from "@/lib/types";

/**
 * Ask a question about this organization's data in plain language. The answer comes from
 * the assistant reading the reporting canvases and running validated, read-only SQL; every
 * query it ran is shown with its rows, and can be opened in the SQL workspace.
 */
export function AssistantPanel({ compact }: { compact?: boolean }) {
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [integrity, setIntegrity] = useState<IntegrityOverview | null>(null);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAssistantStatus().then(setStatus).catch(() => setStatus({ configured: false, model: null }));
    fetchIntegrity().then(setIntegrity).catch(() => setIntegrity(null));
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [turns, busy]);

  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setQuestion("");
    try {
      const response = await askAssistant(q, threadFor(turns));
      setTurns((t) => appendTurns(t, q, response));
    } catch (err) {
      setTurns((t) => [...t, { role: "user", text: q },
        { role: "error", text: err instanceof Error ? err.message : "The assistant could not answer." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={`glass-panel ${compact ? "p-4" : "p-6"}`} aria-label="Ask the assistant">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">Ask the assistant</p>
          <h2 className={`mt-1 font-bold text-heading ${compact ? "text-lg" : "text-xl"}`}>
            A question about your data, in plain language
          </h2>
          <p className="mt-1 text-sm text-fg-muted">
            It reads your reporting canvases, writes and runs read-only SQL, and shows you every query
            it ran. It never sees CISADM tables or another organization&rsquo;s data.
          </p>
          {integrity ? (
            <p className="mt-1 text-xs text-fg-muted" data-testid="integrity-headline">{integrityHeadline(integrity)}</p>
          ) : null}
        </div>
        {turns.length ? (
          <button type="button" className="btn-ghost text-xs" onClick={() => setTurns([])} disabled={busy}>
            New conversation
          </button>
        ) : null}
      </div>

      {status && !status.configured ? (
        <p className="rounded-xl border border-over bg-over-bg px-4 py-3 text-sm text-over">
          The assistant is not configured for this deployment yet (no model key). The governed
          metrics below still answer everyday questions.
        </p>
      ) : null}

      {turns.length ? (
        <div className="mb-4 max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {turns.map((t, i) => (
            <div key={i}>
              {t.role === "user" ? (
                <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-primary/10 px-4 py-2 text-sm text-heading">{t.text}</p>
              ) : t.role === "error" ? (
                <p className="rounded-xl border border-over bg-over-bg px-4 py-2 text-sm text-over">{t.text}</p>
              ) : (
                <Answer response={t.response} />
              )}
            </div>
          ))}
          {busy ? <p className="text-xs text-fg-muted">Working — reading the canvases and running the query…</p> : null}
          <div ref={endRef} />
        </div>
      ) : null}

      <form onSubmit={ask} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={turns.length ? "Ask a follow-up…" : "How much was billed by cycle in the last 90 days?"}
          className="input-modern w-full"
          disabled={busy || (status ? !status.configured : false)}
          aria-label="Your question"
        />
        <button type="submit" className="btn-primary" disabled={busy || !question.trim() || (status ? !status.configured : false)}>
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>
    </section>
  );
}

function Answer({ response }: { response: AssistantResponse }) {
  return (
    <div className="rounded-xl border border-edge tint-panel-br p-4">
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-heading">{response.answer}</p>
      {response.queries.map((q, i) => <QueryResult key={i} q={q} />)}
      <p className="mt-3 text-xs text-fg-muted">{summarise(response)} · {response.model}</p>
    </div>
  );
}

function QueryResult({ q }: { q: AssistantQuery }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(q.sql); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard unavailable */ }
  };
  const handoff = () => {
    try { sessionStorage.setItem(WORKSPACE_SQL_KEY, q.sql); } catch { /* storage unavailable */ }
  };
  const shown = q.rows.slice(0, 25);
  return (
    <div className="mt-3 rounded-lg border border-edge-subtle">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
        <p className="text-xs text-fg-muted">
          {q.purpose ? <span className="text-heading">{q.purpose} · </span> : null}
          {q.row_count.toLocaleString()} row{q.row_count === 1 ? "" : "s"}{q.truncated ? " (capped)" : ""} · {q.ms} ms
        </p>
        <div className="flex gap-2">
          <button type="button" className="btn-ghost text-xs" onClick={() => setOpen((o) => !o)}>{open ? "Hide SQL" : "Show SQL"}</button>
          <button type="button" className="btn-ghost text-xs" onClick={copy}>{copied ? "Copied" : "Copy SQL"}</button>
          <Link href="/database" className="btn-ghost text-xs" onClick={handoff}>Open in SQL workspace</Link>
        </div>
      </div>
      {q.integrity?.length ? (
        <ul className="border-t border-edge-subtle px-3 py-2 text-xs text-fg-muted">
          {q.integrity.map((i) => (
            <li key={i.canvas} className={i.verdict === "differences" ? "text-over" : undefined}>{integrityLabel(i)}</li>
          ))}
        </ul>
      ) : null}
      {open ? <pre className="overflow-x-auto border-t border-edge-subtle px-3 py-2 text-xs text-heading">{q.sql}</pre> : null}
      {shown.length ? (
        <div className="overflow-auto border-t border-edge-subtle">
          <table className="min-w-full text-left text-xs">
            <thead>
              <tr>{q.columns.map((c) => <th key={c} className="px-3 py-2 text-fg-muted">{c}</th>)}</tr>
            </thead>
            <tbody>
              {shown.map((row, i) => (
                <tr key={i} className="border-t border-edge-subtle">
                  {row.map((v, j) => <td key={j} className="px-3 py-1.5 text-heading">{cell(v, q.columns[j])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          {q.rows.length > shown.length ? (
            <p className="px-3 py-2 text-xs text-fg-muted">Showing {shown.length} of {q.rows.length} rows; open in the SQL workspace for all of them.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
