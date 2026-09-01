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
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary via-transparent to-accent-2" />
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
                className="inline-flex items-center gap-2 rounded-lg border text-chart-2 text-chart-2 px-3 py-2 text-xs text-chart-2 dark:text-chart-2 transition hover:text-chart-2"
              >
                <span className="font-medium text-chart-2 dark:text-chart-2">View data model →</span>
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
            <p className="mt-3 rounded-lg border border-warn bg-warn-bg px-3 py-2 text-xs text-warn">
              <span className="font-medium text-warn">Data guidance: </span>
              {metadata.usage_guidance}
            </p>
          ) : null}
          {metadata.related_snapshot ? (
            <Link
              href={`/explore/${metadata.related_snapshot.id}`}
              className="mt-3 inline-flex items-center gap-2 rounded-lg border border-edge bg-band px-3 py-2 text-xs text-primary transition hover:border-edge"
            >
              <span className="font-medium text-primary">Related domain →</span>
              {metadata.related_snapshot.label}
              <span className="text-primary">· {metadata.related_snapshot.hint}</span>
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
 ? "border-ok bg-ok-bg"
 : "border-edge-subtle bg-surface-subtle"
 }`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wider text-fg-muted">{label}</p>
      <p
        className={`mt-1 font-semibold ${accent ? "text-ok" : "text-heading"} ${
 small ? "text-sm" : "text-lg"
 }`}
        title={value}
      >
        {value}
      </p>
    </div>
  );
}
