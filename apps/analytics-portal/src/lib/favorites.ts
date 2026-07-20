export type SavedFavorite = {
  id: string;
  snapshotId: string;
  snapshotLabel: string;
  title: string;
  kind: "premade" | "custom";
  reportId?: string;
  dimensions?: string[];
  measureField?: string;
  measureAgg?: string;
  chartType?: "bar" | "line" | "pie" | "horizontal" | "table";
  datePreset?: string;
  dateStart?: string;
  dateEnd?: string;
  scopeField?: string;
  scopeValue?: string;
  savedAt: string;
};

const STORAGE_KEY = "originba_utility_insights_favorites";

export function loadFavorites(): SavedFavorite[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedFavorite[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveFavorite(favorite: Omit<SavedFavorite, "id" | "savedAt">): SavedFavorite {
  const entry: SavedFavorite = {
    ...favorite,
    id: crypto.randomUUID(),
    savedAt: new Date().toISOString(),
  };
  const existing = loadFavorites().filter(
    (f) => !(f.snapshotId === entry.snapshotId && f.title === entry.title),
  );
  const next = [entry, ...existing].slice(0, 12);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return entry;
}

export function removeFavorite(id: string): void {
  const next = loadFavorites().filter((f) => f.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function getFavorite(id: string): SavedFavorite | undefined {
  return loadFavorites().find((f) => f.id === id);
}
