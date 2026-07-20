import type { SavedFavorite } from "./favorites";
import type { SavedView } from "./types";
import {
  createSavedView,
  deleteSavedView,
  fetchSavedViews,
  importSavedViews,
} from "./api";

const LEGACY_STORAGE_KEY = "originba_utility_insights_favorites";
const MIGRATED_KEY = "originba_saved_views_migrated";

export function savedViewToFavorite(view: SavedView): SavedFavorite {
  return {
    id: view.id,
    snapshotId: view.snapshot_id,
    snapshotLabel: view.snapshot_label,
    title: view.title,
    kind: view.kind,
    reportId: view.report_id ?? undefined,
    dimensions: view.dimensions ?? undefined,
    measureField: view.measure_field ?? undefined,
    measureAgg: view.measure_agg ?? undefined,
    chartType: (view.chart_type as SavedFavorite["chartType"]) ?? undefined,
    datePreset: view.date_preset ?? undefined,
    dateStart: view.date_start ?? undefined,
    dateEnd: view.date_end ?? undefined,
    scopeField: view.scope_field ?? undefined,
    scopeValue: view.scope_value ?? undefined,
    savedAt: view.saved_at,
  };
}

export function favoriteToSavedViewPayload(
  favorite: Omit<SavedFavorite, "id" | "savedAt">,
): Omit<SavedView, "id" | "client_id" | "saved_at"> {
  return {
    snapshot_id: favorite.snapshotId,
    snapshot_label: favorite.snapshotLabel,
    title: favorite.title,
    kind: favorite.kind,
    report_id: favorite.reportId ?? null,
    dimensions: favorite.dimensions ?? null,
    measure_field: favorite.measureField ?? null,
    measure_agg: favorite.measureAgg ?? null,
    chart_type: favorite.chartType ?? null,
    date_preset: favorite.datePreset ?? null,
    date_start: favorite.dateStart ?? null,
    date_end: favorite.dateEnd ?? null,
    scope_field: favorite.scopeField ?? null,
    scope_value: favorite.scopeValue ?? null,
  };
}

function loadLegacyFavorites(): SavedFavorite[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedFavorite[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function loadSavedViews(): Promise<SavedFavorite[]> {
  try {
    const { views } = await fetchSavedViews();
    if (views.length === 0 && typeof window !== "undefined") {
      const migrated = localStorage.getItem(MIGRATED_KEY);
      const legacy = loadLegacyFavorites();
      if (!migrated && legacy.length) {
        await importSavedViews(legacy.map(favoriteToSavedViewPayload));
        localStorage.setItem(MIGRATED_KEY, "1");
        localStorage.removeItem(LEGACY_STORAGE_KEY);
        const again = await fetchSavedViews();
        return again.views.map(savedViewToFavorite);
      }
    }
    return views.map(savedViewToFavorite);
  } catch {
    return loadLegacyFavorites();
  }
}

export async function saveViewRemote(
  favorite: Omit<SavedFavorite, "id" | "savedAt">,
): Promise<SavedFavorite> {
  try {
    const created = await createSavedView(favoriteToSavedViewPayload(favorite));
    return savedViewToFavorite(created);
  } catch {
    const { saveFavorite } = await import("./favorites");
    return saveFavorite(favorite);
  }
}

export async function removeViewRemote(id: string): Promise<void> {
  try {
    await deleteSavedView(id);
  } catch {
    const { removeFavorite } = await import("./favorites");
    removeFavorite(id);
  }
}

export async function getViewRemote(id: string): Promise<SavedFavorite | undefined> {
  const views = await loadSavedViews();
  return views.find((v) => v.id === id);
}
