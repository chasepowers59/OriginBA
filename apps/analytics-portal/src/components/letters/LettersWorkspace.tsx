"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { defaultDateRangeLastMonth, fetchLetters, fetchLettersAsOf } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import {
  activeFilterCount,
  applyFilters,
  formatAmount,
  kindFacets,
  letterErrorMessage,
  MAX_WINDOW_DAYS,
  NO_FILTERS,
  sortLetters,
  statusLabel,
  toggle,
  totals,
  validateWindow,
  type Facet,
  type Filters,
  type LetterSummary,
  type Printed,
  type SortDir,
  type SortKey,
} from "@/lib/letters";
import { LetterDetailPane, type PaneTab } from "./LetterDetailPane";
import { LetterRunsPanel } from "./LetterRunsPanel";

type Load = { state: "loading" } | { state: "error"; message: string } | { state: "ready"; letters: LetterSummary[] };
type DateWindow = { from: string; to: string };

const COLUMNS: { key: SortKey; label: string; right?: boolean }[] = [
  { key: "letter_date", label: "Date" },
  { key: "kind_label", label: "Type" },
  { key: "account_id", label: "Account" },
  { key: "printed", label: "Status" },
  { key: "amount", label: "Amount due", right: true },
];

const STATUSES: { value: Printed; label: string }[] = [
  { value: "all", label: "Any status" },
  { value: "not_printed", label: "Not printed" },
  { value: "printed", label: "Printed" },
];

const plural = (n: number, word: string) => `${formatNumber(n)} ${word}${n === 1 ? "" : "s"}`;

/**
 * The letters review page: a date window, the letters dated in it, and the selected letter's PDF
 * beside the data behind it. Customer names and addresses appear only in the detail pane.
 */
export function LettersWorkspace() {
  const [draft, setDraft] = useState<DateWindow>({ from: "", to: "" });
  const [applied, setApplied] = useState<DateWindow | null>(null);
  const [windowError, setWindowError] = useState<string | null>(null);
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "letter_date", dir: "asc" });
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<PaneTab>("letter");

  // The default window is the last full month the data covers: the month before a frozen copy's
  // as-of date, else before today in the viewer's calendar (chosen after hydration, so a server in
  // another timezone cannot pick a different month).
  useEffect(() => {
    let live = true;
    const open = (asOf: string | null) => {
      if (!live) return;
      const [from, to] = defaultDateRangeLastMonth(asOf);
      setDraft({ from, to });
      setApplied({ from, to });
    };
    fetchLettersAsOf().then((r) => open(r.data_as_of)).catch(() => open(null));
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!applied) return;
    let live = true;
    setLoad({ state: "loading" });
    setSelected(null);
    setFilters(NO_FILTERS);
    fetchLetters(applied.from, applied.to)
      .then((r) => live && setLoad({ state: "ready", letters: r.letters }))
      .catch((e) => live && setLoad({ state: "error", message: letterErrorMessage(e) }));
    return () => {
      live = false;
    };
  }, [applied]);

  const show = (e: FormEvent) => {
    e.preventDefault();
    const problem = validateWindow(draft.from, draft.to);
    setWindowError(problem);
    if (!problem) setApplied({ ...draft });
  };

  const letters = load.state === "ready" ? load.letters : [];
  const shown = useMemo(() => sortLetters(applyFilters(letters, filters), sort.key, sort.dir), [letters, filters, sort]);
  const selectedLetter = letters.find((l) => l.letter_id === selected) ?? null;
  const t = totals(shown);
  const active = activeFilterCount(filters);
  const sortBy = (key: SortKey) =>
    setSort((s) => ({ key, dir: s.key === key && s.dir === "asc" ? "desc" : "asc" }));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">Collections</p>
        <h1 className="mt-1 text-2xl font-bold text-heading">Letters</h1>
        <p className="mt-2 max-w-2xl text-sm text-fg-muted">
          The collections letters sent to customers, with the account and process facts behind each one. Choose a
          letter to review its PDF.
        </p>
      </div>

      <form onSubmit={show} className="glass-panel flex flex-wrap items-end gap-3 p-4" aria-label="Letter dates">
        <label className="text-xs font-medium text-fg-muted">
          From
          <input type="date" value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })}
            className="input-modern mt-1 block w-44" />
        </label>
        <label className="text-xs font-medium text-fg-muted">
          To
          <input type="date" value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })}
            className="input-modern mt-1 block w-44" />
        </label>
        <button type="submit" className="btn-primary">Show letters</button>
        {windowError ? (
          <p role="alert" className="pb-2 text-sm text-over">{windowError}</p>
        ) : (
          <p className="pb-2 text-xs text-fg-muted">By letter date, up to {MAX_WINDOW_DAYS} days at a time.</p>
        )}
      </form>

      {load.state === "loading" ? (
        <div role="status" aria-label="Loading letters" className="loading-shimmer h-64 rounded-2xl" />
      ) : load.state === "error" ? (
        <div role="alert" className="glass-panel p-8 text-center text-sm text-heading">{load.message}</div>
      ) : letters.length === 0 ? (
        <div className="glass-panel p-8 text-center text-sm text-fg-muted">No letters in this window.</div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <section className="glass-panel min-w-0 space-y-3 p-4" aria-label="Letters in this window">
            <div className="flex flex-wrap items-center gap-2">
              <input type="search" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                placeholder="Search account, customer or letter" aria-label="Search letters"
                className="input-modern max-w-xs" />
              <div role="group" aria-label="Status" className="flex gap-1">
                {STATUSES.map((s) => (
                  <button key={s.value} type="button" aria-pressed={filters.printed === s.value}
                    onClick={() => setFilters({ ...filters, printed: s.value })}
                    className={`chip ${filters.printed === s.value ? "chip-active" : ""}`}>
                    {s.label}
                  </button>
                ))}
              </div>
              {active > 0 ? (
                <button type="button" onClick={() => setFilters(NO_FILTERS)} className="btn-ghost ml-auto text-xs">
                  Clear {plural(active, "filter")}
                </button>
              ) : null}
            </div>

            <LetterTypeChips facets={kindFacets(letters, filters)} selected={filters.kinds}
              onToggle={(value) => setFilters({ ...filters, kinds: toggle(filters.kinds, value) })} />

            <p className="text-xs text-fg-muted" aria-live="polite">
              {shown.length === letters.length ? plural(t.letters, "letter") : `${formatNumber(t.letters)} of ${plural(letters.length, "letter")}`}
              {" · "}{plural(t.accounts, "account")} · {formatAmount(t.amount)} due · {formatNumber(t.notPrinted)} not printed
            </p>

            <div className="max-h-[65vh] overflow-auto rounded-xl border border-edge-subtle">
              <table className="min-w-full text-left text-sm">
                <thead className="sticky top-0 border-b border-edge-subtle bg-surface-solid">
                  <tr>
                    {COLUMNS.map((c) => (
                      <th key={c.key} scope="col" className={`px-3 py-2 font-medium text-fg-muted ${c.right ? "text-right" : ""}`}
                        aria-sort={sort.key === c.key ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}>
                        <button type="button" onClick={() => sortBy(c.key)} className="inline-flex items-center gap-1 hover:text-heading">
                          {c.label}
                          {sort.key === c.key ? <span aria-hidden>{sort.dir === "asc" ? "▲" : "▼"}</span> : null}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {shown.map((l) => {
                    const on = l.letter_id === selected;
                    return (
                      <tr key={l.letter_id} onClick={() => setSelected(l.letter_id)}
                        className={`cursor-pointer border-b border-edge-subtle transition ${on ? "tint-active" : "hover:bg-chip"}`}>
                        <td className="whitespace-nowrap px-3 py-2 tabular-nums text-heading">{formatDateTime(l.letter_date)}</td>
                        <td className="px-3 py-2">
                          {/* the keyboard's way in; its click bubbles to the row */}
                          <button type="button" aria-current={on ? "true" : undefined}
                            className="text-left font-medium text-heading hover:text-primary">
                            {l.kind_label}
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 tabular-nums text-heading">{l.account_id}</td>
                        <td className="px-3 py-2">
                          <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
                            l.printed ? "bg-ok-bg text-ok" : "bg-warn-bg text-warn"}`}>
                            {statusLabel(l.printed)}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-heading">{formatAmount(l.amount)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {shown.length === 0 ? (
                <p className="p-6 text-center text-sm text-fg-muted">No letters match these filters.</p>
              ) : null}
            </div>
          </section>

          <section className="glass-panel min-w-0 overflow-hidden lg:sticky lg:top-24 lg:self-start" aria-label="Selected letter">
            {selectedLetter ? (
              <LetterDetailPane key={selectedLetter.letter_id} letter={selectedLetter} tab={tab} onTab={setTab} />
            ) : (
              <p className="p-8 text-center text-sm text-fg-muted">Choose a letter to see its PDF and the data behind it.</p>
            )}
          </section>
        </div>
      )}

      <LetterRunsPanel dates={applied} filters={filters} shown={load.state === "ready" ? shown.length : null} />
    </div>
  );
}

export function LetterTypeChips({ facets, selected, onToggle }: {
  facets: Facet[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div role="group" aria-label="Letter type" className="flex flex-wrap gap-1.5">
      {facets.map((f) => {
        const on = selected.includes(f.value);
        return (
          <button key={f.value} type="button" aria-pressed={on} onClick={() => onToggle(f.value)}
            className={`chip ${on ? "chip-active" : ""}`}>
            {f.label} <span className="tabular-nums text-fg-subtle">{formatNumber(f.count)}</span>
          </button>
        );
      })}
    </div>
  );
}
