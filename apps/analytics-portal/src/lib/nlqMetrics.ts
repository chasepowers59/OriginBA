import type { NlqMetricCatalogItem } from "./types";

export type MetricGroup = { category: string; items: NlqMetricCatalogItem[] };

/** The vetted-metric catalogue by category, in the order the API lists it, for a picker. */
export function groupMetrics(catalog: NlqMetricCatalogItem[]): MetricGroup[] {
  const map = new Map<string, NlqMetricCatalogItem[]>();
  for (const m of catalog) map.set(m.category, [...(map.get(m.category) ?? []), m]);
  return [...map.entries()].map(([category, items]) => ({ category, items }));
}
