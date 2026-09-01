"use client";

import { useEffect, useMemo, useState } from "react";
import { useBrand } from "@/components/PortalThemeProvider";
import { printLineagePack } from "@/lib/lineagePack";
import { fieldRoleLabel } from "@/lib/businessLabels";
import type { FieldDef, SnapshotDataModel, SnapshotMetadata } from "@/lib/types";
import { cisadmTableGuide } from "@/lib/cisadmTableGuide";

type ModelTab = "overview" | "tables" | "joins" | "fields";

const ROLE_LABELS: Record<string, string> = {
  driving: "Driving table",
  context: "Context join",
  optional_child: "Optional child (type-gated)",
  lookup: "Lookup / description",
};

const ROLE_COLORS: Record<string, string> = {
  driving: "text-ok ring-ok bg-ok-bg",
  context: "text-primary ring-edge bg-band",
  optional_child: "text-warn ring-warn bg-warn-bg",
  lookup: "text-chart-2 dark:text-chart-2 ring-edge text-chart-2",
};

const FIELD_ROLE_COLORS: Record<string, string> = {
  dimension: "text-primary bg-band",
  measure: "text-ok bg-ok-bg",
  date: "text-warn bg-warn-bg",
};

export function SnapshotDataModelPanel({
  metadata,
  initialSubTab,
}: {
  metadata: SnapshotMetadata;
  initialSubTab?: ModelTab;
}) {
  const brand = useBrand();
  const model = metadata.data_model;
  const [tab, setTab] = useState<ModelTab>(initialSubTab ?? "overview");
  const [fieldQuery, setFieldQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");

  useEffect(() => {
    if (initialSubTab) setTab(initialSubTab);
  }, [initialSubTab]);

  const fields = metadata.fields ?? [];
  const filteredFields = useMemo(() => {
    const q = fieldQuery.trim().toLowerCase();
    return fields.filter((field) => {
      if (roleFilter !== "all" && field.role !== roleFilter) return false;
      if (!q) return true;
      return (
        field.id.toLowerCase().includes(q) ||
        field.label.toLowerCase().includes(q) ||
        (field.group ?? "").toLowerCase().includes(q)
      );
    });
  }, [fields, fieldQuery, roleFilter]);

  if (!model) {
    return (
      <div className="glass-panel p-8 text-center text-sm text-fg-muted">
        Data model documentation is not available for this domain yet.
      </div>
    );
  }

  return (
    <div id="lineage-pack-export" className="lineage-pack space-y-4">
      <div className="lineage-pack-header hidden print:block">
        <p className="text-xs uppercase tracking-widest text-fg-muted">{brand.name}</p>
        <h1 className="text-2xl font-bold text-slate-900">{metadata.label} — Data Model</h1>
        <p className="mt-1 font-mono text-sm text-slate-700">
          {model.snapshot_table} · grain: {model.grain}
        </p>
        <p className="mt-2 text-xs text-fg-muted">
          Generated {new Date().toLocaleString()} · {brand.name}
        </p>
        <hr className="my-4 border-slate-300" />
      </div>

      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-fg-muted">
          Governed lineage for client transparency — source tables, join logic, and field catalog.
        </p>
        <button
          type="button"
          onClick={() => printLineagePack(`${metadata.label} Data Model`)}
          className="btn-primary text-xs"
        >
          Lineage pack (PDF)
        </button>
      </div>

      <div className="glass-panel p-2 no-print">
        <div className="grid grid-cols-2 gap-1 sm:grid-cols-4">
          {(
            [
              ["overview", "Overview"],
              ["tables", "Source tables"],
              ["joins", "Join paths"],
              ["fields", "All fields"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`rounded-xl px-2 py-2.5 text-xs font-medium transition sm:text-sm ${
 tab === key
 ? "bg-gradient-to-r from-primary to-accent-2 text-heading ring-1 ring-edge"
 : "text-fg-muted hover:bg-chip hover:text-heading"
 }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {tab === "overview" ? <OverviewTab model={model} metadata={metadata} /> : null}
      {tab === "tables" ? <TablesTab model={model} /> : null}
      {tab === "joins" ? (
        <JoinsTab model={model} onPrint={() => printLineagePack(`${metadata.label} Join Paths`)} />
      ) : null}
      {tab === "fields" ? (
        <FieldsTab
          fields={filteredFields}
          totalCount={fields.length}
          fieldQuery={fieldQuery}
          roleFilter={roleFilter}
          onFieldQueryChange={setFieldQuery}
          onRoleFilterChange={setRoleFilter}
          trustedMeasures={model.trusted_measures}
        />
      ) : null}
    </div>
  );
}

function OverviewTab({
  model,
  metadata,
}: {
  model: SnapshotDataModel;
  metadata: SnapshotMetadata;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="glass-panel space-y-4 p-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
            Governed canvas
          </p>
          <p className="mt-2 font-mono text-sm text-primary">{model.snapshot_table}</p>
          <p className="mt-1 text-xs text-fg-muted">
            End-user Domain points at this table — not live C2M joins at report runtime.
          </p>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
            Row grain
          </p>
          <p className="mt-2 text-sm text-heading">{model.grain}</p>
          <p className="mt-1 text-xs text-fg-muted">{model.grain_description}</p>
        </div>
        <div className="rounded-xl border border-edge-subtle bg-surface-subtle px-4 py-3 text-xs text-fg">
          {model.grain_preservation}
        </div>
        {model.trusted_measures.length ? (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
              Trusted additive measures
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {model.trusted_measures.map((measure) => (
                <span
                  key={measure}
                  className="rounded-full bg-ok-bg px-3 py-1 text-xs font-medium text-ok ring-1 ring-ok"
                >
                  {measure}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-fg-muted">
            This domain is primarily for counts and workflow monitoring — no single trusted dollar
            measure is published.
          </p>
        )}
      </section>

      <section className="glass-panel space-y-4 p-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
            Driving C2M table
          </p>
          <p className="mt-2 font-mono text-sm text-heading">
            CISADM.{model.driving_table ?? "—"}
          </p>
          <p className="mt-1 text-xs text-fg-muted">
            Population and grain are anchored here during the nightly refresh.
          </p>
        </div>
        {model.population_filter ? (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-muted">
              Population filter
            </p>
            <pre className="mt-2 overflow-x-auto rounded-lg bg-black/30 p-3 text-xs text-fg">
              {model.population_filter}
            </pre>
          </div>
        ) : null}
        <div className="grid grid-cols-2 gap-3 text-center">
          <StatCard label="Source tables" value={String(model.source_tables.length)} />
          <StatCard label="Join steps" value={String(model.join_paths.length)} />
          <StatCard label="Domain fields" value={String(metadata.fields?.length ?? 0)} />
          <StatCard label="Field groups" value={String(model.field_groups.length)} />
        </div>
        {model.refresh_sql ? (
          <p className="text-[10px] text-fg-muted">
            Lineage parsed from{" "}
            <span className="font-mono text-fg-muted">{model.refresh_sql}</span>
          </p>
        ) : null}
      </section>
    </div>
  );
}

function TablesTab({ model }: { model: SnapshotDataModel }) {
  const grouped = useMemo(() => {
    // Two catalog shapes: the legacy Oracle build emits {table, role, alias} objects;
    // the dbt build emits plain CISADM table names (lineage-derived — no per-table role,
    // so they all group under "source"). Normalise so both render.
    const normalized = model.source_tables.map((t) =>
      typeof t === "string" ? { table: t, role: "source", alias: undefined } : t,
    );
    const order = ["driving", "context", "optional_child", "lookup", "source"];
    const map = new Map<string, typeof normalized>();
    for (const table of normalized) {
      const list = map.get(table.role) ?? [];
      list.push(table);
      map.set(table.role, list);
    }
    return order
      .filter((role) => (map.get(role)?.length ?? 0) > 0)
      .map((role) => ({ role, tables: map.get(role) ?? [] }));
  }, [model.source_tables]);

  return (
    <div className="space-y-4">
      <p className="text-sm text-fg-muted">
        These Oracle tables are combined during the canvas refresh. Analysts query the flattened{" "}
        <span className="font-mono text-primary">{model.snapshot_table}</span> table in the portal.
      </p>
      {grouped.map(({ role, tables }) => (
        <section key={role} className="glass-panel p-5">
          <div className="mb-4 flex items-center gap-2">
            <span className={`chip ${ROLE_COLORS[role] ?? ""}`}>{ROLE_LABELS[role] ?? role}</span>
            <span className="text-xs text-fg-muted">{tables.length} tables</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {tables.map((table) => {
              const guide = cisadmTableGuide(table.table);
              return (
                <div
                  key={table.table}
                  className="rounded-xl border border-edge-subtle bg-surface-subtle px-4 py-3"
                >
                  <p className="font-mono text-sm text-heading">CISADM.{table.table}</p>
                  {guide ? <p className="mt-1 text-xs text-fg-muted">{guide}</p> : null}
                  {table.alias ? (
                    <p className="mt-1 text-xs text-fg-subtle">SQL alias: {table.alias}</p>
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

function JoinsTab({ model, onPrint }: { model: SnapshotDataModel; onPrint?: () => void }) {
  if (!model.join_paths.length) {
    return (
      <div className="glass-panel p-8 text-center text-sm text-fg-muted">
        No join paths were parsed for this canvas (may use UNION or a custom refresh pattern).
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="no-print flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-fg-muted">
          Join logic applied when building{" "}
          <span className="font-mono text-primary">{model.snapshot_table}</span>. LEFT joins preserve
          the driving population; optional-child joins only populate when FT/type rules match.
        </p>
        {onPrint ? (
          <button type="button" onClick={onPrint} className="btn-ghost text-xs shrink-0">
            Print join diagram
          </button>
        ) : null}
      </div>
      <div className="relative space-y-3">
        <div className="absolute bottom-4 left-5 top-4 w-px bg-gradient-to-b from-primary to-accent-2" />
        {model.driving_table ? (
          <div className="relative pl-12">
            <span className="absolute left-3 top-4 h-4 w-4 rounded-full bg-ok ring-4 ring-ok" />
            <div className="glass-panel p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-ok">
                Start · driving table
              </p>
              <p className="mt-1 font-mono text-sm text-heading">CISADM.{model.driving_table}</p>
            </div>
          </div>
        ) : null}
        {model.join_paths.map((join, index) => (
          <div key={`${join.table}-${index}`} className="relative pl-12">
            <span className="absolute left-3 top-5 h-4 w-4 rounded-full bg-band ring-4 ring-edge" />
            <div className="glass-panel p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
                  Step {index + 1}
                </span>
                <span className={`chip text-[10px] ${ROLE_COLORS[join.role] ?? ""}`}>
                  {join.join_type} · {ROLE_LABELS[join.role] ?? join.role}
                </span>
              </div>
              <p className="mt-2 font-mono text-sm text-heading">
                CISADM.{join.table}
                {join.alias ? ` AS ${join.alias}` : ""}
              </p>
              <pre className="mt-3 overflow-x-auto rounded-lg bg-black/30 p-3 text-xs leading-relaxed text-fg">
                ON {join.on}
              </pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FieldsTab({
  fields,
  totalCount,
  fieldQuery,
  roleFilter,
  onFieldQueryChange,
  onRoleFilterChange,
  trustedMeasures,
}: {
  fields: FieldDef[];
  totalCount: number;
  fieldQuery: string;
  roleFilter: string;
  onFieldQueryChange: (value: string) => void;
  onRoleFilterChange: (value: string) => void;
  trustedMeasures: string[];
}) {
  const trusted = new Set(trustedMeasures.map((m) => m.toUpperCase()));

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-fg-muted">
          {fields.length} of {totalCount} fields available for filters, group-by, and metrics in
          this Domain.
        </p>
        <div className="flex flex-wrap gap-2">
          <input
            type="search"
            placeholder="Search fields…"
            value={fieldQuery}
            onChange={(e) => onFieldQueryChange(e.target.value)}
            className="input-modern min-w-[200px] text-xs"
          />
          <select
            value={roleFilter}
            onChange={(e) => onRoleFilterChange(e.target.value)}
            className="input-modern text-xs"
          >
            <option value="all">All roles</option>
            <option value="dimension">Fields</option>
            <option value="measure">Measures</option>
            <option value="date">Dates</option>
          </select>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="max-h-[560px] overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 border-b border-edge-subtle bg-surface-solid backdrop-blur">
              <tr>
                <th className="px-4 py-3 font-medium text-fg-muted">Field</th>
                <th className="px-4 py-3 font-medium text-fg-muted">Business label</th>
                <th className="px-4 py-3 font-medium text-fg-muted">Role</th>
                <th className="hidden px-4 py-3 font-medium text-fg-muted md:table-cell">Group</th>
                <th className="hidden px-4 py-3 font-medium text-fg-muted lg:table-cell">Type</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field) => (
                <tr key={field.id} className="border-b border-edge-subtle hover:bg-white/[0.02]">
                  <td className="px-4 py-2.5 font-mono text-xs text-primary">{field.id}</td>
                  <td className="px-4 py-2.5 text-heading">
                    {field.label}
                    {trusted.has(field.id) ? (
                      <span className="ml-2 rounded bg-ok-bg px-1.5 py-0.5 text-[10px] text-ok">
                        trusted
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${
 FIELD_ROLE_COLORS[field.role] ?? "text-fg-muted bg-chip"
 }`}
                    >
                      {fieldRoleLabel(field.role)}
                    </span>
                  </td>
                  <td className="hidden px-4 py-2.5 text-xs text-fg-muted md:table-cell">
                    {field.group ?? "—"}
                  </td>
                  <td className="hidden px-4 py-2.5 text-xs text-fg-muted lg:table-cell">
                    {field.type.replace("java.lang.", "").replace("java.sql.", "").replace("java.math.", "")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-edge-subtle bg-surface-subtle px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-heading">{value}</p>
    </div>
  );
}
