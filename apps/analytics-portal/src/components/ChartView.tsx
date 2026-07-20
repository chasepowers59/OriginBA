"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency, formatNumber } from "@/lib/format";
import { ChartTooltipContent, chartTooltipWrapperStyle } from "./ChartTooltip";

const COLORS = ["#38bdf8", "#818cf8", "#22d3ee", "#34d399", "#a78bfa", "#fbbf24"];

type ChartViewProps = {
  chartType: "bar" | "line" | "pie" | "horizontal";
  rows: Record<string, unknown>[];
  dimensionKey: string;
  measureKey: string;
  measureLabel?: string;
  isCurrency?: boolean;
  selectedCategory?: string | null;
  onCategoryClick?: (category: string) => void;
  sortTimeSeries?: boolean;
};

export function ChartView({
  chartType,
  rows,
  dimensionKey,
  measureKey,
  measureLabel = "Value",
  isCurrency = false,
  selectedCategory = null,
  onCategoryClick,
  sortTimeSeries = false,
}: ChartViewProps) {
  const formatValue = (v: number) => (isCurrency ? formatCurrency(v) : formatNumber(v));
  const tooltip = (
    <ChartTooltipContent measureLabel={measureLabel} isCurrency={isCurrency} />
  );
  const data = useMemo(() => {
    const mapped = rows.map((row) => ({
      name: String(row[dimensionKey] ?? "Unknown").slice(0, 40),
      fullName: String(row[dimensionKey] ?? "Unknown"),
      value: Number(row[measureKey] ?? 0),
    }));
    if (sortTimeSeries) {
      return [...mapped].sort((a, b) => String(a.fullName).localeCompare(String(b.fullName)));
    }
    return mapped;
  }, [rows, dimensionKey, measureKey, sortTimeSeries]);

  const handleClick = (payload: { fullName?: string }) => {
    if (onCategoryClick && payload.fullName) {
      onCategoryClick(payload.fullName);
    }
  };

  const barFill = (fullName: string, index: number) => {
    if (selectedCategory && fullName === selectedCategory) return "#fbbf24";
    return COLORS[index % COLORS.length];
  };

  if (!data.length) {
    return (
      <div className="flex h-72 items-center justify-center text-slate-500">
        No chart data for this selection
      </div>
    );
  }

  if (chartType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={110}
            paddingAngle={2}
            label={({ name, percent }) =>
              `${name.slice(0, 12)} ${((percent ?? 0) * 100).toFixed(0)}%`
            }
            onClick={(_, index) => handleClick(data[index] ?? {})}
            style={{ cursor: onCategoryClick ? "pointer" : "default" }}
          >
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={barFill(entry.fullName, index)}
                stroke={selectedCategory === entry.fullName ? "#fbbf24" : "transparent"}
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip
            content={tooltip}
            wrapperStyle={chartTooltipWrapperStyle}
            cursor={{ fill: "rgba(255,255,255,0.06)" }}
          />
          <Legend wrapperStyle={{ color: "#94a3b8", fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "horizontal") {
    return (
      <ResponsiveContainer width="100%" height={Math.max(280, data.length * 36)}>
        <BarChart data={data} layout="vertical" barCategoryGap="16%">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => formatValue(v)} />
          <YAxis
            type="category"
            dataKey="name"
            width={120}
            tick={{ fontSize: 11, fill: "#64748b" }}
          />
          <Tooltip content={tooltip} wrapperStyle={chartTooltipWrapperStyle} cursor={{ fill: "rgba(255,255,255,0.06)" }} />
          <Bar
            dataKey="value"
            radius={[0, 6, 6, 0]}
            onClick={(payload) => handleClick(payload as { fullName?: string })}
            style={{ cursor: onCategoryClick ? "pointer" : "default" }}
          >
            {data.map((entry, index) => (
              <Cell key={index} fill={barFill(entry.fullName, index)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "line") {
    return (
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: "#64748b" }}
            interval={0}
            angle={-20}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => formatValue(v)} />
          <Tooltip content={tooltip} wrapperStyle={chartTooltipWrapperStyle} cursor={{ stroke: "rgba(56,189,248,0.4)", strokeWidth: 1 }} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#38bdf8"
            strokeWidth={2}
            fill="url(#lineGrad)"
            onClick={(payload) => handleClick(payload as { fullName?: string })}
            style={{ cursor: onCategoryClick ? "pointer" : "default" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} barCategoryGap="20%">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: "#64748b" }}
          interval={0}
          angle={-20}
          textAnchor="end"
          height={60}
        />
        <YAxis tick={{ fontSize: 11, fill: "#64748b" }} tickFormatter={(v) => formatValue(v)} />
        <Tooltip content={tooltip} wrapperStyle={chartTooltipWrapperStyle} cursor={{ fill: "rgba(255,255,255,0.06)" }} />
        <Bar
          dataKey="value"
          radius={[6, 6, 0, 0]}
          onClick={(payload) => handleClick(payload as { fullName?: string })}
          style={{ cursor: onCategoryClick ? "pointer" : "default" }}
        >
          {data.map((entry, index) => (
            <Cell key={index} fill={barFill(entry.fullName, index)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
