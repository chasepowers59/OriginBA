"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  defaultDateRange,
  fetchBuilderQuestions,
  fetchScopeOptions,
  fetchSnapshotMetadata,
  fetchSnapshots,
  fetchSavedViews,
  runSnapshotQuery,
  createSavedView,
} from "@/lib/api";
import {
  aggregationLabel,
  allowedAggsForMeasure,
  measureColumnLabel,
  measureDisplaysAsCurrency,
  workstreamDisplayName,
} from "@/lib/businessLabels";
import { activeFilters, optionsWithCurrent, restoreFilters } from "@/lib/builderFilters";
import { formatNumber, formatCellValue } from "@/lib/format";
import type {
  BuilderQuestion,
  FieldDef,
  QueryResponse,
  SnapshotMetadata,
  SnapshotSummary,
} from "@/lib/types";
import { FieldPalette } from "./FieldPalette";
import { Shelf } from "./Shelf";
import { VisualPicker, type VisualChoice } from "./VisualPicker";
import { shelfDimensions } from "@/lib/builderShelves";
import { BuilderChart, type ChartSeries } from "./BuilderChart";
import { QuestionGallery } from "./QuestionGallery";
import { AppliedWindowNote } from "@/components/AppliedWindowNote";

type ColItem = { field: string; label: string; kind: "dim" | "time"; grain?: string };
type ValItem = { field: string; label: string; agg: string; trusted: boolean };
type FilItem = { field: string; label: string; op: string; value: unknown; role: string };

const GRAINS = ["month", "quarter", "year"];

export function VisualBuilder({
  initialCanvas,
  initialReport,
  initialView,
}: {
  initialCanvas?: string;
  initialReport?: string;
  /** A saved custom view's id — reopens it with shelves and visual restored. */
  initialView?: string;
} = {}) {
  const [index, setIndex] = useState<SnapshotSummary[]>([]);
  const [snapshotId, setSnapshotId] = useState("");
  const [meta, setMeta] = useState<SnapshotMetadata | null>(null);
  const [cols, setCols] = useState<ColItem[]>([]);
  const [vals, setVals] = useState<ValItem[]>([]);
  const [fils, setFils] = useState<FilItem[]>([]);
  const [visual, setVisual] = useState<VisualChoice>("bar");
  const [limit] = useState(200);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [questions, setQuestions] = useState<BuilderQuestion[]>([]);
  const [saved, setSaved] = useState<string | null>(null);
  const initialApplied = useRef(false);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  useEffect(() => {
    fetchSnapshots().then((r) => setIndex(r.snapshots)).catch(() => setIndex([]));
    fetchBuilderQuestions().then((r) => setQuestions(r.questions)).catch(() => setQuestions([]));
  }, []);

  const loadCanvas = useCallback(async (id: string, reset = true) => {
    setSnapshotId(id);
    if (reset) { setCols([]); setVals([]); setFils([]); setResult(null); }
    const m = await fetchSnapshotMetadata(id);
    setMeta(m);
    return m;
  }, []);

  const trusted = useMemo(() => new Set(meta?.trusted_measures ?? []), [meta]);
  // Flag columns keyed by their declared type, so a NUMBER(1) 1/0 (Oracle path) or a
  // native boolean (Postgres path) both render as True/False in the result table.
  const booleanCols = useMemo(
    () => new Set((meta?.fields ?? []).filter((f) => f.type === "boolean").map((f) => f.id)),
    [meta],
  );

  const addField = useCallback(
    (shelf: string, field: FieldDef) => {
      if (shelf === "columns") {
        if (field.role === "measure") return; // measures go to Values
        const kind = field.role === "date" ? "time" : "dim";
        setCols((c) =>
          c.some((x) => x.field === field.id)
            ? c
            : [...c, { field: field.id, label: field.label, kind, grain: kind === "time" ? "month" : undefined }],
        );
      } else if (shelf === "values") {
        if (field.role !== "measure") return;
        const aggs = meta ? allowedAggsForMeasure(meta, field.id) : ["count"];
        const isTrusted = trusted.has(field.id);
        const agg = isTrusted ? "sum" : aggs.find((a) => a !== "sum") ?? aggs[0] ?? "count";
        setVals((v) =>
          v.some((x) => x.field === field.id && x.agg === agg)
            ? v
            : [...v, { field: field.id, label: field.label, agg, trusted: isTrusted }],
        );
      } else if (shelf === "filters") {
        const op = field.role === "date" ? "between" : "eq";
        const value = field.role === "date" ? defaultDateRange(90) : "";
        setFils((f) =>
          f.some((x) => x.field === field.id)
            ? f
            : [...f, { field: field.id, label: field.label, op, value, role: field.role }],
        );
      }
    },
    [meta, trusted],
  );

  const onDragEnd = useCallback(
    (e: DragEndEvent) => {
      const overId = e.over?.id;
      const field = e.active.data.current?.field as FieldDef | undefined;
      if (!overId || !field) return;
      addField(String(overId), field);
    },
    [addField],
  );

  // --- query assembly ---------------------------------------------------------
  const buildRequest = useCallback(() => {
    if (!meta) return null;
    // Empty shelves are not a query. The count(*) default below is for "how many",
    // asked by putting a measure on VALUES; with nothing on either shelf it ran anyway
    // and drew an axis with no bars and "1 rows" under it (demo25, 2026-09-04).
    if (!cols.length && !vals.length) return null;
    const { dimensions: dims, timeDimensions: timeDims } = shelfDimensions(cols);
    const measures = vals.length
      ? vals.map((v) => ({ field: v.field, agg: v.agg }))
      : [{ field: "*", agg: "count" }];

    // Shared with saveView, so the view that reopens is the view that ran.
    const filters = activeFilters(fils);
    // No client-side default window: an unfiltered query gets the server's, and the
    // server DISCLOSES it (applied_window), which a silent client-side one never did.
    return {
      // Both, always. A date used to blank the dimension list, which silently
      // dropped every other column the user had put on the shelf.
      dimensions: dims,
      measures,
      filters,
      time_dimensions: timeDims.length ? timeDims : undefined,
      limit,
    };
  }, [meta, cols, vals, fils, limit]);

  // debounced auto-run
  const runTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!meta) return;
    const req = buildRequest();
    if (!req) {
      setResult(null);
      return;
    }
    if (runTimer.current) clearTimeout(runTimer.current);
    runTimer.current = setTimeout(async () => {
      setRunning(true);
      setError(null);
      try {
        const res = await runSnapshotQuery(snapshotId, req);
        setResult(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Query failed");
        setResult(null);
      } finally {
        setRunning(false);
      }
    }, 350);
    return () => {
      if (runTimer.current) clearTimeout(runTimer.current);
    };
  }, [snapshotId, meta, buildRequest]);

  // --- chart wiring -----------------------------------------------------------
  const xKey = useMemo(() => {
    if (cols.some((c) => c.kind === "time")) return "TD0";
    const dim = cols.find((c) => c.kind === "dim");
    return dim?.field ?? "";
  }, [cols]);

  const xLabel = useMemo(() => {
    if (cols.some((c) => c.kind === "time")) {
      const t = cols.find((c) => c.kind === "time");
      return `${t?.label} (${t?.grain})`;
    }
    return cols.find((c) => c.kind === "dim")?.label ?? "";
  }, [cols]);

  const series = useMemo<ChartSeries[]>(() => {
    const src = vals.length ? vals : [{ field: "*", agg: "count", label: "", trusted: false }];
    return src.map((v, i) => ({
      key: `m${i}`,
      label: result?.column_labels?.[`m${i}`] ?? measureColumnLabel(v.field, v.agg, v.label),
      currency: v.field !== "*" && measureDisplaysAsCurrency(v.field, v.agg),
    }));
  }, [vals, result]);

  const applyQuestion = useCallback(
    async (question: BuilderQuestion) => {
      setGalleryOpen(false);
      const m = await loadCanvas(question.snapshot_id, true);
      const nextCols: ColItem[] = question.dimensions.map((d) => {
        const f = m.fields?.find((x) => x.id === d);
        const kind = f?.role === "date" ? "time" : "dim";
        return { field: d, label: f?.label ?? d, kind, grain: kind === "time" ? "month" : undefined };
      });
      const nextVals: ValItem[] = question.measures
        .filter((mm) => mm.field !== "*")
        .map((mm) => {
          const f = m.fields?.find((x) => x.id === mm.field);
          return { field: mm.field, label: f?.label ?? mm.field, agg: mm.agg, trusted: (m.trusted_measures ?? []).includes(mm.field) };
        });
      setCols(nextCols);
      setVals(nextVals);
      setFils(
        (question.filters ?? []).map((f) => {
          const fd = m.fields?.find((x) => x.id === f.field);
          return { field: f.field, label: fd?.label ?? f.field, op: f.op, value: f.value, role: fd?.role ?? "dimension" };
        }),
      );
      const ct = question.chart_type;
      setVisual((ct === "line" ? "line" : ct === "pie" ? "pie" : ct === "horizontal" ? "horizontal" : "bar") as VisualChoice);
    },
    [loadCanvas],
  );

  // Reopen a saved custom view: restore canvas, shelves and visual from the stored
  // definition. Without this, a saved view opened an EMPTY builder (the user's work
  // never came back).
  useEffect(() => {
    if (!initialView || initialApplied.current) return;
    initialApplied.current = true;
    (async () => {
      try {
        const { views } = await fetchSavedViews();
        const v = views.find((x) => x.id === initialView);
        if (!v) return;
        const m = await loadCanvas(v.snapshot_id, true);
        const findField = (id: string) => m.fields?.find((x) => x.id === id);
        setCols(
          (v.dimensions ?? []).map((d) => {
            const f = findField(d);
            const kind = f?.role === "date" ? ("time" as const) : ("dim" as const);
            return { field: d, label: f?.label ?? d, kind, grain: kind === "time" ? "month" : undefined };
          }),
        );
        const ms = v.measures?.length
          ? v.measures
          : v.measure_field && v.measure_field !== "*"
            ? [{ field: v.measure_field, agg: v.measure_agg ?? "sum" }]
            : [];
        setVals(
          ms.map((mm) => ({
            field: mm.field,
            label: findField(mm.field)?.label ?? mm.field,
            agg: mm.agg,
            trusted: (m.trusted_measures ?? []).includes(mm.field),
          })),
        );
        // Restore the scope too. Without this the view reopened over the whole canvas
        // while its title still described the scoped question.
        setFils(restoreFilters(v.filters ?? null, m.fields));
        const ct = v.chart_type;
        setVisual(
          (ct === "line" || ct === "pie" || ct === "horizontal" || ct === "area" ||
           ct === "stacked-bar" || ct === "stacked-area" || ct === "table"
            ? ct
            : "bar") as VisualChoice,
        );
      } catch {
        /* view missing or fetch failed — the builder still opens usable */
      }
    })();
  }, [initialView, loadCanvas]);

  // Deep-link entry from a Canvas Overview: /build?canvas=<id> preselects the canvas;
  // &report=<id> also prefills that governed report. Apply once, after the catalog loads.
  useEffect(() => {
    if (initialApplied.current || !index.length) return;
    if (initialReport && questions.length) {
      // The catalog id is composite (canvas:report); the Library's own report_id also resolves.
      const q = questions.find((x) => x.id === initialReport || x.report_id === initialReport);
      if (q) {
        initialApplied.current = true;
        void applyQuestion(q);
        return;
      }
      // report id unknown in the loaded set -> fall through to the canvas
    }
    if (initialCanvas) {
      initialApplied.current = true;
      void loadCanvas(initialCanvas);
    }
  }, [index, questions, initialCanvas, initialReport, applyQuestion, loadCanvas]);

  const saveView = useCallback(async () => {
    if (!meta) return;
    const measures = vals.length ? vals.map((v) => ({ field: v.field, agg: v.agg })) : [{ field: "*", agg: "count" }];
    const first = measures[0];
    const title = `${cols.map((c) => c.label).join(", ") || meta.label} by ${series[0]?.label ?? "count"}`.slice(0, 80);
    try {
      await createSavedView({
        snapshot_id: snapshotId,
        snapshot_label: meta.label,
        title,
        kind: "custom",
        dimensions: cols.map((c) => c.field),
        measure_field: first.field,
        measure_agg: first.agg,
        measures,
        // The scoping is part of the view. Saving without it meant reopening over the
        // whole canvas: different numbers, and nothing said why.
        filters: activeFilters(fils),
        chart_type: visual,
      });
      setSaved("Saved — find it under Saved views on Home");
      setTimeout(() => setSaved(null), 3500);
    } catch (err) {
      setSaved(`Save failed: ${err instanceof Error && err.message ? err.message : "try again"}`);
      setTimeout(() => setSaved(null), 3500);
    }
  }, [meta, snapshotId, cols, vals, fils, visual, series]);

  const grouped = useMemo(() => {
    const g = new Map<string, SnapshotSummary[]>();
    for (const s of index) {
      const arr = g.get(s.workstream) ?? [];
      arr.push(s);
      g.set(s.workstream, arr);
    }
    return [...g.entries()];
  }, [index]);

  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn-ghost text-sm" onClick={() => setGalleryOpen(true)}>
            ✨ Start from a question
          </button>
          {running ? <span className="text-xs" style={{ color: "var(--foreground-subtle)" }}>Running…</span> : null}
        </div>

        {/* Table-first layout: the data pane (tables -> columns) is always visible —
            picking the table IS the entry point, columns expand beneath it. */}
        <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)]">
          <div className="glass-panel max-h-[320px] overflow-y-auto p-3 lg:sticky lg:top-20 lg:max-h-[calc(100vh-7rem)] lg:self-start">
            <FieldPalette
              grouped={grouped}
              activeId={snapshotId}
              meta={meta}
              onSelect={(id) => void loadCanvas(id)}
              onAddField={(field) =>
                addField(field.role === "measure" ? "values" : "columns", field)
              }
            />
          </div>

          {!meta ? (
            <div className="glass-panel flex items-center justify-center px-6 py-16 text-center text-sm" style={{ color: "var(--foreground-subtle)" }}>
              Pick a table on the left to see its columns, or open “Start from a question”
              for a ready-made view.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="glass-panel grid gap-3 p-3 md:grid-cols-3">
                <Shelf id="columns" label="Columns / Group" hint="dimensions + dates" accent="var(--chart-2)" empty={!cols.length}>
                  {cols.map((c) => (
                    <span key={c.field} className="chip flex items-center gap-1.5">
                      {c.label}
                      {c.kind === "time" ? (
                        <select
                          value={c.grain}
                          onChange={(e) => setCols((cc) => cc.map((x) => (x.field === c.field ? { ...x, grain: e.target.value } : x)))}
                          className="rounded bg-transparent text-[10px]"
                          // The Columns shelf accent, not chart-3: this select lives in
                          // a Columns pill, and chart-3 is a series fill that reads at
                          // 2.86:1 as 10px text on the light ground.
                          style={{ color: "var(--chart-2)" }}
                        >
                          {GRAINS.map((g) => (
                            <option key={g} value={g}>{g}</option>
                          ))}
                        </select>
                      ) : null}
                      <button type="button" onClick={() => setCols((cc) => cc.filter((x) => x.field !== c.field))} aria-label="remove" className="-my-2 -mr-1 rounded p-2 leading-none hover:text-heading">×</button>
                    </span>
                  ))}
                </Shelf>
                <Shelf id="values" label="Values" hint="measures" accent="var(--chart-1)" empty={!vals.length}>
                  {vals.map((v) => {
                    const aggs = allowedAggsForMeasure(meta, v.field);
                    return (
                      <span key={v.field} className="chip flex items-center gap-1.5">
                        <select
                          value={v.agg}
                          onChange={(e) => setVals((vv) => vv.map((x) => (x.field === v.field ? { ...x, agg: e.target.value } : x)))}
                          className="rounded bg-transparent text-[10px] font-semibold"
                          style={{ color: "var(--chart-1)" }}
                        >
                          {aggs.map((a) => (
                            <option key={a} value={a} disabled={a === "sum" && !v.trusted}>
                              {aggregationLabel(a)}
                            </option>
                          ))}
                        </select>
                        {v.label}
                        <button type="button" onClick={() => setVals((vv) => vv.filter((x) => x.field !== v.field))} aria-label="remove" className="-my-2 -mr-1 rounded p-2 leading-none hover:text-heading">×</button>
                      </span>
                    );
                  })}
                </Shelf>
                <Shelf id="filters" label="Filters" hint="scope the data" accent="var(--chart-4)" empty={!fils.length}>
                  {fils.map((f) => (
                    <span key={f.field} className="chip flex items-center gap-1.5">
                      {f.label}
                      {f.role === "date" ? (
                        <span className="text-[10px]" style={{ color: "var(--foreground-subtle)" }}>last 90d</span>
                      ) : (
                        <FilterValuePicker
                          snapshotId={snapshotId}
                          field={f.field}
                          value={String(f.value ?? "")}
                          onChange={(v) => setFils((ff) => ff.map((x) => (x.field === f.field ? { ...x, value: v } : x)))}
                        />
                      )}
                      <button type="button" onClick={() => setFils((ff) => ff.filter((x) => x.field !== f.field))} aria-label="remove" className="-my-2 -mr-1 rounded p-2 leading-none hover:text-heading">×</button>
                    </span>
                  ))}
                </Shelf>
              </div>

              <div className="glass-panel space-y-3 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <VisualPicker
                    value={visual}
                    onChange={setVisual}
                    categoryCount={result?.rows.length ?? 0}
                    seriesCount={series.length}
                  />
                  <div className="flex items-center gap-3">
                    {saved ? (
                      <span
                        role={saved.startsWith("Saved") ? undefined : "alert"}
                        className={`text-xs ${saved.startsWith("Saved") ? "" : "text-over"}`}
                        style={saved.startsWith("Saved") ? { color: "var(--chart-1)" } : undefined}
                      >{saved}</span>
                    ) : null}
                    {result ? (
                      <span className="text-xs" style={{ color: "var(--foreground-subtle)" }}>
                        {result.row_count} {result.row_count === 1 ? "row" : "rows"}
                      </span>
                    ) : null}
                    <AppliedWindowNote result={result} />
                    <button type="button" onClick={saveView} className="btn-ghost text-xs" disabled={!result}>
                      Save view
                    </button>
                  </div>
                </div>
                {error ? (
                  <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "color-mix(in srgb, var(--chart-5) 12%, transparent)", color: "var(--chart-5)" }}>
                    {error}
                  </p>
                ) : visual === "table" ? (
                  <ResultTable result={result} booleanCols={booleanCols} />
                ) : (
                  <BuilderChart
                    rows={result?.rows ?? []}
                    xKey={xKey}
                    xLabel={xLabel}
                    series={series}
                    visual={visual}
                    // xKey is the time dimension whenever the shelf holds one, and a date
                    // axis has to read chronologically rather than ranked by size.
                    sortTimeSeries={cols.some((c) => c.kind === "time")}
                    xGrain={cols.find((c) => c.kind === "time")?.grain ?? null}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {galleryOpen ? (
        <QuestionGallery questions={questions} onPick={applyQuestion} onClose={() => setGalleryOpen(false)} />
      ) : null}
    </DndContext>
  );
}

/**
 * Value picker for a filter pill: fetches the field's distinct values (governed, capped
 * at 100) so users pick from what actually exists instead of typing blind. Falls back
 * to a free-text input when the list is unavailable or the value set is capped-out.
 */
function FilterValuePicker({
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

function ResultTable({ result, booleanCols }: { result: QueryResponse | null; booleanCols?: Set<string> }) {
  if (!result?.rows.length) {
    return <p className="py-8 text-center text-sm" style={{ color: "var(--foreground-subtle)" }}>No rows.</p>;
  }
  const cols = result.columns;
  const label = (c: string) => result.column_labels?.[c] ?? c;
  const fmt = (v: unknown, c: string) => {
    if (booleanCols?.has(c) || typeof v === "boolean") return formatCellValue(v, { isBoolean: true });
    return v == null || v === "" ? "—" : typeof v === "number" ? formatNumber(v) : String(v);
  };
  return (
    <div className="max-h-[min(70vh,900px)] overflow-auto">
      <table className="min-w-full text-left text-xs">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c} className="sticky top-0 px-3 py-2" style={{ background: "var(--surface-solid)", color: "var(--foreground-subtle)" }}>
                {label(c)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.slice(0, 200).map((row, i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--border-subtle)" }}>
              {cols.map((c) => (
                <td key={c} className="px-3 py-1.5 tabular-nums" style={{ color: "var(--foreground)" }}>
                  {fmt(row[c], c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
