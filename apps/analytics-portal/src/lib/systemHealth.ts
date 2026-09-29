import { formatDateTime } from "@/lib/format";
import { age, type Freshness } from "@/lib/freshness";

/** GET /portal/health (api/health_routes.py): what this API process has been doing. */

export type HealthError = { reference: string; at: string; route: string; org: string; error: string };
export type HealthSlow = { reference: string; at: string; route: string; status: number; ms: number; org: string };
export type HealthRoute = { route: string; requests: number; server_errors: number; total_ms: number; max_ms: number; avg_ms: number };
export type CacheStats = { hits: number; misses: number; entries: number };

export type SystemHealth = {
  started_at: string;
  slow_ms: number;
  requests: number;
  server_errors: number;
  routes: HealthRoute[];
  slow: HealthSlow[];
  errors: HealthError[];
  cache: CacheStats;
  data_versions: Record<string, { version: string | null; read_seconds_ago: number }>;
  warmed: Record<string, { at: string; version: string; built: string[]; failed: string[] }>;
  freshness?: Record<string, Freshness | null>;
};

/** The error a user's "Reference: 3f9c..." points at, however it was pasted. */
export function findReference(errors: HealthError[], text: string): HealthError | null {
  const ref = text.replace(/reference:?/i, "").trim().toLowerCase();
  return (ref && errors.find((e) => e.reference.toLowerCase() === ref)) || null;
}

export function hitRate(c: CacheStats): string {
  const total = c.hits + c.misses;
  return total ? `${Math.round((100 * c.hits) / total)}%` : "—";
}

/** Each organization's last build, stale ones first (the 36-hour line is api/freshness.py's). */
export function freshnessRows(byOrg: Record<string, Freshness | null>): string[][] {
  const rank = (f: Freshness | null) => (f?.stale ? 0 : f?.built_at ? 1 : 2);
  return Object.entries(byOrg)
    .sort(([a, fa], [b, fb]) => rank(fa) - rank(fb) || a.localeCompare(b))
    .map(([org, f]) =>
      f?.built_at && f.age_hours != null
        ? [org, formatDateTime(f.built_at), `${age(f.age_hours)} ago`, f.stale ? "Stale" : "Fresh"]
        : [org, "—", "—", "Unknown"],
    );
}
