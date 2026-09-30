/**
 * UI-16 (issues log, Decisions): ONE format set, used everywhere. The locale is fixed
 * because the decision fixes the format -- "Sep 1, 2026", "$1,234.56" -- not the browser.
 */
const LOCALE = "en-US";
const USD = { style: "currency", currency: "USD" } as const;

/** From this magnitude on, a chart axis or KPI headline reads compact (12.3K). */
const COMPACT_FROM = 10_000;

/**
 * A missing value is NOT zero: Number(null) and Number("") are both 0, so a NULL
 * amount rendered as a real "$0" while undefined rendered "—". A SUM over zero
 * matching rows IS null, and the backend distinguishes that state deliberately
 * (kpi_runner.empty_window_note), so erasing it here turns "no data" into a business
 * fact the reader will act on.
 */
function toNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/**
 * Money: "$1,234.56", "-$12,071.26". Cents always, so a column lines up; a unit price
 * keeps the precision it was stored at (up to 6), while float noise and a computed
 * average's tail round to cents.
 */
export function formatCurrency(value: unknown): string {
  const n = toNumber(value);
  if (n == null) return "—";
  const stored = String(value).trim().match(/\.(\d*?)0*$/)?.[1].length ?? 0;
  return n.toLocaleString(LOCALE, {
    ...USD,
    minimumFractionDigits: 2,
    maximumFractionDigits: stored > 6 ? 2 : Math.max(2, stored),
  });
}

/** Every digit, with separators: tables, sentences and tooltips. */
export function formatNumber(value: unknown): string {
  const n = toNumber(value);
  return n == null ? "—" : n.toLocaleString(LOCALE, { maximumFractionDigits: 2 });
}

function compact(n: number, currency: boolean): string {
  return n.toLocaleString(LOCALE, {
    notation: "compact",
    maximumSignificantDigits: 3,
    ...(currency ? USD : {}),
  });
}

/**
 * A KPI headline: compact from 10,000 ("12.3K", "-$9.5K"), every digit below it.
 * Compact belongs on chart axes and headlines only; a table never compacts.
 */
export function formatCompact(value: unknown, { currency = false } = {}): string {
  const n = toNumber(value);
  if (n == null) return "—";
  if (Math.abs(n) < COMPACT_FROM) return currency ? formatCurrency(n) : formatNumber(n);
  return compact(n, currency);
}

const STEP_RATIOS = [1, 2, 2.5, 5];

/**
 * Axis ticks from min(0, lo) to max(0, hi) in a round step -- 1, 2, 2.5 or 5 x 10^n --
 * at most `maxTicks` of them. Recharts' own steps are any multiple of 0.05 x 10^n,
 * which put "$5.5K" on an axis. `zero: false` fits a trend line's axis to its data (a bar
 * always starts at zero); a labelled axis is what keeps that honest.
 */
export function niceTicks(lo: number, hi: number, maxTicks = 6, { zero = true } = {}): number[] {
  const fit = !zero && hi > lo;
  const from = fit ? lo : Math.min(0, lo);
  const to = fit ? hi : Math.max(0, hi);
  const intervals = maxTicks - 1;
  for (let power = 10 ** Math.floor(Math.log10((to - from || 1) / intervals)); ; power *= 10) {
    for (const ratio of STEP_RATIOS) {
      const step = Number((ratio * power).toPrecision(12));
      const first = Math.floor(from / step + 1e-9);
      const last = Math.ceil(to / step - 1e-9);
      if (last - first <= intervals) {
        // + 0 turns -0 into 0, which would otherwise print "-0"
        return Array.from({ length: last - first + 1 }, (_, i) => Number(((first + i) * step).toPrecision(12)) + 0);
      }
    }
  }
}

export type ValueAxis = { ticks: number[]; domain: [number, number]; format: (v: number) => string };

/**
 * A chart's value axis: round ticks covering every value, and zero unless `zero: false`
 * (pass stack totals for a stacked chart), labelled alike -- all compact when the axis
 * reaches 10,000, none otherwise. A tick is a round number, so money on an axis carries
 * no cents.
 */
export function valueAxis(values: number[], { currency = false, zero = true, maxTicks = 6 } = {}): ValueAxis {
  const finite = values.filter(Number.isFinite);
  const lo = finite.reduce((a, b) => Math.min(a, b), Infinity);
  const hi = finite.reduce((a, b) => Math.max(a, b), -Infinity);
  const ticks = niceTicks(lo, hi, maxTicks, { zero });
  const compactAll = ticks.some((t) => Math.abs(t) >= COMPACT_FROM);
  const format = (v: number) =>
    compactAll
      ? compact(v, currency)
      : v.toLocaleString(LOCALE, {
          maximumFractionDigits: 2,
          ...(currency ? { ...USD, minimumFractionDigits: 0 } : {}),
        });
  return { ticks, domain: [ticks[0], ticks[ticks.length - 1]], format };
}

export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

/** Whole words naming an identifier, matched as TOKENS rather than suffixes. */
const IDENTIFIER_WORDS = new Set(["ID", "IDS", "KEY", "KEYS", "PATH", "GUID", "UUID"]);

/** Words meaning this is a tally or a state, whatever identifier word sits beside it. */
const NOT_IDENTIFIER_WORDS = new Set([
  "COUNT", "COUNTS", "REQUIRED", "FLAG", "TOTAL", "AMOUNT", "PERCENT", "PCT",
]);

/** IDs and natural keys should stay literal — never compact to 90.47M-style labels. */
export function isIdentifierColumn(columnId?: string): boolean {
  if (!columnId) return false;
  const upper = columnId.toUpperCase();
  // Suffixes alone missed names whose shape is not a suffix. Found by running REAL
  // Ellensburg values through this: "Hierarchy Path" rendered '498295347400' as
  // "498,295,347,400" and "Drill Key Values" did the same -- both round-trip, so the
  // round-trip guard in formatCellValue cannot see them either. Token matching also
  // catches "Adjustment ID (Pay Seg)", which endsWith(" ID") missed over a
  // parenthetical. The negative set keeps "Drill Key Count" (a measure that wants its
  // separators) and "Key Required" (a flag) out.
  const words = upper.split(/[^A-Z0-9]+/).filter(Boolean);
  if (!words.some((w) => NOT_IDENTIFIER_WORDS.has(w))
      && words.some((w) => IDENTIFIER_WORDS.has(w))) {
    return true;
  }
  // Two naming worlds: raw CISADM columns from the SQL workspace (ACCT_ID,
  // TENDER_TYPE_CD) and the canvases' Title Case ("Account ID", "Bill Cycle Code",
  // "Meter Badge Number"). An identifier rendered with thousand separators
  // ("1,358,301,387") is corrupted for copy/paste and lookups, so this guard must
  // cover both.
  // "Count" columns are measures, not identifiers -- only " NUMBER" matches here.
  return (
    upper.endsWith("_ID") ||
    upper.endsWith(" ID") ||
    upper === "ID" ||
    upper.endsWith("_KEY") ||
    upper.includes("NATURAL_KEY") ||
    upper.endsWith("_NBR") ||
    upper.endsWith("_CD") ||
    upper.endsWith(" CODE") ||
    upper.endsWith(" NUMBER")
  );
}

/**
 * Render a flag column as a state, never a raw 1/0 or bare true/false.
 *
 * A flag reaches the UI in several encodings depending on the backend: a genuine
 * boolean on the Postgres/Supabase path, a NUMBER(1) 1/0 on the Oracle path, or a
 * Y/N/T/F string. All of them mean the same thing on a BI surface, so normalise to
 * one readable pair. Undecidable values fall through to their string form.
 */
export function formatBoolean(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "True" : "False";
  const s = String(value).trim().toLowerCase();
  if (["1", "t", "true", "y", "yes"].includes(s)) return "True";
  if (["0", "f", "false", "n", "no"].includes(s)) return "False";
  return String(value);
}

/** Table / preview cells: every digit, never compact (UI-16); a measure rounds to 2 decimals. */
export function formatCellValue(
  value: unknown,
  options?: { columnId?: string; isMeasure?: boolean; asCurrency?: boolean; isBoolean?: boolean },
): string {
  if (value == null || value === "") return "—";
  // Flags render as a state. A native JS boolean is always a flag (Postgres path);
  // a NUMBER(1) 1/0 flag is indistinguishable from an integer by value alone, so the
  // caller declares it via isBoolean from the column's declared type (Oracle path).
  if (options?.isBoolean || typeof value === "boolean") return formatBoolean(value);
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    return isCalendarDate(value, options?.columnId) ? formatDate(value.slice(0, 10)) : formatDateTime(value);
  }
  if (options?.asCurrency) return formatCurrency(value);
  if (isIdentifierColumn(options?.columnId)) return String(value);
  const n = Number(value);
  if (!Number.isFinite(n) || !String(value).match(/^-?\d/)) return String(value);
  // A STRING is only rendered as a number when doing so LOSES NOTHING. The name-based
  // guard above cannot cover this: measured across all 958 text columns in
  // originba_v2_demo25, eight hold leading-zero digit strings under names that share no
  // suffix -- rpt_gl."GL Account", rpt_characteristics."Ad Hoc Value",
  // rpt_asset_location."Hierarchy Path", rpt_todo."Drill Key Values" among them. The
  // worst rendered '01000123923000000000000' as "1,000,123,923,000,000,000,000": the
  // key field of a FINANCE canvas, past 2^53, so the leading zero AND the trailing
  // digits were wrong. Lossless is: a plain decimal, no leading zero, integer part
  // within 2^53 -- formatted at ITS OWN scale, because the API serializes NUMERIC
  // columns at the column scale and a strict String(n) round-trip left "-1265.00" raw
  // beside a formatted "-1,561.11" in the same row.
  if (typeof value === "string") {
    const m = value.trim().match(/^-?(0|[1-9]\d*)(?:\.(\d+))?$/);
    if (!m || !Number.isSafeInteger(Math.trunc(n))) return value;
    if (options?.isMeasure) return formatNumber(n);
    const scale = Math.min(m[2]?.length ?? 0, 6);
    return n.toLocaleString(LOCALE, { minimumFractionDigits: scale, maximumFractionDigits: scale });
  }
  if (options?.isMeasure) return formatNumber(n);
  return n.toLocaleString(LOCALE, { maximumFractionDigits: 6 });
}

/**
 * Whether a timestamp in this column is a calendar date, so it shows no time (UI-16:
 * "12:00 AM" never appears on a date). "X Date" is a date by the reporting layer's
 * naming contract and "X Date/Time" the instant; CISADM says "_DT" and "_DTTM". CISADM
 * DATE columns land as timestamps and rendered "Jul 21, 2026, 12:00 AM" on every
 * canvas. Under any other name a zone-less local midnight is a date too -- a time
 * bucket ("TD0") or a DATE column the name cannot vouch for -- unless the column calls
 * itself a date-time.
 */
function isCalendarDate(raw: string, columnId = ""): boolean {
  if (/\bDate$|_DT$/i.test(columnId)) return true;
  if (/Date\/Time|\bTime\b|_DTTM$/i.test(columnId)) return false;
  return /^\d{4}-\d{2}-\d{2}(?:[T ]00:00(?::00(?:\.0+)?)?)?$/.test(raw);
}

/**
 * "2026-09-20 00:00:00" -- Python's str() of a timestamp, which the Data Quality
 * worklist sends -- parses on Chrome and is Invalid Date on Safari; the ISO "T" form
 * parses everywhere. Anything else passes through untouched.
 */
export function isoDateTimeString(raw: string): string {
  return raw.replace(/^(\d{4}-\d{2}-\d{2}) (\d)/, "$1T$2");
}

/** YYYY-MM-DD with nothing after it: a calendar date, not an instant. */
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;

const DAY: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", year: "numeric" };

/**
 * A plain date stays on its own calendar day; a timestamp is read in the viewer's clock.
 *
 * `new Date("2026-09-02")` is specified to parse as UTC MIDNIGHT, while
 * `new Date("2026-09-02T00:00:00")` parses as local midnight. Feeding the first form to
 * toLocaleString rendered every date-only value as THE PREVIOUS DAY west of UTC, with a
 * time nobody supplied: "2026-09-02" came out "Sep 1, 2026, 06:00 PM". The API
 * serializes a Postgres DATE column with `date.isoformat()`, which is exactly that
 * form, so a bill dated the 1st displayed the 31st on every canvas that has one.
 *
 * Found by running real Ellensburg values through the formatter. Bug class 12 a third
 * time, after report_schedules and the date-range builders: a business date belongs in
 * the utility's own calendar, never as a UTC instant.
 */
function parseDate(value: unknown): Date | null {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const raw = String(value);
  if (DATE_ONLY_RE.test(raw)) {
    const [y, m, d] = raw.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  const d = new Date(isoDateTimeString(raw));
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "Sep 1, 2026". */
export function formatDate(value: unknown): string {
  if (!value) return "—";
  return parseDate(value)?.toLocaleDateString(LOCALE, DAY) ?? String(value);
}

/** "Sep 1, 2026, 10:11 AM"; a date with no time is rendered without one. */
export function formatDateTime(value: unknown): string {
  if (!value) return "—";
  if (typeof value === "string" && DATE_ONLY_RE.test(value)) return formatDate(value);
  return parseDate(value)?.toLocaleString(LOCALE, { ...DAY, hour: "numeric", minute: "2-digit" }) ?? String(value);
}

const MONTH_RE = /^(\d{4})-(0[1-9]|1[0-2])$/;

/** "May 2026" from "2026-05", built on the local calendar so no timezone can move the month. */
export function formatMonth(value: unknown): string {
  if (!value) return "—";
  const m = MONTH_RE.exec(String(value));
  if (!m) return String(value);
  return new Date(Number(m[1]), Number(m[2]) - 1, 1).toLocaleDateString(LOCALE, { month: "short", year: "numeric" });
}

/**
 * A Date as YYYY-MM-DD in the VIEWER'S calendar.
 *
 * `toISOString().slice(0, 10)` is the trap this replaces: `new Date()` is local but
 * `toISOString()` converts to UTC, so the two disagree for the offset's worth of hours
 * every day. These strings filter BUSINESS dates -- Bill Date, Accounting Date -- which
 * are calendar dates in the utility's own timezone, never UTC instants. The same defect
 * was fixed on the backend in api/reporting_dates.py; fixing it there and leaving it
 * here would only have moved the disagreement to the client.
 *
 * Two copies of defaultDateRangeYtd/LastMonth lived here, byte-identical to the ones in
 * api.ts and imported by nobody -- every consumer takes them from @/lib/api. They are
 * deleted rather than fixed twice; this helper is what api.ts now builds them from.
 */
export function localIsoDate(d: Date): string {
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}

/**
 * RFC 4180 CSV that is safe to open in Excel. A text cell starting with = + - @ is prefixed
 * with ' so it cannot run as a formula (a customer name of =HYPERLINK(...) would otherwise
 * be live in whoever opens the export); real numbers, negatives included, are left alone.
 */
export function toCsv(columns: string[], rows: Record<string, unknown>[]): string {
  const cell = (v: unknown) => {
    let s = v == null ? "" : String(v);
    if (typeof v !== "number" && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [columns.map(cell).join(","), ...rows.map((row) => columns.map((c) => cell(row[c])).join(","))].join("\r\n");
}

export function exportRowsCsv(columns: string[], rows: Record<string, unknown>[], filename: string) {
  // A byte-order mark so Excel reads the file as UTF-8 (names with accents stay intact).
  saveBlob(new Blob(["\ufeff" + toCsv(columns, rows)], { type: "text/csv;charset=utf-8;" }), filename);
}

/** Hand a file built in the browser (or fetched) to the reader as a download. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** A cell that reads as a number lines up on the right; identifiers stay literal text on the left. */
export function alignsRight(value: unknown, columnId?: string): boolean {
  if (value == null || isIdentifierColumn(columnId)) return false;
  return /^-?\d+(\.\d+)?$/.test(String(value).trim());
}
