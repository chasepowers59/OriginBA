"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  countDatabaseSql,
  executeDatabaseSql,
  fetchDatabaseTables,
} from "@/lib/api";
import { suggestChart } from "@/lib/databaseChartUtils";
import {
  categoriesForEngine,
  templatesForEngine,
  tipsForEngine,
  type DatabaseQueryTemplate,
  type WorkspaceEngine,
} from "@/lib/databaseQueryTemplates";
import { exportRowsCsv, formatBoolean, formatCurrency, formatNumber, isIdentifierColumn } from "@/lib/format";
import { prettifyFieldName } from "@/lib/businessLabels";
import { cisadmTableGuide } from "@/lib/cisadmTableGuide";
import { DatabaseResultChart } from "@/components/DatabaseResultChart";
import type { DatabaseSqlResponse, DatabaseTableInfo } from "@/lib/types";

const PAGE_SIZES = [50, 100, 200, 500] as const;
type SidebarTab = "starters" | "tables" | "tips";
type ResultView = "table" | "chart" | "both";

function formatCell(value: unknown, isNumericCol = false, columnId?: string): string {
  if (value === null || value === undefined) return "—";
  // A flag renders as a state, not a number: Number(true) is a finite 1, so without this
  // a boolean column would be mis-detected as numeric and print "1"/"0".
  if (typeof value === "boolean") return formatBoolean(value);
  // an identifier is a STRING that happens to be digits -- never comma-format it
  if (isIdentifierColumn(columnId)) return String(value);
  if (typeof value === "number") return formatNumber(value);
  if (isNumericCol && value !== "" && !Number.isNaN(Number(value))) {
    return formatNumber(Number(value));
  }
  const text = String(value);
  if (text.length > 200) return `${text.slice(0, 200)}…`;
  return text;
}

function parseApiError(err: unknown): string {
  if (!(err instanceof Error)) return "Query failed";
  const raw = err.message;
  try {
    const parsed = JSON.parse(raw) as { detail?: string };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    /* plain text */
  }
  if (raw.includes("503") || raw.toLowerCase().includes("configured")) {
    return "Database unavailable — configure the connection in Settings.";
  }
  return raw || "Query failed";
}

function isNumericColumn(rows: Record<string, unknown>[], col: string): boolean {
  const sample = rows.slice(0, 15);
  if (!sample.length) return false;
  const numeric = sample.filter((r) => {
    const v = r[col];
    return v != null && v !== "" && Number.isFinite(Number(v));
  }).length;
  return numeric >= Math.ceil(sample.length * 0.7);
}

export function DatabaseWorkspace({
  dbConfigured,
  initialTable,
}: {
  dbConfigured: boolean;
  initialTable?: string;
}) {
  const [sql, setSql] = useState("");
  const [activeTemplate, setActiveTemplate] = useState<DatabaseQueryTemplate | null>(null);
  const [pageSize, setPageSize] = useState<number>(50);
  const [loading, setLoading] = useState(false);
  const [fetchingMore, setFetchingMore] = useState(false);
  const [fetchingAll, setFetchingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DatabaseSqlResponse | null>(null);
  const [accumulatedRows, setAccumulatedRows] = useState<Record<string, unknown>[]>([]);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  const [countLoading, setCountLoading] = useState(false);
  const [tables, setTables] = useState<DatabaseTableInfo[]>([]);
  const [tableSearch, setTableSearch] = useState("");
  const [tablesLoading, setTablesLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("starters");
  const [templateCategory, setTemplateCategory] = useState("All");
  const [resultView, setResultView] = useState<ResultView>("table");
  // The warehouse is where the fleet is going; the first /database/tables response
  // corrects this for a legacy Oracle tenant.
  const [engine, setEngine] = useState<WorkspaceEngine>("postgres");
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const queryTemplates = useMemo(() => templatesForEngine(engine), [engine]);
  const templateCategories = useMemo(() => categoriesForEngine(engine), [engine]);
  const workspaceTips = useMemo(() => tipsForEngine(engine), [engine]);

  const columns = result?.columns ?? (accumulatedRows[0] ? Object.keys(accumulatedRows[0]) : []);
  const hasMore = result?.has_more ?? false;
  const fetchedTotal = accumulatedRows.length;
  const lastExecutionMs = result?.execution_ms ?? 0;

  const chartSuggestion = useMemo(
    () => suggestChart(columns, accumulatedRows, activeTemplate),
    [columns, accumulatedRows, activeTemplate],
  );

  const numericColumns = useMemo(
    () => new Set(columns.filter((c) => isNumericColumn(accumulatedRows, c))),
    [columns, accumulatedRows],
  );

  const filteredTemplates = useMemo(
    () =>
      templateCategory === "All"
        ? queryTemplates
        : queryTemplates.filter((t) => t.category === templateCategory),
    [templateCategory, queryTemplates],
  );

  const loadTables = useCallback(async (search: string) => {
    if (!dbConfigured) return;
    setTablesLoading(true);
    try {
      const response = await fetchDatabaseTables("", search, {
        snapshotsOnly: !search.trim(),
        includeStats: Boolean(search.trim()),
      });
      if (response.engine) setEngine(response.engine);
      setTables(response.tables);
    } catch {
      setTables([]);
    } finally {
      setTablesLoading(false);
    }
  }, [dbConfigured]);

  // Learn the engine on mount so the starter queries and tips match the database
  // this org actually queries, before the user ever opens the Tables tab.
  useEffect(() => {
    void loadTables("");
  }, [loadTables]);

  useEffect(() => {
    if (sidebarTab === "tables") void loadTables(tableSearch);
  }, [sidebarTab, tableSearch, loadTables]);

  useEffect(() => {
    if (sidebarTab !== "tables") return;
    const timer = window.setTimeout(() => void loadTables(tableSearch), 300);
    return () => window.clearTimeout(timer);
  }, [tableSearch, loadTables, sidebarTab]);

  const resetResults = () => {
    setResult(null);
    setAccumulatedRows([]);
    setTotalCount(null);
  };

  const applyPage = (response: DatabaseSqlResponse, append: boolean) => {
    setResult(response);
    if (append) {
      setAccumulatedRows((prev) => [...prev, ...response.rows]);
    } else {
      setAccumulatedRows(response.rows);
    }
    if (response.total_count != null) setTotalCount(response.total_count);
  };

  const runQuery = async (opts?: {
    append?: boolean;
    includeCount?: boolean;
    sqlOverride?: string;
  }) => {
    const querySql = opts?.sqlOverride ?? sql;
    const append = opts?.append ?? false;
    const offset = append ? accumulatedRows.length : 0;

    if (append) setFetchingMore(true);
    else {
      setLoading(true);
      if (!append) resetResults();
    }
    setError(null);

    try {
      const response = await executeDatabaseSql({
        sql: querySql,
        offset,
        page_size: pageSize,
        include_total_count: opts?.includeCount ?? false,
      });
      applyPage(response, append);
    } catch (err) {
      setError(parseApiError(err));
      if (!append) resetResults();
    } finally {
      setLoading(false);
      setFetchingMore(false);
    }
  };

  const applyTemplate = (template: DatabaseQueryTemplate, autoRun = true) => {
    setActiveTemplate(template);
    setSql(template.sql);
    setSidebarTab("starters");
    editorRef.current?.focus();
    if (autoRun) void runQuery({ sqlOverride: template.sql });
  };

  const fetchNextPage = () => {
    if (!hasMore || loading || fetchingMore) return;
    void runQuery({ append: true });
  };

  const fetchAllRemaining = async () => {
    if (!hasMore || fetchingAll) return;
    setFetchingAll(true);
    setError(null);
    let offset = accumulatedRows.length;
    let more = true;
    let cols = columns;
    const merged = [...accumulatedRows];

    try {
      while (more && merged.length < 50_000) {
        const response = await executeDatabaseSql({ sql, offset, page_size: pageSize });
        cols = response.columns;
        merged.push(...response.rows);
        offset = merged.length;
        more = response.has_more;
        setAccumulatedRows([...merged]);
        setResult({ ...response, rows: response.rows, fetched_total: merged.length });
      }
      if (merged.length >= 50_000 && more) {
        setError("Stopped at 50,000 rows (safety limit). Narrow your query to fetch more.");
      }
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setFetchingAll(false);
    }

    if (cols.length && merged.length) {
      setResult((prev) =>
        prev ? { ...prev, columns: cols, fetched_total: merged.length, has_more: more } : null,
      );
    }
  };

  const loadTotalCount = async () => {
    setCountLoading(true);
    setError(null);
    try {
      const response = await countDatabaseSql(sql);
      setTotalCount(response.total_count);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setCountLoading(false);
    }
  };

  const insertTable = (tableName: string) => {
    // CISADM browse snippets. ci_pay_tndr carries protected columns, so its snippet
    // lists safe columns explicitly — the fence rejects SELECT * there.
    const isTender = tableName.toLowerCase() === "ci_pay_tndr";
    const cols = isTender ? "pay_event_id, tender_type_cd, tender_amt, tender_ctl_id" : "*";
    const snippet =
      engine === "postgres"
        ? `SELECT ${cols}\nFROM cisadm.${tableName}\nLIMIT ${pageSize}`
        : engine === "oracle_dbt"
          ? `SELECT ${cols}\nFROM ${tableName}\nFETCH FIRST ${pageSize} ROWS ONLY`
          : `SELECT ${cols}\nFROM CISADM.${tableName}\nWHERE ROWNUM <= ${pageSize}`;
    setSql(snippet);
    setActiveTemplate(null);
    editorRef.current?.focus();
  };

  // Deep-link entry from a Canvas Overview: /database?table=<name> seeds a browse query.
  const seededTable = useRef(false);
  useEffect(() => {
    if (initialTable && !seededTable.current) {
      seededTable.current = true;
      insertTable(initialTable);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTable]);

  const statusText = useMemo(() => {
    if (loading) return "Executing…";
    if (fetchingMore) return "Fetching next page…";
    if (fetchingAll) return "Fetching all remaining rows…";
    if (!fetchedTotal) return "Ready";
    const parts = [`${fetchedTotal.toLocaleString()} row${fetchedTotal === 1 ? "" : "s"} fetched`];
    if (lastExecutionMs) parts.push(`${lastExecutionMs.toLocaleString()} ms`);
    if (totalCount != null) parts.push(`of ${totalCount.toLocaleString()} total`);
    else if (hasMore) parts.push("(more available)");
    return parts.join(" · ");
  }, [loading, fetchingMore, fetchingAll, fetchedTotal, lastExecutionMs, totalCount, hasMore]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void runQuery();
    }
  };

  const showChart =
    chartSuggestion && (resultView === "chart" || resultView === "both") && accumulatedRows.length > 0;

  if (!dbConfigured) {
    return (
      <div className="glass-panel p-8 text-center">
        <p className="portal-heading text-lg font-semibold">Database not connected</p>
        <p className="portal-text-muted mt-2 text-sm">
          Configure your organization&apos;s Oracle connection in Settings before using the SQL workspace.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-8.5rem)] min-h-[560px] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface-solid)] shadow-lg">
      <div className="flex flex-wrap items-center gap-2 border-b border-[var(--border)] bg-[var(--surface-subtle)] px-3 py-2">
        <button
          type="button"
          onClick={() => void runQuery()}
          disabled={loading || fetchingAll || !sql.trim()}
          className="btn-primary text-xs"
        >
          {loading ? "Running…" : "Run"}
        </button>
        <button
          type="button"
          onClick={fetchNextPage}
          disabled={!hasMore || loading || fetchingMore || fetchingAll}
          className="btn-ghost text-xs"
        >
          {fetchingMore ? "Fetching…" : `+${pageSize} rows`}
        </button>
        <button
          type="button"
          onClick={() => void fetchAllRemaining()}
          disabled={!hasMore || loading || fetchingAll}
          className="btn-ghost text-xs"
        >
          {fetchingAll ? "Fetching all…" : "Fetch all"}
        </button>
        <button
          type="button"
          onClick={() => void loadTotalCount()}
          disabled={!sql.trim() || countLoading || loading}
          className="btn-ghost text-xs"
        >
          {countLoading ? "Counting…" : "Row count"}
        </button>
        {accumulatedRows.length > 0 ? (
          <button
            type="button"
            onClick={() => exportRowsCsv(columns, accumulatedRows, "database_query_results.csv")}
            className="btn-ghost text-xs"
          >
            Export CSV
          </button>
        ) : null}
        <div className="hidden h-5 w-px bg-[var(--border)] sm:block" />
        <div className="flex rounded-lg border border-[var(--border)] p-0.5">
          {(["table", "both", "chart"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => setResultView(mode)}
              disabled={mode !== "table" && !chartSuggestion}
              className={`rounded-md px-2.5 py-1 text-xs capitalize transition ${
                resultView === mode
                  ? "bg-sky-500/20 text-sky-600 dark:text-sky-300"
                  : "portal-text-muted hover:bg-chip disabled:opacity-40"
              }`}
              title={
                mode !== "table" && !chartSuggestion
                  ? "Run a grouped query to enable charts"
                  : undefined
              }
            >
              {mode === "both" ? "Split" : mode}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <label className="portal-text-muted flex items-center gap-1.5 text-xs">
            Page size
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="input-modern py-1 text-xs"
            >
              {PAGE_SIZES.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
            className="btn-ghost text-xs"
          >
            {sidebarOpen ? "Hide panel" : "Show panel"}
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {sidebarOpen ? (
          <aside className="flex w-72 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface-subtle)]">
            <div className="flex border-b border-[var(--border)]">
              {(
                [
                  ["starters", "Starters"],
                  ["tables", "Tables"],
                  ["tips", "Tips"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSidebarTab(id)}
                  className={`flex-1 px-2 py-2 text-[11px] font-medium ${
                    sidebarTab === id
                      ? "border-b-2 border-sky-400 text-sky-600 dark:text-sky-300"
                      : "portal-text-muted hover:text-fg"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="min-h-0 flex-1 overflow-auto p-2">
              {sidebarTab === "starters" ? (
                <div className="space-y-2">
                  <select
                    value={templateCategory}
                    onChange={(e) => setTemplateCategory(e.target.value)}
                    className="input-modern w-full py-1.5 text-xs"
                  >
                    {templateCategories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                  {filteredTemplates.map((template) => (
                    <button
                      key={template.id}
                      type="button"
                      onClick={() => applyTemplate(template)}
                      className={`w-full rounded-xl border px-3 py-2.5 text-left transition ${
                        activeTemplate?.id === template.id
                          ? "border-sky-400/40 bg-sky-500/10"
                          : "border-[var(--border)] bg-[var(--surface-solid)] hover:border-sky-400/30"
                      }`}
                    >
                      <span className="text-[10px] font-medium uppercase tracking-wide text-sky-600 dark:text-sky-400/80">
                        {template.category}
                      </span>
                      <p className="mt-0.5 text-sm font-medium text-[var(--heading)]">
                        {template.title}
                      </p>
                      <p className="mt-1 text-[11px] leading-relaxed text-fg-muted">
                        {template.description}
                      </p>
                    </button>
                  ))}
                </div>
              ) : null}

              {sidebarTab === "tables" ? (
                <div className="space-y-2">
                  <input
                    type="search"
                    value={tableSearch}
                    onChange={(e) => setTableSearch(e.target.value)}
                    placeholder={engine === "oracle" ? "Search CISADM tables…" : "Search reporting canvases…"}
                    className="input-modern w-full py-1.5 text-xs"
                  />
                  {tablesLoading ? (
                    <p className="px-1 py-2 text-xs text-fg-muted">Loading…</p>
                  ) : (
                    <ul className="space-y-0.5">
                      {tables.map((t) => {
                        const guide = cisadmTableGuide(t.table_name);
                        return (
                          <li key={t.table_name}>
                            <button
                              type="button"
                              onClick={() => insertTable(t.table_name)}
                              className="w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-chip"
                              title={guide ?? undefined}
                            >
                              <span className="flex items-baseline justify-between gap-2">
                                <span className="font-mono text-sky-600 dark:text-sky-300/90">{t.table_name}</span>
                                {t.num_rows != null ? (
                                  <span className="shrink-0 tabular-nums text-fg-subtle">
                                    {Number(t.num_rows).toLocaleString()}
                                  </span>
                                ) : null}
                              </span>
                              {guide ? (
                                <span className="mt-0.5 block text-[11px] leading-snug text-fg-muted">
                                  {guide}
                                </span>
                              ) : null}
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              ) : null}

              {sidebarTab === "tips" ? (
                <ul className="space-y-3 text-xs leading-relaxed text-fg-muted">
                  {workspaceTips.map((tip) => (
                    <li key={tip} className="flex gap-2">
                      <span className="text-sky-600 dark:text-sky-400">•</span>
                      <span>{tip}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </aside>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          {activeTemplate ? (
            <div className="border-b border-sky-400/20 bg-sky-500/5 px-3 py-2 text-xs text-sky-700 dark:text-sky-200/90">
              <span className="font-medium">{activeTemplate.title}</span>
              <span className="mx-2 text-sky-600 dark:text-sky-400/50">·</span>
              {activeTemplate.tip}
            </div>
          ) : null}

          <div className="border-b border-[var(--border)]">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--chip-bg)] px-3 py-1">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
                SQL worksheet
              </span>
              <span className="text-[10px] text-fg-muted">Ctrl+Enter to run · read-only SELECT</span>
            </div>
            <textarea
              ref={editorRef}
              value={sql}
              onChange={(e) => {
                setSql(e.target.value);
                setActiveTemplate(null);
              }}
              onKeyDown={handleKeyDown}
              spellCheck={false}
              placeholder="Pick a starter query from the left panel, or write your own SELECT…"
              rows={8}
              className="w-full resize-y border-0 bg-[var(--surface-input)] px-3 py-2 font-mono text-xs leading-relaxed text-[var(--foreground)] outline-none"
              style={{ minHeight: "120px", maxHeight: "34vh" }}
            />
          </div>

          {error ? (
            <div className="border-b border-red-400/20 bg-red-500/10 px-3 py-2 text-xs text-red-700 dark:text-red-200">
              {error}
            </div>
          ) : null}

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--chip-bg)] px-3 py-1">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-fg-muted">
                Results
              </span>
              <span className="font-mono text-[10px] text-fg-muted">{statusText}</span>
            </div>

            {showChart && chartSuggestion ? (
              <DatabaseResultChart rows={accumulatedRows} suggestion={chartSuggestion} />
            ) : null}

            {(resultView === "table" || resultView === "both") && (
              <div className="min-h-0 flex-1 overflow-auto">
                {!accumulatedRows.length && !loading ? (
                  <div className="px-6 py-10 text-center">
                    <p className="portal-heading text-base font-semibold">Choose a starter query</p>
                    <p className="portal-text-muted mx-auto mt-2 max-w-md text-sm">
                      Pick a business question from the Starters panel — queries run automatically.
                      Results appear in pages of {pageSize} rows.
                    </p>
                    <div className="mt-6 flex flex-wrap justify-center gap-2">
                      {queryTemplates.slice(0, 3).map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => applyTemplate(t)}
                          className="btn-ghost text-xs"
                        >
                          {t.title}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <table className="min-w-full border-collapse text-left text-xs">
                    <thead className="sticky top-0 z-10 bg-slate-950/95 backdrop-blur">
                      <tr>
                        <th className="border-b border-edge-subtle px-2 py-2 text-center font-normal text-fg-muted">
                          #
                        </th>
                        {columns.map((col) => (
                          <th
                            key={col}
                            className={`whitespace-nowrap border-b border-edge-subtle px-3 py-2 font-medium text-fg-muted ${
                              numericColumns.has(col) ? "text-right" : "text-left"
                            }`}
                          >
                            {prettifyFieldName(col)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {accumulatedRows.map((row, idx) => (
                        <tr
                          key={idx}
                          className={`border-t border-edge-subtle hover:bg-white/[0.04] ${
                            idx % 2 === 0 ? "" : "bg-white/[0.02]"
                          }`}
                        >
                          <td className="px-2 py-1.5 text-center font-mono text-[10px] text-fg-muted">
                            {idx + 1}
                          </td>
                          {columns.map((col) => {
                            const isNum = numericColumns.has(col) && !isIdentifierColumn(col);
                            const raw = row[col];
                            const display = isNum && raw != null && CURRENCY_LIKE.test(col)
                              ? formatCurrency(Number(raw))
                              : formatCell(raw, isNum, col);
                            return (
                              <td
                                key={col}
                                className={`max-w-xs truncate whitespace-nowrap px-3 py-1.5 font-mono ${
                                  isNum ? "text-right text-emerald-200/90" : "text-heading"
                                } ${raw == null ? "text-fg-muted" : ""}`}
                                title={raw != null ? String(raw) : undefined}
                              >
                                {display}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-[var(--border)] bg-[var(--surface-subtle)] px-3 py-1.5 font-mono text-[10px] text-fg-muted">
        <span>{statusText}</span>
        <span>
          {chartSuggestion ? "Chart available · " : ""}
          Read-only SELECT · 50-row paging
        </span>
      </div>
    </div>
  );
}

const CURRENCY_LIKE = /(amt|amount|revenue|cur_amt|calc_amt|gl_amt|billed)/i;
