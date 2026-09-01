import type {
  DashboardTileDef,
  DataSourcePayload,
  DataSourceStatus,
  ExecutiveSummary,
  NlqResponse,
  PortalConfig,
  ReportLibraryResponse,
  DatabaseSqlCountResponse,
  DatabaseSqlResponse,
  DatabaseTablesResponse,
  QueryRequest,
  QueryResponse,
  SavedDashboard,
  SavedView,
  SnapshotMetadata,
  SnapshotStats,
  SampleRowsResponse,
  ScopeOptionsResponse,
  SnapshotsIndex,
  WorkstreamSummary,
} from "./types";
import { authHeaders, activeOrganizationHeader } from "./auth";
import { parseApiError } from "@/lib/apiErrors";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function resolveRequestHeaders(init?: RequestInit): Promise<HeadersInit> {
  const merged: Record<string, string> = {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...activeOrganizationHeader(),
  };
  if (typeof window === "undefined") {
    try {
      const { cookies } = await import("next/headers");
      const jar = await cookies();
      const token = jar.get("portal_access_token")?.value;
      if (token) {
        merged.Authorization = `Bearer ${decodeURIComponent(token)}`;
      }
      // The admin's tenant choice, forwarded on the SERVER side as well. Without this
      // the first paint of every page renders against the admin's home tenant.
      const org = jar.get("portal_active_organization")?.value;
      if (org) {
        merged["X-Organization-Id"] = decodeURIComponent(org);
      }
    } catch {
      /* ignore — not in a server context */
    }
  }
  return { ...merged, ...(init?.headers as Record<string, string> | undefined) };
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: await resolveRequestHeaders(init),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(parseApiError(await res.text(), res.statusText));
  }
  return res.json() as Promise<T>;
}

export function fetchPortalConfig(): Promise<PortalConfig> {
  return fetchJson<PortalConfig>("/portal/config");
}

const SETTINGS_TOKEN_KEY = "portal_settings_token";

export function getStoredSettingsToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(SETTINGS_TOKEN_KEY) ?? "";
}

export function storeSettingsToken(token: string): void {
  if (typeof window === "undefined") return;
  if (token.trim()) sessionStorage.setItem(SETTINGS_TOKEN_KEY, token.trim());
  else sessionStorage.removeItem(SETTINGS_TOKEN_KEY);
}

// Generic authenticated GET/POST for feature routes (data quality etc.)
export async function apiGet<T>(path: string): Promise<T> {
  return fetchJson<T>(path);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return fetchJson<T>(path, { method: "POST", body: JSON.stringify(body) });
}

function settingsHeaders(token?: string): Record<string, string> {
  const t = token ?? getStoredSettingsToken();
  return t ? { "X-Portal-Settings-Token": t } : {};
}

export function fetchDataSourceStatus(): Promise<DataSourceStatus> {
  return fetchJson<DataSourceStatus>("/portal/data-source");
}

export function testDataSourceConnection(
  body: DataSourcePayload,
  settingsToken?: string,
): Promise<{ ok: boolean; message?: string; error?: string }> {
  return fetchJson("/portal/data-source/test", {
    method: "POST",
    body: JSON.stringify(body),
    headers: settingsHeaders(settingsToken),
  });
}

export function saveDataSourceConnection(
  body: DataSourcePayload,
  settingsToken?: string,
): Promise<{ saved: boolean; status: DataSourceStatus }> {
  return fetchJson("/portal/data-source", {
    method: "PUT",
    body: JSON.stringify(body),
    headers: settingsHeaders(settingsToken),
  });
}

export function clearDataSourceConnection(
  settingsToken?: string,
): Promise<{ cleared: boolean; status: DataSourceStatus }> {
  return fetchJson("/portal/data-source", {
    method: "DELETE",
    headers: settingsHeaders(settingsToken),
  });
}

export function fetchSnapshots(): Promise<SnapshotsIndex> {
  return fetchJson<SnapshotsIndex>("/snapshots");
}

export function fetchReportLibrary(): Promise<ReportLibraryResponse> {
  return fetchJson<ReportLibraryResponse>("/portal/report-library");
}

export function fetchExecutiveSummary(
  days = 30,
  compare = false,
  crossFilter?: { field: string; value: string },
  compareMode: "prior_period" | "mom" | "yoy" = "prior_period",
  lenses?: Record<string, string>,
): Promise<ExecutiveSummary> {
  const params = new URLSearchParams({
    days: String(days),
    compare: compare ? "true" : "false",
    compare_mode: compareMode,
  });
  if (crossFilter) {
    params.set("cross_field", crossFilter.field);
    params.set("cross_value", crossFilter.value);
  }
  // one `lens=<kpi>:<lens>` per card the reader has switched; the rest keep their default
  for (const [kpiId, lensId] of Object.entries(lenses ?? {})) {
    params.append("lens", `${kpiId}:${lensId}`);
  }
  return fetchJson<ExecutiveSummary>(`/snapshots/executive-summary?${params}`);
}

export function fetchWorkstreamSummary(
  workstreamId: string,
  days = 30,
  compare = false,
  crossFilter?: { field: string; value: string },
  compareMode: "prior_period" | "mom" | "yoy" = "prior_period",
): Promise<WorkstreamSummary> {
  const params = new URLSearchParams({
    days: String(days),
    compare: compare ? "true" : "false",
    compare_mode: compareMode,
  });
  if (crossFilter) {
    params.set("cross_field", crossFilter.field);
    params.set("cross_value", crossFilter.value);
  }
  return fetchJson<WorkstreamSummary>(`/snapshots/workstream-summary/${workstreamId}?${params}`);
}

export function fetchWorkstreamAbout(
  workstreamId: string,
): Promise<import("@/lib/types").WorkstreamAbout> {
  return fetchJson(`/snapshots/workstream-about/${workstreamId}`);
}

export function fetchSavedViews(): Promise<{ client_id: string; views: SavedView[] }> {
  return fetchJson("/portal/saved-views");
}

export function createSavedView(
  body: Omit<SavedView, "id" | "client_id" | "saved_at">,
): Promise<SavedView> {
  return fetchJson<SavedView>("/portal/saved-views", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteSavedView(viewId: string): Promise<void> {
  return fetchJson(`/portal/saved-views/${viewId}`, { method: "DELETE" });
}

export type ReportSchedule = {
  id: string;
  saved_view_id: string;
  view_title?: string | null;
  recipients: string[];
  cadence: "daily" | "weekly" | "monthly";
  weekday: number;
  hour_utc: number;
  window_days: number;
  enabled: boolean;
  last_run_at?: string | null;
  last_status?: string | null;
};

export function fetchReportSchedules(): Promise<{
  schedules: ReportSchedule[];
  smtp_configured: boolean;
}> {
  return fetchJson("/report-schedules");
}

export function createReportSchedule(body: {
  saved_view_id: string;
  recipients: string[];
  cadence: string;
  weekday?: number;
  hour_utc?: number;
  window_days?: number;
}): Promise<ReportSchedule> {
  return fetchJson("/report-schedules", { method: "POST", body: JSON.stringify(body) });
}

export function deleteReportSchedule(scheduleId: string): Promise<void> {
  return fetchJson(`/report-schedules/${scheduleId}`, { method: "DELETE" });
}

export type KpiAlert = {
  id: string;
  kpi_id: string;
  kpi_label: string;
  condition: "above" | "below" | "pct_change_above" | "pct_change_below";
  threshold: number;
  window_days: number;
  recipients: string[];
  enabled: boolean;
  last_state: "ok" | "breached";
  last_status?: string | null;
};

export type WatchableKpi = { id: string; label: string; subtitle: string; format: string };

export function fetchKpiAlerts(): Promise<{
  alerts: KpiAlert[];
  available_kpis: WatchableKpi[];
  smtp_configured: boolean;
}> {
  return fetchJson("/kpi-alerts");
}

export function createKpiAlert(body: {
  kpi_id: string;
  condition: string;
  threshold: number;
  window_days?: number;
  recipients: string[];
}): Promise<KpiAlert> {
  return fetchJson("/kpi-alerts", { method: "POST", body: JSON.stringify(body) });
}

export function deleteKpiAlert(alertId: string): Promise<void> {
  return fetchJson(`/kpi-alerts/${alertId}`, { method: "DELETE" });
}

export type Annotation = {
  id: string;
  target_type: string;
  target_id: string;
  text: string;
  author_email: string;
  created_at: string;
};

export function fetchAnnotations(
  targetType: string,
  targetId: string,
): Promise<{ annotations: Annotation[] }> {
  const q = new URLSearchParams({ target_type: targetType, target_id: targetId });
  return fetchJson(`/annotations?${q}`);
}

export function createAnnotation(body: {
  target_type: string;
  target_id: string;
  text: string;
}): Promise<Annotation> {
  return fetchJson("/annotations", { method: "POST", body: JSON.stringify(body) });
}

export function deleteAnnotation(annotationId: string): Promise<void> {
  return fetchJson(`/annotations/${annotationId}`, { method: "DELETE" });
}

export function importSavedViews(
  views: Omit<SavedView, "id" | "client_id" | "saved_at">[],
): Promise<{ imported: number; views: SavedView[] }> {
  return fetchJson("/portal/saved-views/import", {
    method: "POST",
    body: JSON.stringify({ views }),
  });
}

export function runNlqQuery(query: string): Promise<NlqResponse> {
  return fetchJson<NlqResponse>("/nlq", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export function runAnalyticsNlq(
  query: string,
  params?: {
    metric_id?: string;
    days?: number;
    bill_cycle?: string;
    customer_class?: string;
    payment_type?: string;
    uom?: string;
    rate_code?: string;
  },
): Promise<NlqResponse> {
  return fetchJson<NlqResponse>("/portal/analytics-nlq", {
    method: "POST",
    body: JSON.stringify({ query, ...params }),
  });
}

export function fetchNlqMetricCatalog(): Promise<{ metrics: import("@/lib/types").NlqMetricCatalogItem[] }> {
  return fetchJson("/portal/analytics-nlq/metrics");
}

export function fetchDashboards(): Promise<{ client_id: string; dashboards: SavedDashboard[] }> {
  return fetchJson("/portal/dashboards");
}

export function fetchDashboard(id: string): Promise<SavedDashboard> {
  return fetchJson(`/portal/dashboards/${id}`);
}

export function createDashboard(body: {
  title: string;
  description?: string;
  days?: number;
  tiles: DashboardTileDef[];
}): Promise<SavedDashboard> {
  return fetchJson("/portal/dashboards", { method: "POST", body: JSON.stringify(body) });
}

export function updateDashboard(
  id: string,
  body: Partial<{ title: string; description: string; days: number; tiles: DashboardTileDef[] }>,
): Promise<SavedDashboard> {
  return fetchJson(`/portal/dashboards/${id}`, { method: "PUT", body: JSON.stringify(body) });
}

export function deleteDashboard(id: string): Promise<void> {
  return fetchJson(`/portal/dashboards/${id}`, { method: "DELETE" });
}

export function fetchBuilderQuestions(): Promise<import("@/lib/types").BuilderQuestionsResponse> {
  return apiGet("/snapshots/questions");
}

export function fetchSnapshotMetadata(snapshotId: string): Promise<SnapshotMetadata> {
  return fetchJson<SnapshotMetadata>(`/snapshots/${snapshotId}/metadata`);
}

export function runSnapshotQuery(
  snapshotId: string,
  body: QueryRequest,
): Promise<QueryResponse> {
  return fetchJson<QueryResponse>(`/snapshots/${snapshotId}/query`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchScopeOptions(
  snapshotId: string,
  fieldId: string,
): Promise<ScopeOptionsResponse> {
  return fetchJson<ScopeOptionsResponse>(`/snapshots/${snapshotId}/scope-options/${fieldId}`);
}

export function fetchSnapshotStats(snapshotId: string): Promise<SnapshotStats> {
  return fetchJson<SnapshotStats>(`/snapshots/${snapshotId}/stats`);
}

export function fetchSnapshotSampleRows(
  snapshotId: string,
  limit = 3,
): Promise<SampleRowsResponse> {
  return fetchJson<SampleRowsResponse>(`/snapshots/${snapshotId}/sample-rows?limit=${limit}`);
}

export function runSnapshotRawSql(
  snapshotId: string,
  sql: string,
  limit = 100,
): Promise<QueryResponse> {
  return fetchJson<QueryResponse>(`/snapshots/${snapshotId}/raw-sql`, {
    method: "POST",
    body: JSON.stringify({ sql, limit }),
  });
}

export function defaultDateRange(days = 90): [string, string] {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - days);
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}

export function defaultDateRangeYtd(): [string, string] {
  const end = new Date();
  const start = new Date(end.getFullYear(), 0, 1);
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}

export function defaultDateRangeLastMonth(): [string, string] {
  const end = new Date();
  end.setDate(0);
  const start = new Date(end.getFullYear(), end.getMonth(), 1);
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}

export function fetchDatabaseTables(
  // Empty = let the API pick the engine's own schema (reporting for the warehouse,
  // CISADM for a legacy Oracle tenant).
  schema = "",
  search = "",
  opts?: { snapshotsOnly?: boolean; includeStats?: boolean },
): Promise<DatabaseTablesResponse> {
  const params = new URLSearchParams(schema ? { schema } : {});
  if (search.trim()) params.set("search", search.trim());
  if (opts?.snapshotsOnly === false) params.set("snapshots_only", "false");
  if (opts?.includeStats) params.set("include_stats", "true");
  return fetchJson<DatabaseTablesResponse>(`/database/tables?${params}`);
}

export function executeDatabaseSql(body: {
  sql: string;
  offset?: number;
  page_size?: number;
  include_total_count?: boolean;
}): Promise<DatabaseSqlResponse> {
  return fetchJson<DatabaseSqlResponse>("/database/sql/execute", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function countDatabaseSql(sql: string): Promise<DatabaseSqlCountResponse> {
  return fetchJson<DatabaseSqlCountResponse>("/database/sql/count", {
    method: "POST",
    body: JSON.stringify({ sql, offset: 0, page_size: 50 }),
  });
}
