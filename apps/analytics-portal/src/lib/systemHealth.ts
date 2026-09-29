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
