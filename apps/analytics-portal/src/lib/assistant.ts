/**
 * The assistant conversation as the browser holds it: what the user asked, what came back,
 * and the model-facing thread the API hands back for a follow-up.
 */
import { formatCellValue, isIdentifierColumn } from "@/lib/format";
import { measureIsCurrency } from "@/lib/businessLabels";
import { suggestChart, type ChartSuggestion } from "@/lib/databaseChartUtils";
import type { NlqResponse, AssistantSpend, CanvasIntegrity, AssistantMessage, AssistantResponse, IntegrityOverview } from "@/lib/types";

export type Turn =
  | { role: "user"; text: string }
  | { role: "assistant"; response: AssistantResponse }
  | { role: "governed"; question: string; result: NlqResponse }
  | { role: "error"; text: string };

/**
 * Whether a question tries the governed metrics before the model. A vetted metric answers
 * "how much / how many" at no token cost with the definition the dashboards use; a
 * why-question needs reasoning, and a question about the page on screen needs its context.
 */
export function tryGovernedFirst(question: string, aboutThePage: boolean): boolean {
  return !aboutThePage && !/^\s*(why|explain|what caused|how come)\b/i.test(question);
}

/** The SQL workspace handoff: one key, the last query the reader chose to open. */
export const WORKSPACE_SQL_KEY = "portal.assistant.sql";

export function appendTurns(turns: Turn[], question: string, response: AssistantResponse): Turn[] {
  return [...turns, { role: "user", text: question }, { role: "assistant", response }];
}

/** The thread to send with the next question: the API's own, from the last answer. */
export function threadFor(turns: Turn[]): AssistantMessage[] {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    const t = turns[i];
    if (t.role === "assistant") return t.response.thread;
  }
  return [];
}

/** "3 steps · 2 queries · 1,240 tokens (22,000 cached)" -- the footer under an answer.
 *  Cached reads are the bulk of a question's tokens and cost a tenth; they are shown apart
 *  so the number a reader sees tracks the bill. */
export function summarise(r: AssistantResponse): string {
  const tokens = (r.usage?.input_tokens ?? 0) + (r.usage?.output_tokens ?? 0);
  const cached = (r.usage?.cache_read_input_tokens ?? 0) + (r.usage?.cache_creation_input_tokens ?? 0);
  const parts = [
    `${r.steps.length} step${r.steps.length === 1 ? "" : "s"}`,
    `${r.queries.length} ${r.queries.length === 1 ? "query" : "queries"}`,
  ];
  if (tokens) parts.push(`${tokens.toLocaleString()} tokens${cached ? ` (${cached.toLocaleString()} cached)` : ""}`);
  return parts.join(" · ");
}

/**
 * A cell for the result table, formatted the way every other canvas cell in the portal is:
 * identifiers and years verbatim, dates as dates, numbers with separators. The first real
 * result rendered a "Year" column as "2,026" (Ellensburg, 2026-09-15); a year is a label.
 */
export function cell(v: unknown, column?: string): string {
  if (column && (isIdentifierColumn(column) || /\byear\b/i.test(column))) return v == null ? "—" : String(v);
  if (column && measureIsCurrency(column)) {
    const money = moneyCell(v);
    if (money) return money;
  }
  return formatCellValue(v, { columnId: column });
}

/** Cents always, so a column lines up; a unit price keeps the precision it was stored at. */
function moneyCell(v: unknown): string | null {
  const raw = typeof v === "number" ? String(v) : typeof v === "string" ? v.trim() : "";
  const m = raw.match(/^-?\d+(?:\.(\d+))?$/);
  if (!m) return null;
  const decimals = Math.min(Math.max(m[1]?.length ?? 0, 2), 6);
  return Number(raw).toLocaleString("en-US", {
    style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: decimals,
  });
}

/** One line per canvas a query read: what it was proven against and how old the build is. */
export function integrityLabel(i: CanvasIntegrity): string {
  const age = i.canvas_as_of ? ageLabel(i.canvas_as_of) : null;
  const built = age ? ` · built ${age}` : "";
  if (i.verdict === "unavailable") return `${i.canvas}: no verification on record`;
  if (i.verdict === "not covered") return `${i.canvas}: not covered by a parity check${built}`;
  return `${i.canvas}: ${i.verdict === "proven" ? "proven" : "differences"} (${i.summary})${built}`;
}

export function ageLabel(iso: string, now: Date = new Date()): string {
  const h = Math.floor((now.getTime() - new Date(iso).getTime()) / 3_600_000);
  if (h < 1) return "within the hour";
  if (h < 48) return `${h} h ago`;
  return `${Math.floor(h / 24)} days ago`;
}

/** The panel's standing line: how current the canvases are and how many are proven. */
export function integrityHeadline(o: IntegrityOverview, now: Date = new Date()): string {
  if (!o.available) return "No verification on record for this organization yet.";
  const proven = o.canvases.filter((c) => c.verdict === "proven").length;
  const built = o.canvas_as_of ? `Canvases built ${ageLabel(o.canvas_as_of, now)}` : "Canvas build time unknown";
  return `${built} · ${proven} of ${o.canvases.length} canvases proven against the source database`;
}

/** "Today: 44,464 tokens (2 questions) of a 2,000,000 budget" -- what the organization has spent. */
export function spendLabel(s: AssistantSpend): string {
  const q = `${s.questions} question${s.questions === 1 ? "" : "s"}`;
  const base = `Today: ${s.today.toLocaleString()} tokens (${q})`;
  return s.budget ? `${base} of a ${s.budget.toLocaleString()} budget` : base;
}

/** Questions a new user can start from, each answerable from the canvases. */
export const STARTER_QUESTIONS = [
  "How much was billed by bill cycle in the last 90 days?",
  "Which accounts owe the most more than 90 days past due?",
  "How were payments taken last month, by tender type?",
  "Which batch jobs ended in error in the last week?",
];

const MAX_CHART_ROWS = 50;
const PERIOD_COLUMN = /\b(year|quarter|month|week|period)\b/i;

/**
 * A chart for a query result when one reads better than the table: a label column against
 * a number, a handful to a few dozen rows. A single figure or a long detail list stays a table.
 */
export function resultChart(q: { columns: string[]; rows: unknown[][] }): ChartSuggestion | null {
  if (q.rows.length < 2 || q.rows.length > MAX_CHART_ROWS) return null;
  const records = q.rows.map((r) => Object.fromEntries(q.columns.map((c, i) => [c, r[i]])));
  // A year or month is the label axis even when it is stored as a number, which the
  // general suggestion reads as a measure.
  const period = q.columns.find((c) => PERIOD_COLUMN.test(c));
  const measure = period && q.columns.find((c, i) => c !== period && !isIdentifierColumn(c)
    && q.rows.every((r) => r[i] == null || Number.isFinite(Number(r[i]))));
  const s = period && measure
    ? { dimensionKey: period, measureKey: measure, chartType: "line" as const, sortTimeSeries: true,
        isCurrency: false, label: measure }
    : suggestChart(q.columns, records);
  return s ? { ...s, isCurrency: measureIsCurrency(s.measureKey) } : null;
}
