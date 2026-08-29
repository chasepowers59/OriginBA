export type DataSourceStatus = {
  configured: boolean;
  source: "portal_vault" | "portal_memory" | "environment" | "none";
  organization_id?: string;
  user_masked: string | null;
  dsn_masked: string | null;
  thick_mode: boolean;
  has_oracle_client_lib_dir: boolean;
  saved_at: string | null;
  env_fallback_available: boolean;
  settings_token_required: boolean;
};

export type DataSourcePayload = {
  user: string;
  password: string;
  dsn: string;
  oracle_client_lib_dir?: string;
  thick_mode?: boolean;
};

export type SnapshotSummary = {
  id: string;
  label: string;
  workstream: string;
  workstream_label?: string;
  grain: string;
  grain_description?: string;
  summary?: string;
  trusted_measures: string[];
  required_date_field: string | null;
  portal_enabled?: boolean;
  poc_enabled: boolean;
  large_domain?: boolean;
};

export type WorkstreamFeatured = {
  snapshot_id: string;
  report_id: string;
};

export type BusinessProcessReport = {
  snapshot_id: string;
  report_id: string | null;
  title: string;
  snapshot_label?: string;
};

export type BusinessProcess = {
  id: string;
  workstream: string;
  label: string;
  description: string;
  reports: BusinessProcessReport[];
};

export type ProcessFieldGuide = {
  label: string;
  description: string;
  dimensions: string[];
  measures: string[];
  scope_fields?: string[];
  report_ids?: string[];
};

export type WorkstreamGroup = {
  id: string;
  label: string;
  snapshot_count: number;
  snapshots: SnapshotSummary[];
  processes?: BusinessProcess[];
  featured?: WorkstreamFeatured[];
};

export type DatePresetConfig = {
  kind: "days" | "ytd" | "last_month";
  days?: number;
  label: string;
};

export type MeasureDef = { id: string; label: string; aggs: string[] };
export type FieldDef = {
  id: string;
  label: string;
  type: string;
  role: string;
  group?: string;
  description?: string;
};

export type SourceTableDef = {
  table: string;
  role: string;
  alias?: string;
};

export type JoinPathDef = {
  join_type: string;
  table: string;
  alias: string;
  on: string;
  role: string;
  from?: string;
};

export type FieldGroupDef = {
  id: string;
  label: string;
  fields: { id: string; label: string }[];
};

export type SnapshotDataModel = {
  snapshot_table: string;
  domain_table: string;
  grain: string;
  grain_description: string;
  grain_preservation: string;
  trusted_measures: string[];
  driving_table: string | null;
  source_tables: SourceTableDef[];
  join_paths: JoinPathDef[];
  population_filter: string | null;
  refresh_sql?: string;
  field_groups: FieldGroupDef[];
};

export type PremadeReport = {
  id: string;
  title: string;
  description: string;
  dimensions: string[];
  measures: { field: string; agg: string }[];
  filters: FilterDef[];
  chart_type: "bar" | "line" | "pie" | "horizontal";
};

export type ScopeFilterDef = {
  field: string;
  label: string;
};

export type ScopeOptionsResponse = {
  snapshot_id: string;
  field: string;
  label: string;
  values: string[];
};

export type SnapshotMetadata = {
  schema: string;
  id: string;
  client: string;
  table_name: string;
  label: string;
  workstream: string;
  workstream_label?: string;
  grain: string;
  grain_description?: string;
  summary?: string;
  use_case?: string;
  required_date_label?: string;
  dimensions: { id: string; label: string }[];
  measures: MeasureDef[];
  date_fields: { id: string; label: string }[];
  default_date_field: string;
  required_date_field: string;
  premade_reports: PremadeReport[];
  scope_filters?: ScopeFilterDef[];
  usage_guidance?: string;
  related_snapshot?: { id: string; label: string; hint: string };
  suggested_default_filter: FilterDef | null;
  fields?: FieldDef[];
  data_model?: SnapshotDataModel;
  large_domain?: boolean;
  skip_sample_rows?: boolean;
  default_date_preset?: DatePresetConfig;
  trusted_measures?: string[];
  process_guides?: Record<string, ProcessFieldGuide>;
};

export type BuilderMeasure = { field: string; agg: string };

/** A cross-canvas "common business question" (flattened premade reports) served by
 *  GET /snapshots/questions; picking one prefills the visual builder. */
export type BuilderQuestion = {
  id: string;
  report_id: string;
  snapshot_id: string;
  snapshot_label: string;
  workstream: string;
  workstream_label: string;
  title: string;
  description: string;
  dimensions: string[];
  measures: BuilderMeasure[];
  filters: FilterDef[];
  chart_type: string;
};

export type BuilderQuestionsResponse = {
  organization_id: string | null;
  workstream_order: string[];
  workstream_labels: Record<string, string>;
  count: number;
  questions: BuilderQuestion[];
};

export type FilterDef = {
  field: string;
  op: string;
  value: unknown;
};

export type QueryRequest = {
  dimensions: string[];
  measures: { field: string; agg: string }[];
  filters: FilterDef[];
  time_dimensions?: { field: string; grain: string }[];
  limit: number;
};

export type QueryResponse = {
  /** Server-side labels for EVERY column, aggregate aliases included. The client-side
   *  builder only ever named the last measure, so a report with two measures showed one
   *  of them as "m0". */
  column_labels?: Record<string, string>;
  client: string;
  snapshot_id: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  sql: string;
};

export type DatabaseTableInfo = {
  table_name: string;
  num_rows: number | null;
  last_analyzed: string | null;
};

export type DatabaseTablesResponse = {
  organization_id: string;
  /** "postgres" = the dbt reporting warehouse; "oracle" = legacy CISADM snapshots. */
  engine?: "postgres" | "oracle";
  schema: string;
  tables: DatabaseTableInfo[];
  table_count: number;
};

export type DatabaseSqlResponse = {
  organization_id: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  offset: number;
  page_size: number;
  has_more: boolean;
  fetched_total: number;
  total_count: number | null;
  execution_ms: number;
  sql: string;
};

export type DatabaseSqlCountResponse = {
  organization_id: string;
  total_count: number;
  execution_ms: number;
  sql: string;
};

export type SnapshotStats = {
  snapshot_id: string;
  client: string;
  row_count: number;
  latest_load_dttm: string | null;
};

export type SampleRowsResponse = {
  snapshot_id: string;
  grain_description?: string;
  columns: string[];
  column_labels: Record<string, string>;
  rows: Record<string, unknown>[];
  row_count: number;
  sql: string;
};

export type SnapshotsIndex = {
  client: string;
  workstream_order?: string[];
  workstream_labels?: Record<string, string>;
  portal_snapshots?: string[];
  poc_enabled: string[];
  db_configured: boolean;
  workstreams?: WorkstreamGroup[];
  snapshots: SnapshotSummary[];
};

export type ExecutiveTrendPoint = {
  label: string;
  value: number;
};

export type ExecutiveKpi = {
  id: string;
  label: string;
  subtitle: string;
  snapshot_id: string;
  format: "currency" | "number";
  workstream: string;
  explore_report_id?: string | null;
  value: number | null;
  prior_value?: number | null;
  change_pct?: number | null;
  /** "vs July" / "vs 2025" / "vs prior 30d" — set by the API per compare mode. */
  compare_label?: string | null;
  trend: ExecutiveTrendPoint[];
  trend_dimension?: string | null;
  error?: string | null;
};

export type PeriodInfo = {
  start: string;
  end: string;
  label: string;
  days: number;
};

export type WorkstreamAbout = {
  workstream: string;
  label: string;
  summary: string;
  canvases: { id: string; label: string; grain: string | null }[];
  kpis: { id: string; label: string; subtitle: string }[];
  not_included: string[];
  related: { workstream: string; label: string; via: string }[];
};

export type RefreshInsight = {
  last_refresh: string | null;
  tables: { table: string; batch_rows: number; total_rows: number }[];
};

export type ExecutiveSummary = {
  refresh?: RefreshInsight | null;
  client: string;
  db_configured: boolean;
  compare_enabled?: boolean;
  period: PeriodInfo;
  prior_period?: PeriodInfo;
  kpis: ExecutiveKpi[];
};

export type WorkstreamSummary = {
  client: string;
  db_configured: boolean;
  compare_enabled?: boolean;
  workstream: string;
  workstream_label: string;
  period: PeriodInfo;
  prior_period?: PeriodInfo;
  kpis: ExecutiveKpi[];
};

export type PortalBrandConfig = {
  name: string;
  product: string;
  tagline: string;
  logo_initials: string;
  logo_src?: string;
  connection_label: string;
  footer: string;
};

export type PortalThemeConfig = {
  accent_from: string;
  accent_to: string;
  accent_muted: string;
  mesh_glow_1: string;
  mesh_glow_2: string;
  mesh_glow_3: string;
};

export type PortalConfig = {
  client_id: string;
  organization_id?: string;
  organization_name: string;
  brand: PortalBrandConfig;
  theme: PortalThemeConfig;
};

export type SavedView = {
  id: string;
  client_id: string;
  snapshot_id: string;
  snapshot_label: string;
  title: string;
  kind: "premade" | "custom";
  report_id?: string | null;
  dimensions?: string[] | null;
  measure_field?: string | null;
  measure_agg?: string | null;
  chart_type?: string | null;
  date_preset?: string | null;
  date_start?: string | null;
  date_end?: string | null;
  scope_field?: string | null;
  scope_value?: string | null;
  saved_at: string;
};

export type NlqMetricCatalogItem = {
  id: string;
  label: string;
  category: string;
  snapshot_id: string;
  default_days: number;
  format: string;
  param_keys: string[];
  example: string;
};

export type NlqPinSpec = {
  visual: "chart" | "kpi";
  measure_field?: string;
  measure_agg?: string;
  dimensions?: string[];
};

export type NlqResponse = {
  narrative: string;
  acct_id?: number | null;
  metrics?: Record<string, unknown> | null;
  resolved_from?: string | null;
  source?: string;
  metric_id?: string;
  metric_label?: string;
  format?: "number" | "currency";
  pin?: NlqPinSpec;
  param_schema?: string[];
  params_used?: Record<string, unknown>;
  table?: { columns: string[]; rows: { label: string; value: number }[] };
};

export type DashboardTileDef = {
  id: string;
  slot: number;
  title: string;
  visual: "chart" | "kpi" | "table";
  snapshot_id: string;
  report_id?: string | null;
  dimensions?: string[];
  measure_field?: string | null;
  measure_agg?: string | null;
  chart_type?: string | null;
  time_grain?: string | null;
};

export type SavedDashboard = {
  id: string;
  client_id: string;
  title: string;
  description?: string;
  days: number;
  tiles: DashboardTileDef[];
  created_at: string;
  updated_at: string;
};

export type TimeGrain = "month" | "quarter" | "year";

export type ReportLibraryEntry = {
  snapshot_id: string;
  snapshot_label: string;
  workstream: string;
  workstream_label: string;
  report_id: string;
  title: string;
  description: string;
  chart_type: string;
  explore_url: string;
};

export type ReportLibraryPack = {
  id: string;
  title: string;
  description: string;
  audience: string;
  report_count: number;
  reports: ReportLibraryEntry[];
};

export type ReportLibraryResponse = {
  client: string;
  pack_count: number;
  report_count: number;
  packs: ReportLibraryPack[];
  error?: string;
};
