"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchNlqMetricCatalog, runAnalyticsNlq, runNlqQuery } from "@/lib/api";
import { pinReportUrl } from "@/lib/pinReport";
import type { NlqMetricCatalogItem, NlqResponse } from "@/lib/types";
import { NlqAnswerCard } from "./NlqAnswerCard";

export function NlqSearchPanel({ compact }: { compact?: boolean }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NlqResponse | null>(null);
  const [catalog, setCatalog] = useState<NlqMetricCatalogItem[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>("");
  const [days, setDays] = useState(180);
  const [billCycle, setBillCycle] = useState("");
  const [customerClass, setCustomerClass] = useState("");
  const [paymentType, setPaymentType] = useState("");
  const [rateCode, setRateCode] = useState("");

  useEffect(() => {
    fetchNlqMetricCatalog()
      .then((r) => setCatalog(r.metrics))
      .catch(() => setCatalog([]));
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, NlqMetricCatalogItem[]>();
    for (const m of catalog) {
      map.set(m.category, [...(map.get(m.category) ?? []), m]);
    }
    return [...map.entries()];
  }, [catalog]);

  const runQuery = async (q: string, metricId?: string) => {
    const text = q.trim();
    if (!text && !metricId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const params = {
        metric_id: metricId || undefined,
        days,
        bill_cycle: billCycle.trim() || undefined,
        customer_class: customerClass.trim() || undefined,
        payment_type: paymentType.trim() || undefined,
        rate_code: rateCode.trim() || undefined,
      };
      try {
        const analytics = await runAnalyticsNlq(text || catalog.find((m) => m.id === metricId)?.example || "", params);
        setResult(analytics);
        if (analytics.metric_id) setSelectedMetric(analytics.metric_id);
      } catch {
        const response = await runNlqQuery(text);
        setResult(response);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run this question");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void runQuery(query, selectedMetric || undefined);
  };

  return (
    <section className={`glass-panel ${compact ? "p-4" : "p-6"}`}>
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-heading-accent">
          Ask a question
        </p>
        <h2 className={`mt-1 font-bold text-heading ${compact ? "text-lg" : "text-xl"}`}>
          Everyday utility metrics
        </h2>
        <p className="mt-1 text-sm text-fg-muted">
          Governed canvas answers for billing, payments, field work, debt, and operations — adjust
          parameters and re-run.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Total accounts billed by customer class…"
          className="input-modern w-full"
          disabled={loading}
        />
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          <label className="block text-xs text-fg-muted">
            Period (days)
            <input
              type="number"
              min={1}
              max={730}
              value={days}
              onChange={(e) => setDays(Number(e.target.value) || 30)}
              className="input-modern mt-1"
            />
          </label>
          <label className="block text-xs text-fg-muted">
            Bill cycle (optional)
            <input
              type="text"
              value={billCycle}
              onChange={(e) => setBillCycle(e.target.value)}
              className="input-modern mt-1"
              placeholder="Cycle description"
            />
          </label>
          <label className="block text-xs text-fg-muted">
            Customer class (optional)
            <input
              type="text"
              value={customerClass}
              onChange={(e) => setCustomerClass(e.target.value)}
              className="input-modern mt-1"
              placeholder="Residential, C&I…"
            />
          </label>
          <label className="block text-xs text-fg-muted">
            Payment type (optional)
            <input
              type="text"
              value={paymentType}
              onChange={(e) => setPaymentType(e.target.value)}
              className="input-modern mt-1"
              placeholder="Tender type"
            />
          </label>
          <label className="block text-xs text-fg-muted">
            Rate schedule (optional)
            <input
              type="text"
              value={rateCode}
              onChange={(e) => setRateCode(e.target.value)}
              className="input-modern mt-1"
              placeholder="Rate schedule description"
            />
          </label>
        </div>
        <button type="submit" className="btn-primary" disabled={loading || (!query.trim() && !selectedMetric)}>
          {loading ? "Running…" : "Run metric"}
        </button>
      </form>

      {!compact && grouped.length ? (
        <div className="mt-4 max-h-64 space-y-3 overflow-y-auto">
          {grouped.map(([category, items]) => (
            <div key={category}>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-fg-muted">
                {category}
              </p>
              <div className="mt-1 flex flex-wrap gap-2">
                {items.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setSelectedMetric(m.id);
                      setQuery(m.example);
                      setDays(m.default_days);
                      void runQuery(m.example, m.id);
                    }}
                    className={`chip text-left text-[11px] ${selectedMetric === m.id ? "chip-active" : ""}`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-xl border border-over bg-over-bg px-4 py-3 text-sm text-over">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="mt-4">
          <NlqAnswerCard
            result={result}
            days={days}
            onPinToDashboard={
              result.resolved_from
                ? () =>
                    router.push(
                      pinReportUrl({
                        snapshotId: result.resolved_from!,
                        title: result.metric_label ?? "NLQ metric",
                        visual: result.pin?.visual ?? "kpi",
                        measureField: result.pin?.measure_field,
                        measureAgg: result.pin?.measure_agg,
                        dimensions: result.pin?.dimensions,
                        chartType: result.pin?.visual === "chart" ? "bar" : undefined,
                        days: Number(result.metrics?.period_days ?? days),
                      }),
                    )
                : undefined
            }
          />
        </div>
      ) : null}
    </section>
  );
}
