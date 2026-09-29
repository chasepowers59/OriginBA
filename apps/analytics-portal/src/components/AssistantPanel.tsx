"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { askAssistantStream, createSavedView, fetchAssistantSpend, fetchAssistantStatus, fetchIntegrity, runAnalyticsNlq } from "@/lib/api";
import { stepLabel } from "@/lib/sse";
import { exportRowsCsv, formatCurrency, formatNumber } from "@/lib/format";
import { STARTER_QUESTIONS, WORKSPACE_SQL_KEY, appendTurns, cell, integrityHeadline, integrityLabel, resultChart, savedViewFromSpec, spendLabel, summarise, threadFor, tryGovernedFirst, type Turn } from "@/lib/assistant";
import { useAuth } from "@/components/AuthProvider";
import { ORI } from "@/lib/ori";
import { OriMark } from "@/components/OriMark";
import { contextLabel, getPageContext, loadTurns, saveTurns, subscribeAsk, subscribePageContext, takeAsk, type PageContext } from "@/lib/assistantContext";
import { DatabaseResultChart } from "@/components/DatabaseResultChart";
import type { NlqResponse, AssistantQuery, AssistantResponse, AssistantSpend, AssistantStatus, IntegrityOverview } from "@/lib/types";
import { parseAnswer, parseInline, type Inline } from "@/lib/answerMarkdown";

/**
 * Ask a question about this organization's data in plain language. The answer comes from
 * the assistant reading the reporting canvases and running validated, read-only SQL; every
 * query it ran is shown with its rows, and can be opened in the SQL workspace.
 */
export function AssistantPanel({ compact }: { compact?: boolean }) {
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [integrity, setIntegrity] = useState<IntegrityOverview | null>(null);
  const [spend, setSpend] = useState<AssistantSpend | null>(null);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  // What the model is doing right now, one line per tool step, while it works.
  // The question being answered, shown at once rather than after the answer arrives.
  const [pending, setPending] = useState<string | null>(null);
  const [steps, setSteps] = useState<{ label: string; done: boolean; ok: boolean; rows?: number | null }[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const { can } = useAuth();
  // The page the reader is on (a canvas), sent with the question unless they turn it off.
  const page = useSyncExternalStore(subscribePageContext, getPageContext, () => null);
  const [usePage, setUsePage] = useState(true);
  // The conversation follows the reader between pages: loaded after mount (the server
  // render has no session storage), saved on every change.
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    setTurns(loadTurns());
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (loaded) saveTurns(turns);
  }, [turns, loaded]);

  useEffect(() => {
    fetchAssistantStatus().then(setStatus).catch(() => setStatus({ configured: false, model: null }));
    fetchIntegrity().then(setIntegrity).catch(() => setIntegrity(null));
    fetchAssistantSpend().then(setSpend).catch(() => setSpend(null));
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [turns, busy]);

  const send = async (raw: string,
                      { assistantOnly = false, about }: { assistantOnly?: boolean; about?: PageContext | null } = {}) => {
    const q = raw.trim();
    if (!q || busy) return;
    setBusy(true);
    setQuestion("");
    setPending(q);
    setSteps([]);
    const onPage = about !== undefined ? about : page && usePage ? page : null;
    const aboutThePage = Boolean(onPage);
    if (!assistantOnly && tryGovernedFirst(q, aboutThePage)) {
      // A vetted metric answers at no token cost; anything it does not match (a 404) or
      // cannot run falls through to the assistant.
      try {
        const result = await runAnalyticsNlq(q);
        if (result.metric_id && result.table?.rows?.length) {
          setTurns((t) => [...t, { role: "user", text: q }, { role: "governed", question: q, result }]);
          setBusy(false);
          setPending(null);
          return;
        }
      } catch {
        /* no governed metric for this question */
      }
    }
    try {
      const context = onPage
        ? { canvas_id: onPage.canvas_id, period: onPage.period, filters: onPage.filters }
        : null;
      const response = await askAssistantStream(q, threadFor(turns), context, (e) => {
        if (e.type === "step") {
          setSteps((s) => [...s, { label: stepLabel(e.data), done: false, ok: true }]);
        } else if (e.type === "step_done") {
          setSteps((s) => s.map((x, i) => i === s.length - 1
            ? { ...x, done: true, ok: e.data.ok !== false, rows: e.data.rows as number | null } : x));
        }
      });
      setTurns((t) => appendTurns(t, q, response));
      fetchAssistantSpend().then(setSpend).catch(() => undefined);
    } catch (err) {
      setTurns((t) => [...t, { role: "user", text: q },
        { role: "error", text: err instanceof Error ? err.message : ORI.cannotAnswer }]);
    } finally {
      setBusy(false);
      setPending(null);
    }
  };
  const ask = (e: React.FormEvent) => {
    e.preventDefault();
    void send(question);
  };
  // The failed question and its error leave the conversation, and the question is asked again.
  const retry = (index: number) => {
    const failed = turns[index - 1];
    if (!failed || failed.role !== "user") return;
    setTurns((t) => t.slice(0, index - 1));
    void send(failed.text);
  };
  const configured = status ? status.configured : true;
  const sectionRef = useRef<HTMLElement>(null);

  // A question asked from elsewhere on the page ("Explain this number"): taken on mount
  // (the drawer mounts this panel to answer it) and whenever one arrives.
  useEffect(() => {
    if (!loaded) return;
    const takeOne = () => {
      const ask = takeAsk();
      if (!ask) return;
      sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      void send(ask.question, { assistantOnly: true, about: ask.context });
    };
    takeOne();
    return subscribeAsk(takeOne);
  }, [loaded]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section ref={sectionRef} className={`glass-panel ${compact ? "p-4" : "p-6"}`} aria-label={ORI.ask}>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="flex items-center gap-2.5">
            <OriMark size={compact ? "h-8 w-8" : "h-10 w-10"} />
            <div>
              <h2 className={`font-bold text-heading ${compact ? "text-lg" : "text-xl"}`}>{ORI.ask}</h2>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">{ORI.tagline}</p>
            </div>
          </div>
          <p className="mt-2 text-sm text-fg-muted">{ORI.intro}</p>
          {integrity ? (
            <p className="mt-1 text-xs text-fg-muted" data-testid="integrity-headline">{integrityHeadline(integrity)}</p>
          ) : null}
          {spend && can("settings:manage") ? <p className="text-xs text-fg-muted" data-testid="spend-line">{spendLabel(spend)}</p> : null}
        </div>
        {turns.length ? (
          <button type="button" className="btn-ghost text-xs" onClick={() => setTurns([])} disabled={busy}>
            New conversation
          </button>
        ) : null}
      </div>

      {status && !status.configured ? (
        <p className="rounded-xl border border-over bg-over-bg px-4 py-3 text-sm text-over">
          {ORI.notConfigured}
        </p>
      ) : null}

      {turns.length || pending ? (
        <div className="mb-4 max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {turns.map((t, i) => (
            <div key={i}>
              {t.role === "user" ? (
                <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-primary/10 px-4 py-2 text-sm text-heading">{t.text}</p>
              ) : t.role === "error" ? (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-over bg-over-bg px-4 py-2 text-sm text-over">
                  <p>{t.text}</p>
                  {i === turns.length - 1 ? (
                    <button type="button" className="btn-ghost text-xs" onClick={() => retry(i)} disabled={busy}>
                      Try again
                    </button>
                  ) : null}
                </div>
              ) : t.role === "governed" ? (
                <GovernedAnswer
                  result={t.result}
                  onAskAssistant={() => void send(t.question, { assistantOnly: true })}
                  busy={busy}
                />
              ) : (
                <Answer response={t.response} />
              )}
            </div>
          ))}
          {pending ? (
            <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-primary/10 px-4 py-2 text-sm text-heading">{pending}</p>
          ) : null}
          {busy ? (
            <ul className="space-y-1 text-xs text-fg-muted" aria-live="polite">
              {steps.length ? steps.map((s, i) => (
                <li key={i} className={s.done && !s.ok ? "text-over" : undefined}>
                  {s.done ? (s.ok ? "✓" : "✗") : "…"} {s.label}
                  {s.done && s.rows != null ? ` · ${formatNumber(s.rows)} rows` : ""}
                </li>
              )) : <li>{ORI.thinking}</li>}
            </ul>
          ) : null}
          <div ref={endRef} />
        </div>
      ) : null}

      {page ? (
        <label className="mb-3 flex w-fit items-center gap-2 rounded-full bg-chip px-3 py-1 text-xs text-fg-muted">
          <input type="checkbox" checked={usePage} onChange={(e) => setUsePage(e.target.checked)} />
          About this page: <span className="text-heading">{contextLabel(page)}</span>
        </label>
      ) : null}

      {!turns.length && configured ? (
        <div className="mb-3 flex flex-wrap gap-2" aria-label="Example questions">
          {STARTER_QUESTIONS.map((s) => (
            <button key={s} type="button" className="chip text-xs" onClick={() => void send(s)} disabled={busy}>
              {s}
            </button>
          ))}
        </div>
      ) : null}

      <form onSubmit={ask} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={turns.length ? ORI.followUp : ORI.firstQuestion}
          className="input-modern w-full"
          disabled={busy || !configured}
          aria-label="Your question"
        />
        <button type="submit" className="btn-primary" disabled={busy || !question.trim() || !configured}>
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>
    </section>
  );
}

function Inlines({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((p, i) =>
        p.kind === "bold" ? <strong key={i} className="font-semibold">{p.text}</strong>
        : p.kind === "code" ? <code key={i} className="rounded bg-surface-subtle px-1 py-0.5 text-[0.85em]">{p.text}</code>
        : <span key={i}>{p.text}</span>)}
    </>
  );
}

const ALIGN = { left: "text-left", right: "text-right", center: "text-center" } as const;

/** The assistant's light markdown as real elements: paragraphs, bullets, tables. Never raw HTML. */
function AnswerText({ text }: { text: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed text-heading" data-testid="assistant-answer">
      {parseAnswer(text).map((b, i) =>
        b.kind === "p" ? (
          <p key={i}>{b.lines.map((l, j) => <span key={j}>{j ? " " : null}<Inlines parts={l} /></span>)}</p>
        ) : b.kind === "ul" ? (
          <ul key={i} className="list-disc space-y-1 pl-5">{b.items.map((it, j) => <li key={j}><Inlines parts={it} /></li>)}</ul>
        ) : (
          <div key={i} className="overflow-x-auto rounded-lg border border-edge-subtle">
            <table className="w-full text-sm">
              <thead className="bg-surface-subtle text-xs text-fg-muted">
                <tr>{b.header.map((h, j) => <th key={j} className={`px-3 py-1.5 font-semibold ${ALIGN[b.align[j] ?? "left"]}`}>{h}</th>)}</tr>
              </thead>
              <tbody>
                {b.rows.map((r, j) => (
                  <tr key={j} className="border-t border-edge-subtle">
                    {r.map((c, k) => <td key={k} className={`px-3 py-1.5 tabular-nums ${ALIGN[b.align[k] ?? "left"]}`}><Inlines parts={parseInline(c)} /></td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </div>
  );
}

function Answer({ response }: { response: AssistantResponse }) {
  const { can } = useAuth();
  return (
    <div className="rounded-xl border border-edge tint-panel-br p-4">
      <AnswerText text={response.answer} />
      {response.queries.map((q, i) => <QueryResult key={i} q={q} />)}
      <p className="mt-3 text-xs text-fg-muted">{summarise(response, { admin: can("settings:manage") })}</p>
    </div>
  );
}

function QueryResult({ q }: { q: AssistantQuery }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { can } = useAuth();
  const [saved, setSaved] = useState<{ id?: string; error?: string } | null>(null);
  const save = async () => {
    if (!q.view_spec) return;
    try {
      const view = await createSavedView(savedViewFromSpec(q.view_spec, q.purpose));
      setSaved({ id: view.id });
    } catch (err) {
      setSaved({ error: err instanceof Error ? err.message : "Could not save the view." });
    }
  };
  const download = () => exportRowsCsv(
    q.columns,
    q.rows.map((r) => Object.fromEntries(q.columns.map((c, i) => [c, r[i]]))),
    `${(q.purpose || "answer").replace(/[^a-z0-9]+/gi, "_").slice(0, 60)}.csv`,
  );
  const copy = async () => {
    try { await navigator.clipboard.writeText(q.sql); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard unavailable */ }
  };
  const handoff = () => {
    try { sessionStorage.setItem(WORKSPACE_SQL_KEY, q.sql); } catch { /* storage unavailable */ }
  };
  const shown = q.rows.slice(0, 25);
  const chart = resultChart(q);
  return (
    <div className="mt-3 rounded-lg border border-edge-subtle">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
        <p className="text-xs text-fg-muted">
          {q.purpose ? <span className="text-heading">{q.purpose} · </span> : null}
          {formatNumber(q.row_count)} row{q.row_count === 1 ? "" : "s"}{q.truncated ? " (capped)" : ""} · {q.ms} ms
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost text-xs" onClick={() => setOpen((o) => !o)}>{open ? "Hide SQL" : "Show SQL"}</button>
          <button type="button" className="btn-ghost text-xs" onClick={copy}>{copied ? "Copied" : "Copy SQL"}</button>
          <button type="button" className="btn-ghost text-xs" onClick={download}>Download CSV</button>
          {q.view_spec && can("saved_views:write") ? (
            saved?.id ? (
              <Link href={`/build?view=${encodeURIComponent(saved.id)}`} className="btn-ghost text-xs">Saved · open in builder</Link>
            ) : (
              <button type="button" className="btn-ghost text-xs" onClick={save} title="Save as a view you can reopen, pin and schedule">
                Save as view
              </button>
            )
          ) : null}
          <Link href="/database" className="btn-ghost text-xs" onClick={handoff}>Open in SQL workspace</Link>
        </div>
      </div>
      {saved?.error ? <p className="px-3 pb-2 text-xs text-over">{saved.error}</p> : null}
      {q.integrity?.length ? (
        <ul className="border-t border-edge-subtle px-3 py-2 text-xs text-fg-muted">
          {q.integrity.map((i) => (
            <li key={i.canvas} className={i.verdict === "differences" ? "text-over" : undefined}>{integrityLabel(i)}</li>
          ))}
        </ul>
      ) : null}
      {open ? <pre className="overflow-x-auto border-t border-edge-subtle px-3 py-2 text-xs text-heading">{q.sql}</pre> : null}
      {chart ? (
        <div className="border-t border-edge-subtle">
          <DatabaseResultChart
            rows={q.rows.map((r) => Object.fromEntries(q.columns.map((c, i) => [c, r[i]])))}
            suggestion={chart}
          />
        </div>
      ) : null}
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

/** A question the vetted metrics answered: the same definition the dashboards use, no tokens. */
function GovernedAnswer({ result, onAskAssistant, busy }: {
  result: NlqResponse;
  onAskAssistant: () => void;
  busy: boolean;
}) {
  const money = result.format === "currency";
  const rows = result.table?.rows ?? [];
  return (
    <div className="rounded-2xl rounded-bl-sm border border-edge-subtle bg-surface-subtle px-4 py-3 text-sm text-heading">
      <p className="text-xs font-semibold uppercase tracking-widest text-heading-accent">
        {result.metric_label ?? "Governed metric"}
      </p>
      <p className="mt-1">{result.narrative}</p>
      {rows.length ? (
        <table className="mt-3 min-w-full text-left text-xs">
          <thead>
            <tr>
              {(result.table?.columns ?? ["", ""]).map((c) => <th key={c} className="px-2 py-1 text-fg-muted">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 15).map((r) => (
              <tr key={r.label} className="border-t border-edge-subtle">
                <td className="px-2 py-1">{r.label}</td>
                <td className="px-2 py-1 text-right tabular-nums">{money ? formatCurrency(r.value) : formatNumber(r.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-fg-muted">
        <span>Answered from the vetted metric the dashboards use.</span>
        <button type="button" className="btn-ghost text-xs" onClick={onAskAssistant} disabled={busy}>
          {ORI.askInstead}
        </button>
      </div>
    </div>
  );
}
