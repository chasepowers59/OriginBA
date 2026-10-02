"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchNlqMetricCatalog, runAnalyticsNlq } from "@/lib/api";
import { pinReportUrl } from "@/lib/pinReport";
import { groupMetrics } from "@/lib/nlqMetrics";
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

  const grouped = useMemo(() => groupMetrics(catalog), [catalog]);

  const chooseMetric = (m: NlqMetricCatalogItem) => {
    setSelectedMetric(m.id);
    setQuery(m.example);
    setDays(m.default_days);
    void runQuery(m.example, m.id);
  };

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
      const analytics = await runAnalyticsNlq(text || catalog.find((m) => m.id === metricId)?.example || "", params);
      setResult(analytics);
      if (analytics.metric_id) setSelectedMetric(analytics.metric_id);
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
          Vetted metrics
        </p>
        <h2 className={`mt-1 font-bold text-heading ${compact ? "text-lg" : "text-xl"}`}>
          Everyday utility metrics
        </h2>
        <p className="mt-1 text-sm text-fg-muted">
          The same figures the dashboards use, for billing, payments, field work, debt and
          operations. Set the filters and run it again.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {grouped.length ? (
          // Folded under Ori, the form showed a free-text box and a disabled button with no way to
          // see the metrics it answers (2026-10-02): the picker lists them wherever the form is.
          <select
            aria-label="Choose a metric"
            className="input-modern w-full"
            value={selectedMetric}
            disabled={loading}
            onChange={(e) => {
              const m = catalog.find((x) => x.id === e.target.value);
              if (m) chooseMetric(m);
            }}
          >
            <option value="">Choose a metric…</option>
            {grouped.map(({ category, items }) => (
              <optgroup key={category} label={category}>
                {items.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
              </optgroup>
            ))}
          </select>
        ) : null}
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
          {grouped.map(({ category, items }) => (
            <div key={category}>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-fg-muted">
                {category}
              </p>
              <div className="mt-1 flex flex-wrap gap-2">
                {items.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => chooseMetric(m)}
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
