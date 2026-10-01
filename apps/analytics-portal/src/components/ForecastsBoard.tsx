"use client";

import { useEffect, useState } from "react";
import { fetchOriTrends, type OriTrends } from "@/lib/api";
import { requestAsk } from "@/lib/assistantContext";
import { formatMonth } from "@/lib/format";
import { ORI } from "@/lib/ori";
import { oriAsk } from "@/lib/oriPanel";
import { OriForecastChart } from "@/components/OriForecastChart";
import { OriMark } from "@/components/OriMark";

/** Every Home card's forecast with its chart and how it is made: the detail Home links to. */
export function ForecastsBoard() {
  const [trends, setTrends] = useState<OriTrends | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    fetchOriTrends(signal).then(setTrends, () => signal.aborted || setTrends({ through: "", anomalies: [], forecasts: [] }));
    return () => controller.abort();
  }, []);

  const forecasts = trends?.forecasts ?? [];
  return (
    <div className="space-y-6">
      <header className="flex items-start gap-3">
        <OriMark size="h-10 w-10" />
        <div className="max-w-3xl">
          <h1 className="text-2xl font-bold text-heading">{ORI.heading}</h1>
          <p className="mt-2 text-sm leading-relaxed text-fg-muted">{ORI.forecastsIntro}</p>
          <p className="mt-2 text-sm leading-relaxed text-fg-muted">{ORI.forecastsBar}</p>
          {trends?.through ? <p className="mt-2 text-sm text-fg-muted">{ORI.forecastsThrough(formatMonth(trends.through))}</p> : null}
        </div>
      </header>

      {!trends ? (
        <p role="status" className="text-sm text-fg-muted">{ORI.thinking}</p>
      ) : forecasts.length ? (
        <>
          <div className="grid gap-6 xl:grid-cols-2">
            {forecasts.map((f) => (
              <section key={f.kpi_id} aria-label={f.headline} className="glass-panel p-6">
                <h2 className="text-base font-semibold text-heading">{f.headline}</h2>
                <p className="mt-1 text-sm tabular-nums text-fg-muted">{f.detail}</p>
                <div className="mt-4"><OriForecastChart forecast={f} height={220} /></div>
                <button type="button" className="btn-ghost mt-4 text-xs" onClick={() => requestAsk(oriAsk(f, "forecast"))}>
                  {ORI.askAbout}
                </button>
              </section>
            ))}
          </div>
          <p className="text-xs text-fg-muted">{ORI.forecastNote}</p>
        </>
      ) : (
        <p className="glass-panel p-6 text-sm text-fg-muted">{ORI.noForecasts}</p>
      )}
    </div>
  );
}
