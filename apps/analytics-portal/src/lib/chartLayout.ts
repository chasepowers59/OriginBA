import { axisTickLines } from "@/lib/axisLabels";

/**
 * How a bar chart is laid out, decided from its data and its width before it renders
 * (issues log UI-7, UI-8, UI-14). Columns while every category can be labelled flat;
 * one row per category once there are too many, or the columns are too narrow to read.
 * Axis text is never rotated and never thinned out on a categorical axis.
 */
export type AxisPreset = {
  /** Most categories drawn as columns. */
  maxColumns: number;
  fontSize: number;
  /** Px beside the columns taken by the value axis and margins. */
  valueAxisWidth: number;
  /** Lines a row label may use on horizontal bars. */
  rowLines: 1 | 2;
};

/** KPI cards on home and workstream pages (UI-7). */
export const SPARK_AXIS: AxisPreset = { maxColumns: 5, fontSize: 10, valueAxisWidth: 4, rowLines: 1 };
/** The explorer and builder chart (UI-8). */
export const BUILDER_AXIS: AxisPreset = { maxColumns: 6, fontSize: 11, valueAxisWidth: 68, rowLines: 2 };

/**
 * Glyph advance of the UI sans at tick sizes, as a share of the font size; errs wide.
 * Capitals run wider than the 0.6 average (measured 0.68), and client codes are all
 * capitals: at 0.6 "DISCONNECT-METER" lost its first letter on the home KPI card.
 */
const CHAR_EM = 0.6;
const UPPER_EM = 0.7;

/** The widest label's average advance, so a budget in characters holds every label. */
function labelEm(labels: string[]): number {
  return Math.max(
    CHAR_EM,
    ...labels.map((label) => {
      const s = label.trim();
      const upper = s.replace(/[^A-Z]/g, "").length;
      return s ? CHAR_EM + ((UPPER_EM - CHAR_EM) * upper) / s.length : CHAR_EM;
    }),
  );
}

/** How many ordered bands still read as columns (the home cards' aging buckets run to six). */
const ORDERED_MAX_COLUMNS = 8;
/** Columns narrower than this many characters cannot carry a readable label. */
const MIN_LINE_CHARS = 8;
/** Before the chart is measured: the budgets the fixed layouts used. */
const UNMEASURED_LINE_CHARS = 12;
const UNMEASURED_ROW_AXIS = 130;
/** Horizontal bars: the label axis takes at most this share of the chart. */
const ROW_AXIS_SHARE = 0.4;
const ROW_AXIS_MAX = 220;
const AXIS_PAD = 10;

export const tickLineHeight = (fontSize: number) => Math.round(fontSize * 1.3);

export type ChartLayout = {
  /** False when a chart would say nothing; render `note` in its place. */
  showChart: boolean;
  note: string | null;
  orientation: "vertical" | "horizontal";
  /** Tick text per category, in data order. */
  tickLines: string[][];
  /** X axis height for columns; Y axis width for rows. */
  axisSize: number;
};

export function chartLayout({
  labels,
  values,
  width,
  horizontal = false,
  ordered = false,
  maxColumns,
  fontSize,
  valueAxisWidth,
  rowLines,
}: AxisPreset & {
  labels: string[];
  /** Every plotted value, all series; missing values stay null or "". */
  values: unknown[];
  /** Container px; 0 before it has been measured. */
  width: number;
  /** The reader chose horizontal bars. */
  horizontal?: boolean;
  /** An axis with an inherent order (aging bands, months): read left to right, so it keeps
   *  columns up to ORDERED_MAX_COLUMNS while every label still fits. */
  ordered?: boolean;
}): ChartLayout {
  const note = chartNote(labels, values);
  const charPx = fontSize * labelEm(labels);
  const columnChars =
    width > 0 && labels.length ? Math.floor((width - valueAxisWidth) / labels.length / charPx) : null;
  const rows =
    horizontal ||
    labels.length > (ordered ? Math.max(maxColumns, ORDERED_MAX_COLUMNS) : maxColumns) ||
    (columnChars != null && columnChars < Math.min(MIN_LINE_CHARS, wholeLabelChars(labels)));

  if (!rows) {
    const tickLines = axisTickLines(labels, columnChars ?? UNMEASURED_LINE_CHARS, 2);
    const lines = Math.max(1, ...tickLines.map((l) => l.length));
    return {
      showChart: !note,
      note,
      orientation: "vertical",
      tickLines,
      axisSize: AXIS_PAD + lines * tickLineHeight(fontSize),
    };
  }
  const budget = width > 0 ? Math.min(ROW_AXIS_MAX, width * ROW_AXIS_SHARE) : UNMEASURED_ROW_AXIS;
  const tickLines = axisTickLines(labels, Math.floor((budget - AXIS_PAD) / charPx), rowLines);
  const longest = Math.max(0, ...tickLines.flat().map((line) => line.length));
  return {
    showChart: !note,
    note,
    orientation: "horizontal",
    tickLines,
    axisSize: Math.min(budget, Math.ceil(longest * charPx) + AXIS_PAD),
  };
}

/** Why no chart should be drawn (UI-14): none of these is a comparison. */
function chartNote(labels: string[], values: unknown[]): string | null {
  if (!labels.length) return "No breakdown to show.";
  // Number(null) and Number("") are 0: a missing value must not read as a zero.
  const present = values.filter((v) => v != null && v !== "").map(Number);
  if (!present.length) return "No values recorded.";
  if (present.every((v) => v === 0)) return "Every value is zero.";
  if (new Set(labels).size === 1) return `Nothing to compare: one group (${labels[0]}).`;
  return null;
}

/** The narrowest line that still shows every label whole on two lines. */
function wholeLabelChars(labels: string[]): number {
  return Math.max(
    0,
    ...labels.map((label) => {
      const s = label.trim();
      let best = s.length;
      for (let i = s.indexOf(" "); i >= 0; i = s.indexOf(" ", i + 1)) {
        best = Math.min(best, Math.max(i, s.length - i - 1));
      }
      return best;
    }),
  );
}

/** Horizontal bars: px per category row, and the tallest the scroll area grows. */
export const ROW_PITCH = 34;
const ROW_VIEWPORT_MAX = 560;
/** recharts' default axis height, and the fixed legend box above the rows. */
export const ROW_VALUE_AXIS_HEIGHT = 30;
export const ROW_LEGEND_HEIGHT = 28;

export type RowScroll = {
  /** Height of the whole chart: the rows at ROW_PITCH plus `chrome`. */
  chartHeight: number;
  /** Px above the first row: the value axis, and the legend when there is one. */
  chrome: number;
  /** Height of the visible area; cut between rows, never through one. */
  viewport: number;
  scrolls: boolean;
};

/** How a horizontal bar chart of `rows` categories fits a scroll area. */
export function rowScroll({ rows, height, legend }: { rows: number; height: number; legend: boolean }): RowScroll {
  const chrome = ROW_VALUE_AXIS_HEIGHT + (legend ? ROW_LEGEND_HEIGHT : 0);
  const chartHeight = Math.max(height, rows * ROW_PITCH + chrome);
  const cap = Math.max(height, ROW_VIEWPORT_MAX);
  if (chartHeight <= cap) return { chartHeight, chrome, viewport: chartHeight, scrolls: false };
  const wholeRows = Math.floor((cap - chrome) / ROW_PITCH);
  return { chartHeight, chrome, viewport: chrome + wholeRows * ROW_PITCH, scrolls: true };
}

/**
 * recharts `minPointSize` for KPI bars: a small or negative value would draw a 1px
 * sliver, so it gets 2px; zero and missing stay empty, since recharts would otherwise
 * draw zero as a 2px bar too.
 */
export const minBarPx = (value: number | null | undefined) => (value ? 2 : 0);

export type PieSlice = { label: string; value: number };

/** Four named slices and "Other": the five chart colours, none repeated (UI-15). */
const PIE_NAMED_SLICES = 4;

/**
 * The slices of a readable pie, or why bars show the result instead. A negative arc
 * means nothing, and adjustments and refunds go negative routinely. "Other" is only
 * honest while it is no bigger than the smallest slice named beside it.
 */
export function piePlan(
  labels: string[],
  values: number[],
): { slices: PieSlice[]; note: null } | { slices: null; note: string } {
  if (values.some((v) => v < 0)) {
    return { slices: null, note: "Shown as bars: a pie cannot show negative values." };
  }
  const ranked = labels
    .map((label, i) => ({ label, value: values[i] }))
    .filter((s) => s.value > 0)
    .sort((a, b) => b.value - a.value);
  if (ranked.length <= PIE_NAMED_SLICES + 1) return { slices: ranked, note: null };

  const named = ranked.slice(0, PIE_NAMED_SLICES);
  const rest = ranked.slice(PIE_NAMED_SLICES);
  const other = rest.reduce((sum, s) => sum + s.value, 0);
  if (other > named[PIE_NAMED_SLICES - 1].value) {
    return { slices: null, note: `Shown as bars: ${labels.length} groups are too many for a readable pie.` };
  }
  return { slices: [...named, { label: `Other (${rest.length})`, value: other }], note: null };
}
