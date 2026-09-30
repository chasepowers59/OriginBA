/** Folders for saved views and dashboards: named folders alphabetically, unfiled last. */

export function groupByFolder<T extends { folder?: string | null }>(items: T[]): { folder: string | null; items: T[] }[] {
  const groups = new Map<string | null, T[]>();
  for (const item of items) {
    const key = item.folder || null;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  const named = [...groups.keys()].filter((k): k is string => k !== null).sort((a, b) => a.localeCompare(b));
  return [...named.map((folder) => ({ folder, items: groups.get(folder)! })),
          ...(groups.has(null) ? [{ folder: null, items: groups.get(null)! }] : [])];
}

export function folderNames(items: { folder?: string | null }[]): string[] {
  return [...new Set(items.map((i) => i.folder).filter((f): f is string => Boolean(f)))].sort((a, b) => a.localeCompare(b));
}
