"use client";

import { useEffect, useMemo, useState } from "react";
import {
  defaultDateRange,
  fetchSnapshotMetadata,
  runSnapshotQuery,
} from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/format";
import { measureDisplaysAsCurrency } from "@/lib/businessLabels";
import type { DashboardTileDef, QueryResponse } from "@/lib/types";
import { BuilderChart } from "./builder/BuilderChart";
import { useCrossFilter } from "./CrossFilterContext";

type DashboardTileProps = {
  tile: DashboardTileDef;
  days: number;
  onCrossSelect?: (field: string, value: string) => void;
  onData?: (section: { name: string; headers: string[]; rows: Record<string, unknown>[] }) => void;
};

export function DashboardTile({ tile, days, onCrossSelect, onData }: DashboardTileProps) {
  const { filter } = useCrossFilter();
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dimensionKey, setDimensionKey] = useState("");
  const [measureKey, setMeasureKey] = useState("");
  const [queryMeasureField, setQueryMeasureField] = useState("*");
  const [queryMeasureAgg, setQueryMeasureAgg] = useState("count");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [start, end] = defaultDateRange(days);
        const meta = await fetchSnapshotMetadata(tile.snapshot_id);
        const report = tile.report_id
          ? meta.premade_reports.find((r) => r.id === tile.report_id)
          : null;
        const dimensions = report?.dimensions ?? tile.dimensions ?? [];
        const measures = report?.measures ?? [
          { field: tile.measure_field ?? "*", agg: tile.measure_agg ?? "count" },
        ];
        const primaryMeasure = measures[0] ?? { field: "*", agg: "count" };
        const timeDimensions =
          tile.time_grain && meta.required_date_field
            ? [{ field: meta.required_date_field, grain: tile.time_grain }]
            : [];
        const filters: import("@/lib/types").FilterDef[] = [
          ...(meta.required_date_field
            ? [{ field: meta.required_date_field, op: "between" as const, value: [start, end] }]
            : []),
          ...(report?.filters ?? []),
        ];
        if (filter) {
          filters.push({ field: filter.field, op: "eq", value: filter.value });
        }
        const response = await runSnapshotQuery(tile.snapshot_id, {
          dimensions,
          measures,
          filters,
          time_dimensions: timeDimensions,
          limit: 500,
        });
        if (cancelled) return;
        setResult(response);
        setDimensionKey(
          timeDimensions.length ? response.columns[0] ?? "" : dimensions[0] ?? response.columns[0] ?? "",
        );
        setMeasureKey(response.columns[response.columns.length - 1] ?? "");
        setQueryMeasureField(primaryMeasure.field ?? "*");
        setQueryMeasureAgg(primaryMeasure.agg ?? "count");
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Tile failed to load");
          setResult(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tile, days, filter]);

  const total = useMemo(() => {
    if (!result || !measureKey) return null;
    return result.rows.reduce((s, r) => s + Number(r[measureKey] ?? 0), 0);
  }, [result, measureKey]);

  useEffect(() => {
    if (!result || !onData) return;
    onData({
      name: tile.title,
      headers: result.columns,
      rows: result.rows,
    });
  }, [result, tile.title, onData]);

  const chartType = (tile.chart_type as "bar" | "line" | "pie" | "horizontal") ?? "bar";
  const isTimeSeries = Boolean(tile.time_grain);
  const effectiveChart = isTimeSeries ? "line" : chartType;
  const isCurrency = measureDisplaysAsCurrency(queryMeasureField, queryMeasureAgg);

  const handleClick = (category: string) => {
    if (!dimensionKey || dimensionKey.startsWith("TD")) return;
    onCrossSelect?.(dimensionKey, category);
  };

  if (error) {
    return (
      <div className="glass-panel h-full p-4 text-sm text-amber-300">{error}</div>
    );
  }

  if (!result) {
    return <div className="glass-panel loading-shimmer h-full min-h-[220px] rounded-2xl" />;
  }

  if (tile.visual === "kpi") {
    const formatted = isCurrency ? formatCurrency(total) : formatNumber(total);
    return (
      <div className="glass-panel flex h-full flex-col justify-center p-6">
        <p className="text-xs uppercase tracking-wide text-slate-500">{tile.title}</p>
        <p className="mt-2 text-4xl font-bold text-white">{formatted ?? "—"}</p>
      </div>
    );
  }

  if (tile.visual === "table") {
    return (
      <div className="glass-panel flex h-full flex-col overflow-hidden">
        <p className="border-b border-white/10 px-4 py-2 text-sm font-medium text-white">{tile.title}</p>
        <div className="max-h-64 overflow-auto">
          <table className="min-w-full text-left text-xs">
            <thead>
              <tr>
                {result.columns.map((c) => (
                  <th key={c} className="px-3 py-2 text-slate-500">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.slice(0, 12).map((row, i) => (
                <tr key={i} className="border-t border-white/5">
                  {result.columns.map((c) => (
                    <td key={c} className="px-3 py-1.5 text-slate-200">
                      {String(row[c] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-panel flex h-full flex-col p-4">
      <p className="mb-2 text-sm font-medium text-white">{tile.title}</p>
      <div className="flex-1">
        <BuilderChart
          visual={effectiveChart}
          rows={result.rows}
          xKey={dimensionKey}
          xLabel={dimensionKey}
          series={[
            {
              key: measureKey,
              label: queryMeasureField === "*" ? "Count" : queryMeasureField,
              currency: isCurrency,
            },
          ]}
          emphasizeMax
          sortTimeSeries={isTimeSeries}
          selectedCategory={filter && filter.field === dimensionKey ? filter.value : null}
          onCategorySelect={dimensionKey.startsWith("TD") ? undefined : handleClick}
          height={240}
          emptyMessage="No chart data for this tile"
        />
      </div>
    </div>
  );
}
