"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  createDashboard,
  fetchDashboard,
  fetchSnapshots,
  updateDashboard,
} from "@/lib/api";
import type { DashboardTileDef, SavedDashboard, SnapshotSummary } from "@/lib/types";
import { templatesForSnapshots, type DashboardTemplate } from "@/lib/dashboardTemplates";
import { swapTileSlots } from "@/lib/dashboardSlots";
import { CrossFilterProvider, useCrossFilter } from "./CrossFilterContext";
import { DashboardTile } from "./DashboardTile";
import { PresentationToolbar } from "./PresentationToolbar";
import { NotesDialog } from "./NotesDialog";

const SLOTS = [0, 1, 2, 3];

function emptyTile(slot: number, snapshotId = "rpt_financial_txn"): DashboardTileDef {
  // Default to the dbt canvas; callers with the org's catalog loaded pass its first
  // snapshot instead, so a legacy Oracle tenant still gets a valid starting point.
  return {
    id: crypto.randomUUID(),
    slot,
    title: "New tile",
    visual: "chart",
    snapshot_id: snapshotId,
    chart_type: "bar",
  };
}

function CustomDashboardInner({ dashboardId }: { dashboardId?: string }) {
  const [showNotes, setShowNotes] = useState(false);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pinApplied = useRef(false);
  const { filter, clearFilter, toggleFilter } = useCrossFilter();
  const [snapshots, setSnapshots] = useState<SnapshotSummary[]>([]);
  const [board, setBoard] = useState<SavedDashboard | null>(null);
  const [title, setTitle] = useState("My dashboard");
  const [days, setDays] = useState(30);
  const [tiles, setTiles] = useState<DashboardTileDef[]>([]);
  const [editSlot, setEditSlot] = useState<number | null>(null);
  const [exportSections, setExportSections] = useState<
    { name: string; headers: string[]; rows: Record<string, unknown>[] }[]
  >([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [boardLoaded, setBoardLoaded] = useState(false);
  // Drag distance so a click on a tile's Edit/handle isn't read as a drag.
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  useEffect(() => {
    fetchSnapshots().then((i) => setSnapshots(i.snapshots));
  }, []);

  useEffect(() => {
    if (!dashboardId) {
      setTiles([emptyTile(0)]);
      return;
    }
    fetchDashboard(dashboardId).then((d) => {
      setBoard(d);
      setTitle(d.title);
      setDays(d.days);
      setTiles(d.tiles.length ? d.tiles : [emptyTile(0)]);
      setBoardLoaded(true);
    });
  }, [dashboardId]);

  useEffect(() => {
    // Pins APPEND to the first free slot — on a fresh board or an existing one
    // (?pin_* on /dashboards/{id}); a second pin never replaces the first.
    if (pinApplied.current) return;
    if (dashboardId && !boardLoaded) return;
    const snapshotId = searchParams.get("pin_snapshot");
    if (!snapshotId) return;
    pinApplied.current = true;
    const reportId = searchParams.get("pin_report");
    const pinTitle = searchParams.get("pin_title") ?? "Pinned report";
    const chartType = (searchParams.get("pin_chart") as DashboardTileDef["chart_type"]) ?? "bar";
    const visual = (searchParams.get("pin_visual") as DashboardTileDef["visual"]) ?? "chart";
    const measureField = searchParams.get("pin_measure");
    const measureAgg = searchParams.get("pin_agg");
    const pinDims = searchParams.get("pin_dims");
    const pinDays = searchParams.get("pin_days");
    if (pinDays && !dashboardId) setDays(Math.max(1, Number(pinDays) || 30));
    const pinnedTile = (slot: number): DashboardTileDef => ({
      id: crypto.randomUUID(),
      slot,
      title: pinTitle,
      visual,
      snapshot_id: snapshotId,
      report_id: reportId,
      chart_type: chartType,
      measure_field: measureField,
      measure_agg: measureAgg,
      dimensions: pinDims ? pinDims.split(",").filter(Boolean) : undefined,
    });
    setTiles((current) => {
      // ignore the placeholder empty tile a fresh board starts with
      // a fresh board starts with one "New tile" placeholder — strip it there,
      // but never touch a saved board's tiles, whatever they're named
      const real = dashboardId ? current : current.filter((t) => t.title !== "New tile");
      const used = new Set(real.map((t) => t.slot));
      const free = SLOTS.find((sl) => !used.has(sl));
      if (free === undefined) {
        setSaveError("This dashboard is full (4 tiles) — remove one before pinning.");
        return current;
      }
      return [...real, pinnedTile(free)];
    });
    router.replace(dashboardId ? `/dashboards/${dashboardId}` : "/dashboards/new", { scroll: false });
  }, [dashboardId, boardLoaded, router, searchParams]);

  const tileBySlot = useMemo(() => {
    const map = new Map<number, DashboardTileDef>();
    for (const t of tiles) map.set(t.slot, t);
    return map;
  }, [tiles]);

  const applyTemplate = (template: DashboardTemplate) => {
    setTitle(template.title);
    setDays(template.days);
    setTiles(
      template.tiles.map((tile) => ({
        ...tile,
        id: crypto.randomUUID(),
      })),
    );
  };

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      if (board?.id) {
        const updated = await updateDashboard(board.id, { title, days, tiles });
        setBoard(updated);
      } else {
        const created = await createDashboard({ title, days, tiles });
        setBoard(created);
        window.history.replaceState(null, "", `/dashboards/${created.id}`);
      }
    } catch (err) {
      setSaveError(
        err instanceof Error && err.message
          ? err.message
          : "The dashboard could not be saved — check your connection and try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  // Only templates every one of whose tiles this org's catalog can run — a
  // dbt-catalog org never sees the legacy *_RPT_CURR boards, and vice versa.
  const availableTemplates = useMemo(
    () => templatesForSnapshots(new Set(snapshots.map((s) => s.id))),
    [snapshots],
  );

  const updateTile = (slot: number, patch: Partial<DashboardTileDef>) => {
    setTiles((prev) => {
      const existing = prev.find((t) => t.slot === slot);
      if (existing) {
        return prev.map((t) => (t.slot === slot ? { ...t, ...patch } : t));
      }
      return [...prev, { ...emptyTile(slot), ...patch }];
    });
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setTiles((prev) => swapTileSlots(prev, Number(active.id), Number(over.id)));
  };

  const registerExport = useCallback(
    (section: { name: string; headers: string[]; rows: Record<string, unknown>[] }) => {
      setExportSections((prev) => {
        const rest = prev.filter((p) => p.name !== section.name);
        return [...rest, section];
      });
    },
    [],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link href="/dashboards" className="text-xs text-primary hover:text-primary">
            ← My dashboards
          </Link>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="mt-2 block w-full max-w-lg bg-transparent text-2xl font-bold text-heading outline-none border-b border-edge-subtle focus:border-edge"
          />
          <p className="mt-1 text-sm text-fg-muted">
            Drag tiles between slots · up to 4 visuals · saved to server
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {dashboardId ? (
            <button type="button" onClick={() => setShowNotes(true)} className="btn-ghost">
              Notes
            </button>
          ) : null}
          <PresentationToolbar title={title} exportSections={exportSections} />
          <button type="button" onClick={() => void save()} disabled={saving} className="btn-primary">
            {saving ? "Saving…" : "Save dashboard"}
          </button>
        </div>
      </div>

      {saveError ? (
        <p
          role="alert"
          className="rounded-xl border border-over bg-over-bg px-4 py-2 text-sm text-over"
        >
          {saveError}
        </p>
      ) : null}

      {showNotes && dashboardId ? (
        <NotesDialog
          targetType="dashboard"
          targetId={dashboardId}
          title={title}
          onClose={() => setShowNotes(false)}
        />
      ) : null}

      {!dashboardId ? (
        <div className="glass-panel p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
            Starter templates
          </p>
          <p className="mt-1 text-sm text-fg-muted">
            Load a 2×2 workstream dashboard, then drag tiles or edit to customize.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {availableTemplates.map((template) => (
              <button
                key={template.id}
                type="button"
                onClick={() => applyTemplate(template)}
                className="chip text-left"
              >
                <span className="block font-medium text-heading">{template.title}</span>
                <span className="block text-[10px] text-fg-muted">{template.description}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {filter ? (
        <div className="flex items-center justify-between rounded-xl border border-warn bg-warn-bg px-4 py-2 text-sm text-warn">
          <span>
            Cross-filter: <strong>{filter.label ?? filter.field}</strong> = {filter.value}
          </span>
          <button type="button" onClick={clearFilter} className="btn-ghost text-xs">
            Clear
          </button>
        </div>
      ) : (
        <p className="text-xs text-fg-muted">Click a chart value to cross-filter all tiles.</p>
      )}

      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <div id="dashboard-export-root" className="grid gap-4 md:grid-cols-2">
          {SLOTS.map((slot) => (
            <SlotCell key={slot} slot={slot} hasTile={Boolean(tileBySlot.get(slot))}>
              {tileBySlot.get(slot) ? (
                <div className="relative h-full">
                  <div className="absolute right-2 top-2 z-10 flex gap-1">
                    <button
                      type="button"
                      className="chip text-[10px]"
                      onClick={() => setEditSlot(slot)}
                    >
                      Edit
                    </button>
                  </div>
                  <DashboardTile
                    tile={tileBySlot.get(slot)!}
                    days={days}
                    onData={registerExport}
                    onCrossSelect={(field, value) => toggleFilter(field, value, value)}
                  />
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    updateTile(slot, emptyTile(slot));
                    setEditSlot(slot);
                  }}
                  className="flex h-full w-full items-center justify-center text-sm text-fg-muted hover:text-primary"
                >
                  + Add tile
                </button>
              )}
            </SlotCell>
          ))}
        </div>
      </DndContext>

      {editSlot != null ? (
        <TileEditor
          tile={tileBySlot.get(editSlot) ?? emptyTile(editSlot)}
          snapshots={snapshots}
          onClose={() => setEditSlot(null)}
          onSave={(patch) => {
            updateTile(editSlot, patch);
            setEditSlot(null);
          }}
          onRemove={() => {
            setTiles((prev) => prev.filter((t) => t.slot !== editSlot));
            setEditSlot(null);
          }}
        />
      ) : null}
    </div>
  );
}

/**
 * One pinboard slot: a @dnd-kit droppable cell with a drag-handle grip (only when it
 * holds a tile). The grip carries the drag listeners so clicking the chart still
 * cross-filters and the Edit button still opens the editor.
 */
function SlotCell({
  slot,
  hasTile,
  children,
}: {
  slot: number;
  hasTile: boolean;
  children: ReactNode;
}) {
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: slot });
  const { setNodeRef: setDragRef, attributes, listeners, isDragging } = useDraggable({ id: slot });
  return (
    <div
      ref={setDropRef}
      className={`relative min-h-[260px] rounded-2xl border border-dashed p-1 transition ${
 isOver ? "border-edge bg-band" : "border-edge-subtle hover:border-edge"
 } ${isDragging ? "opacity-50" : ""}`}
    >
      {hasTile ? (
        <button
          type="button"
          ref={setDragRef}
          {...attributes}
          {...listeners}
          aria-label="Drag tile to another slot"
          title="Drag to reorder"
          className="absolute left-2 top-2 z-10 cursor-grab rounded px-1.5 py-0.5 text-xs leading-none text-fg-muted hover:text-primary active:cursor-grabbing"
        >
          ⠿
        </button>
      ) : null}
      {children}
    </div>
  );
}

function TileEditor({
  tile,
  snapshots,
  onClose,
  onSave,
  onRemove,
}: {
  tile: DashboardTileDef;
  snapshots: SnapshotSummary[];
  onClose: () => void;
  onSave: (patch: Partial<DashboardTileDef>) => void;
  onRemove: () => void;
}) {
  const [draft, setDraft] = useState(tile);
  return (
    <div className="glass-panel fixed inset-x-4 bottom-4 z-50 mx-auto max-w-xl p-4 shadow-2xl md:inset-x-auto md:right-8 md:top-24 md:bottom-auto">
      <p className="mb-3 font-semibold text-heading">Configure tile</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-xs text-fg-muted sm:col-span-2">
          Title
          <input
            className="input-modern mt-1"
            value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })}
          />
        </label>
        <label className="text-xs text-fg-muted sm:col-span-2">
          Snapshot
          <select
            className="input-modern mt-1"
            value={draft.snapshot_id}
            onChange={(e) => setDraft({ ...draft, snapshot_id: e.target.value })}
          >
            {snapshots.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-fg-muted">
          Visual
          <select
            className="input-modern mt-1"
            value={draft.visual}
            onChange={(e) =>
              setDraft({ ...draft, visual: e.target.value as DashboardTileDef["visual"] })
            }
          >
            <option value="chart">Chart</option>
            <option value="kpi">KPI</option>
            <option value="table">Table</option>
          </select>
        </label>
        <label className="text-xs text-fg-muted">
          Chart type
          <select
            className="input-modern mt-1"
            value={draft.chart_type ?? "bar"}
            onChange={(e) => setDraft({ ...draft, chart_type: e.target.value })}
          >
            <option value="bar">Bar</option>
            <option value="horizontal">Horizontal</option>
            <option value="line">Line</option>
            <option value="pie">Pie</option>
          </select>
        </label>
        <label className="text-xs text-fg-muted sm:col-span-2">
          Time trend (optional)
          <select
            className="input-modern mt-1"
            value={draft.time_grain ?? ""}
            onChange={(e) =>
              setDraft({ ...draft, time_grain: e.target.value || null, chart_type: "line" })
            }
          >
            <option value="">None — group by field</option>
            <option value="month">By month</option>
            <option value="quarter">By quarter</option>
            <option value="year">By year</option>
          </select>
        </label>
      </div>
      <div className="mt-4 flex justify-between gap-2">
        <button type="button" onClick={onRemove} className="text-xs text-over">
          Remove tile
        </button>
        <div className="flex gap-2">
          <button type="button" onClick={onClose} className="btn-ghost">
            Cancel
          </button>
          <button type="button" onClick={() => onSave(draft)} className="btn-primary">
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

export function CustomDashboardPage({ dashboardId }: { dashboardId?: string }) {
  return (
    <CrossFilterProvider>
      <CustomDashboardInner dashboardId={dashboardId} />
    </CrossFilterProvider>
  );
}
