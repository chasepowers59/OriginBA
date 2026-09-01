"use client";

/**
 * Data Quality board — the rules engine's findings as a CIS worklist.
 *
 * Organised the way an analyst triages: an at-a-glance summary strip, then findings
 * GROUPED BY SEVERITY — "Act now" first and expanded, "Review" next, and the clean
 * checks collapsed into a quiet strip at the bottom, so the page reads as "what needs
 * attention", never "what we checked". Every finding card carries the exact action to
 * take in CIS. Theme-token styled (light + dark), reference-dashboard panel language.
 */
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type DqRule = {
  id: string;
  object: string;
  severity: "action" | "review" | "info";
  title: string;
  action: string;
  columns: string[];
  rows: (string | null)[][];
  acked_rows?: (string | null)[][];
  /** Server-computed ack key per row (rule's declared entity, not blindly col 0). */
  row_keys?: string[];
  acked_row_keys?: string[];
  count: number;
  capped?: boolean;
  error?: string;
};

type DqResponse = {
  configured: boolean;
  act_now?: number;
  review?: number;
  acknowledged?: number;
  refresh_marker?: string;
  rules: DqRule[];
  error?: string;
};

const SEV = {
  action: { label: "ACT NOW", pill: "bg-red-500/15 text-red-600 ring-1 ring-red-500/30 dark:text-red-300" },
  review: { label: "REVIEW", pill: "bg-amber-500/15 text-amber-700 ring-1 ring-amber-500/30 dark:text-amber-300" },
  info: { label: "INFO", pill: "bg-chip text-fg-muted ring-1 ring-edge-subtle" },
} as const;

export function DataQualityBoard() {
  const [data, setData] = useState<DqResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const reload = () =>
    apiGet<DqResponse>("/dq/findings")
      .then(setData)
      .catch((e) => setErr(String(e)));
  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const mark = async (key: string, done: boolean) => {
    await apiPost(done ? "/dq/ack" : "/dq/unack", { key });
    await reload();
  };

  const rules = useMemo(() => {
    if (!data?.rules) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return data.rules;
    return data.rules.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        r.object.toLowerCase().includes(q) ||
        r.id.includes(q),
    );
  }, [data, filter]);

  // Triage grouping: anything with findings (or a rule error) surfaces under its
  // severity; clean rules collapse to the quiet strip at the bottom.
  const groups = useMemo(() => {
    const open = (sev: DqRule["severity"]) =>
      rules.filter((r) => r.severity === sev && (r.count > 0 || r.error));
    return {
      action: open("action"),
      review: open("review"),
      info: rules.filter((r) => r.severity === "info" && (r.count > 0 || r.error)),
      clean: rules.filter((r) => r.count === 0 && !r.error),
    };
  }, [rules]);

  if (err) {
    return (
      <div className="glass-panel border-red-400/30 bg-red-500/10 p-6 text-sm text-red-600 dark:text-red-300">
        Could not load data-quality findings: {err}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="animate-pulse space-y-3 p-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="loading-shimmer h-16 rounded-xl" />
        ))}
      </div>
    );
  }
  if (!data.configured) {
    return (
      <div className="glass-panel p-8 text-center text-sm text-fg-muted">
        No reporting warehouse is configured for this organization, so the
        data-quality rules have nothing to run against.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sky-600 dark:text-sky-400">
            Data quality
          </p>
          <h1 className="portal-heading mt-1 text-2xl font-bold">Worklist</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Rules run against this tenant&apos;s data; every finding says exactly where
            to act in CIS.
            {data.refresh_marker ? (
              <span className="text-fg-subtle"> · data as of {data.refresh_marker}</span>
            ) : null}
          </p>
        </div>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter rules…"
          aria-label="Filter rules"
          className="input-modern w-56"
        />
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <SummaryCard label="Act now" value={data.act_now ?? 0} tone="red" glyph="!" />
        <SummaryCard label="Review" value={data.review ?? 0} tone="amber" glyph="?" />
        <SummaryCard label="Rules run" value={data.rules.length} tone="blue" glyph="✓" />
        <SummaryCard label="Marked done" value={data.acknowledged ?? 0} tone="green" glyph="✔" />
      </div>

      <Section
        title="Act now"
        subtitle="Findings that block or corrupt downstream work — fix these in CIS first."
        rules={groups.action}
        defaultOpen
        onMark={mark}
        emptyNote="Nothing needs immediate action."
      />
      <Section
        title="Review"
        subtitle="Worth a look — likely configuration drift or unusual data."
        rules={groups.review}
        onMark={mark}
        emptyNote="Nothing waiting for review."
      />
      {groups.info.length ? (
        <Section title="Informational" rules={groups.info} onMark={mark} />
      ) : null}

      {groups.clean.length ? (
        <details className="glass-panel px-4 py-3">
          <summary className="cursor-pointer text-sm text-fg-muted">
            <span className="font-medium text-emerald-600 dark:text-emerald-400">
              {groups.clean.length} checks clean
            </span>{" "}
            — everything these rules watch is in order
          </summary>
          <ul className="mt-3 grid gap-1 text-xs text-fg-muted sm:grid-cols-2">
            {groups.clean.map((r) => (
              <li key={r.id} className="flex items-center gap-2">
                <span aria-hidden className="text-emerald-500">✓</span>
                <span>{r.title}</span>
                <span className="text-fg-subtle">· {r.object}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function Section({
  title,
  subtitle,
  rules,
  defaultOpen = false,
  onMark,
  emptyNote,
}: {
  title: string;
  subtitle?: string;
  rules: DqRule[];
  defaultOpen?: boolean;
  onMark: (key: string, done: boolean) => Promise<void>;
  emptyNote?: string;
}) {
  if (!rules.length) {
    return emptyNote ? (
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-fg-subtle">{title}</h2>
        <p className="mt-1 text-sm text-fg-muted">
          <span aria-hidden className="mr-1 text-emerald-500">✓</span>
          {emptyNote}
        </p>
      </div>
    ) : null;
  }
  return (
    <section>
      <h2 className="text-sm font-semibold uppercase tracking-wider text-fg-subtle">{title}</h2>
      {subtitle ? <p className="mt-0.5 text-xs text-fg-muted">{subtitle}</p> : null}
      <div className="mt-3 space-y-3">
        {rules.map((r) => (
          <RuleCard key={r.id} rule={r} defaultOpen={defaultOpen} onMark={onMark} />
        ))}
      </div>
    </section>
  );
}

function RuleCard({
  rule: r,
  defaultOpen,
  onMark,
}: {
  rule: DqRule;
  defaultOpen: boolean;
  onMark: (key: string, done: boolean) => Promise<void>;
}) {
  const sev = SEV[r.severity];
  return (
    <details open={defaultOpen && r.count > 0} className="glass-panel overflow-hidden">
      <summary className="flex cursor-pointer flex-wrap items-center gap-3 px-4 py-3">
        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold tracking-wide ${sev.pill}`}>
          {sev.label}
        </span>
        <span className="font-medium text-heading">{r.title}</span>
        <span className="ml-auto flex items-center gap-2 text-sm">
          {r.error ? (
            <span className="text-red-500">rule error</span>
          ) : (
            <span className="rounded-full bg-chip px-2 py-0.5 text-xs font-semibold tabular-nums text-fg">
              {r.count}
              {r.capped ? "+" : ""}
            </span>
          )}
          <span className="font-mono text-xs text-fg-subtle">{r.object}</span>
        </span>
      </summary>
      <div className="border-t border-edge-subtle px-4 py-3">
        <p className="mb-3 rounded-lg border-l-2 border-brand bg-surface-subtle px-3 py-2 text-sm text-fg">
          <span className="font-semibold text-heading">What to do: </span>
          {r.action}
        </p>
        {r.error ? (
          <p className="text-sm text-red-500">rule error: {r.error}</p>
        ) : r.count === 0 ? (
          <p className="text-sm text-fg-muted">No findings — clean.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr>
                  <th className="border-b border-edge-subtle px-2 py-1.5" />
                  {r.columns.map((c) => (
                    <th
                      key={c}
                      className="whitespace-nowrap border-b border-edge-subtle px-2 py-1.5 text-left font-semibold text-fg-muted"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {r.rows.map((row, i) => (
                  <tr key={i} className="border-b border-edge-subtle/60 hover:bg-chip">
                    <td className="px-2 py-1">
                      <button
                        onClick={() => onMark(r.row_keys?.[i] ?? `${r.id}|${row[0]}`, true)}
                        title="Mark done until the next data refresh"
                        className="rounded border border-emerald-500/50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600 hover:bg-emerald-500/10 dark:text-emerald-400"
                      >
                        Done
                      </button>
                    </td>
                    {row.map((v, j) => (
                      <td key={j} className="whitespace-nowrap px-2 py-1 text-fg">
                        {v ?? ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {r.capped && <p className="mt-1 text-xs text-fg-subtle">showing first 100</p>}
          </div>
        )}
        {(r.acked_rows?.length ?? 0) > 0 && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-fg-muted">
              {r.acked_rows!.length} marked done (hidden until the next data refresh)
            </summary>
            <ul className="mt-1 space-y-0.5 text-xs text-fg-muted">
              {r.acked_rows!.map((row, i) => (
                <li key={i} className="flex items-center gap-2">
                  <button
                    onClick={() => onMark(r.acked_row_keys?.[i] ?? `${r.id}|${row[0]}`, false)}
                    className="rounded border border-edge px-1.5 py-0.5 text-[10px] hover:bg-chip"
                  >
                    Undo
                  </button>
                  <span className="line-through">
                    {row.filter(Boolean).slice(0, 4).join(" · ")}
                  </span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </details>
  );
}

function SummaryCard({
  label,
  value,
  tone,
  glyph,
}: {
  label: string;
  value: number;
  tone: "red" | "amber" | "green" | "blue";
  glyph: string;
}) {
  const tones: Record<string, { text: string; chip: string }> = {
    red: { text: "text-red-600 dark:text-red-400", chip: "bg-red-500" },
    amber: { text: "text-amber-600 dark:text-amber-400", chip: "bg-amber-500" },
    green: { text: "text-emerald-600 dark:text-emerald-400", chip: "bg-emerald-500" },
    blue: { text: "text-brand", chip: "bg-brand" },
  };
  const t = tones[tone];
  return (
    <div className="glass-panel flex items-center gap-3 px-4 py-3">
      <span
        aria-hidden
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold text-white ${t.chip}`}
      >
        {glyph}
      </span>
      <div>
        <div className={`text-2xl font-bold tabular-nums leading-none ${t.text}`}>{value}</div>
        <div className="mt-1 text-xs text-fg-muted">{label}</div>
      </div>
    </div>
  );
}
