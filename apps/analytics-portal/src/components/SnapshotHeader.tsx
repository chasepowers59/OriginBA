"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchSnapshotStats } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import type { SnapshotMetadata } from "@/lib/types";
import { snapshotDetailLine, snapshotSubtitle } from "@/lib/snapshot";
import {
  requiredDateLabel,
  snapshotSummary,
  workstreamDisplayName,
} from "@/lib/businessLabels";

export function SnapshotHeader({ metadata }: { metadata: SnapshotMetadata }) {
  const model = metadata.data_model;
  const [rowCount, setRowCount] = useState<number | null>(null);
  const [loadDttm, setLoadDttm] = useState<string | null>(null);

  useEffect(() => {
    fetchSnapshotStats(metadata.id)
      .then((s) => {
        setRowCount(s.row_count);
        setLoadDttm(s.latest_load_dttm);
      })
      .catch(() => {
        setRowCount(null);
        setLoadDttm(null);
      });
  }, [metadata.id]);

  const workstream =
    metadata.workstream_label ?? workstreamDisplayName(metadata.workstream);
  const summary = snapshotSummary(metadata);

  return (
    <div className="no-print glass-panel relative animate-slide-up overflow-hidden p-6">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/5 via-transparent to-indigo-500/10" />
      <div className="relative flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="max-w-2xl">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="chip chip-active">{workstream}</span>
            <span className="chip">Trusted data domain</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-heading">{metadata.label}</h2>
          <p className="mt-2 text-sm leading-relaxed text-fg">
            {summary || snapshotSubtitle(metadata)}
          </p>
          <p className="mt-2 text-xs text-fg-muted">{snapshotDetailLine(metadata)}</p>
          {model ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                href={`/explore/${metadata.id}?tab=model`}
                className="inline-flex items-center gap-2 rounded-lg border border-indigo-400/25 bg-indigo-500/10 px-3 py-2 text-xs text-indigo-700 dark:text-indigo-100 transition hover:border-indigo-400/45"
              >
                <span className="font-medium text-indigo-700 dark:text-indigo-200">View data model →</span>
                {model.source_tables.length} source tables · {metadata.fields?.length ?? 0} fields
              </Link>
              <Link
                href={`/explore/${metadata.id}?tab=model&modelTab=joins`}
                className="inline-flex items-center gap-2 rounded-lg border border-edge-subtle bg-surface-subtle px-3 py-2 text-xs text-fg transition hover:border-edge-subtle hover:text-heading"
              >
                Join path diagram
              </Link>
            </div>
          ) : null}
          {metadata.use_case ? (
            <p className="mt-3 rounded-lg border border-edge-subtle bg-surface-subtle px-3 py-2 text-xs text-fg-muted">
              <span className="font-medium text-fg">Best for: </span>
              {metadata.use_case}
            </p>
          ) : null}
          {metadata.usage_guidance ? (
            <p className="mt-3 rounded-lg border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-100/90">
              <span className="font-medium text-amber-700 dark:text-amber-200">Data guidance: </span>
              {metadata.usage_guidance}
            </p>
          ) : null}
          {metadata.related_snapshot ? (
            <Link
              href={`/explore/${metadata.related_snapshot.id}`}
              className="mt-3 inline-flex items-center gap-2 rounded-lg border border-sky-400/20 bg-sky-500/10 px-3 py-2 text-xs text-sky-700 dark:text-sky-100 transition hover:border-sky-400/40"
            >
              <span className="font-medium text-sky-700 dark:text-sky-200">Related domain →</span>
              {metadata.related_snapshot.label}
              <span className="text-sky-600 dark:text-sky-300/70">· {metadata.related_snapshot.hint}</span>
            </Link>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-3">
          <StatPill
            label="Records in domain"
            value={rowCount != null ? formatNumber(rowCount) : "…"}
          />
          <StatPill
            label="Data refreshed"
            value={loadDttm ? formatDateTime(loadDttm) : "…"}
            accent
          />
          <StatPill label="Date filter" value={requiredDateLabel(metadata)} small />
        </div>
      </div>
    </div>
  );
}

function StatPill({
  label,
  value,
  accent,
  small,
}: {
  label: string;
  value: string;
  accent?: boolean;
  small?: boolean;
}) {
  return (
    <div
      className={`min-w-[140px] rounded-xl border px-4 py-3 ${
        accent
          ? "border-emerald-400/20 bg-emerald-500/10"
          : "border-edge-subtle bg-surface-subtle"
      }`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted">{label}</p>
      <p
        className={`mt-1 font-semibold ${accent ? "text-emerald-600 dark:text-emerald-300" : "text-heading"} ${
          small ? "text-sm" : "text-lg"
        }`}
        title={value}
      >
        {value}
      </p>
    </div>
  );
}
