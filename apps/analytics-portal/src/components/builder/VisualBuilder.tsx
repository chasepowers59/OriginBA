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
  fetchSnapshotMetadata,
  fetchSnapshots,
  runSnapshotQuery,
} from "@/lib/api";
import {
  aggregationLabel,
  allowedAggsForMeasure,
  measureColumnLabel,
  measureDisplaysAsCurrency,
  workstreamDisplayName,
} from "@/lib/businessLabels";
import { formatNumber } from "@/lib/format";
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
import { BuilderChart, type ChartSeries } from "./BuilderChart";
import { QuestionGallery } from "./QuestionGallery";

type ColItem = { field: string; label: string; kind: "dim" | "time"; grain?: string };
type ValItem = { field: string; label: string; agg: string; trusted: boolean };
type FilItem = { field: string; label: string; op: string; value: unknown; role: string };

const GRAINS = ["month", "quarter", "year"];

export function VisualBuilder() {
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
    const dims = cols.filter((c) => c.kind === "dim").map((c) => c.field);
    const timeDims = cols
      .filter((c) => c.kind === "time")
      .map((c) => ({ field: c.field, grain: c.grain ?? "month" }));
    const measures = vals.length
      ? vals.map((v) => ({ field: v.field, agg: v.agg }))
      : [{ field: "*", agg: "count" }];

    const filters = fils.map((f) => ({ field: f.field, op: f.op, value: f.value }));
    // Governance mirror: a canvas with a required date field must carry a between
    // filter on it, or the server rejects the query. Auto-add if the user hasn't.
    const req = meta.required_date_field;
    if (req && !filters.some((f) => f.field === req && f.op === "between")) {
      filters.push({ field: req, op: "between", value: defaultDateRange(90) });
    }
    return {
      dimensions: timeDims.length ? [] : dims,
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
    if (!req) return;
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
        {/* canvas selector + question gallery trigger */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={snapshotId}
            onChange={(e) => loadCanvas(e.target.value)}
            className="input-modern min-w-[260px] text-sm"
          >
            <option value="">Select a reporting canvas…</option>
            {grouped.map(([ws, snaps]) => (
              <optgroup key={ws} label={workstreamDisplayName(ws)}>
                {snaps.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <button type="button" className="btn-ghost text-sm" onClick={() => setGalleryOpen(true)}>
            ✨ Start from a question
          </button>
          {running ? <span className="text-xs" style={{ color: "var(--foreground-subtle)" }}>Running…</span> : null}
        </div>

        {!meta ? (
          <div className="glass-panel px-6 py-16 text-center text-sm" style={{ color: "var(--foreground-subtle)" }}>
            Pick a reporting canvas to start, or open “Start from a question” for a ready-made view.
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
            {/* data pane */}
            <div className="glass-panel h-[560px] p-3">
              <FieldPalette meta={meta} />
            </div>

            {/* shelves + visual */}
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
                          style={{ color: "var(--chart-3)" }}
                        >
                          {GRAINS.map((g) => (
                            <option key={g} value={g}>{g}</option>
                          ))}
                        </select>
                      ) : null}
                      <button type="button" onClick={() => setCols((cc) => cc.filter((x) => x.field !== c.field))} aria-label="remove">×</button>
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
                        <button type="button" onClick={() => setVals((vv) => vv.filter((x) => x.field !== v.field))} aria-label="remove">×</button>
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
                        <input
                          value={String(f.value ?? "")}
                          onChange={(e) => setFils((ff) => ff.map((x) => (x.field === f.field ? { ...x, value: e.target.value } : x)))}
                          placeholder="= value"
                          className="w-20 rounded bg-transparent text-[10px]"
                          style={{ color: "var(--chart-4)" }}
                        />
                      )}
                      <button type="button" onClick={() => setFils((ff) => ff.filter((x) => x.field !== f.field))} aria-label="remove">×</button>
                    </span>
                  ))}
                </Shelf>
              </div>

              <div className="glass-panel space-y-3 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <VisualPicker value={visual} onChange={setVisual} />
                  {result ? (
                    <span className="text-xs" style={{ color: "var(--foreground-subtle)" }}>
                      {result.row_count} rows
                    </span>
                  ) : null}
                </div>
                {error ? (
                  <p className="rounded-lg px-3 py-2 text-sm" style={{ background: "color-mix(in srgb, var(--chart-5) 12%, transparent)", color: "var(--chart-5)" }}>
                    {error}
                  </p>
                ) : visual === "table" ? (
                  <ResultTable result={result} />
                ) : (
                  <BuilderChart rows={result?.rows ?? []} xKey={xKey} xLabel={xLabel} series={series} visual={visual} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {galleryOpen ? (
        <QuestionGallery questions={questions} onPick={applyQuestion} onClose={() => setGalleryOpen(false)} />
      ) : null}
    </DndContext>
  );
}

function ResultTable({ result }: { result: QueryResponse | null }) {
  if (!result?.rows.length) {
    return <p className="py-8 text-center text-sm" style={{ color: "var(--foreground-subtle)" }}>No rows.</p>;
  }
  const cols = result.columns;
  const label = (c: string) => result.column_labels?.[c] ?? c;
  const fmt = (v: unknown) => (typeof v === "number" ? formatNumber(v) : String(v ?? ""));
  return (
    <div className="max-h-[360px] overflow-auto">
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
                  {fmt(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
