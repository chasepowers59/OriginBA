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
    const detail = await res.text();
    throw new Error(detail || res.statusText);
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
): Promise<ExecutiveSummary> {
  const params = new URLSearchParams({
    days: String(days),
    compare: compare ? "true" : "false",
  });
  if (crossFilter) {
    params.set("cross_field", crossFilter.field);
    params.set("cross_value", crossFilter.value);
  }
  return fetchJson<ExecutiveSummary>(`/snapshots/executive-summary?${params}`);
}

export function fetchWorkstreamSummary(
  workstreamId: string,
  days = 30,
  compare = false,
  crossFilter?: { field: string; value: string },
): Promise<WorkstreamSummary> {
  const params = new URLSearchParams({
    days: String(days),
    compare: compare ? "true" : "false",
  });
  if (crossFilter) {
    params.set("cross_field", crossFilter.field);
    params.set("cross_value", crossFilter.value);
  }
  return fetchJson<WorkstreamSummary>(`/snapshots/workstream-summary/${workstreamId}?${params}`);
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
  schema = "CISADM",
  search = "",
  opts?: { snapshotsOnly?: boolean; includeStats?: boolean },
): Promise<DatabaseTablesResponse> {
  const params = new URLSearchParams({ schema });
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
