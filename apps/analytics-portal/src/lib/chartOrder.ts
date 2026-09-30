/**
 * One ordering rule for every chart in the portal.
 *
 * Categorical charts are ranked largest first — the reading convention for bars, and
 * the reason is comparison: ranked bars let you see the order at a glance, where query
 * order makes the reader compare every pair themselves. Rendering left-to-right that
 * puts the biggest bar at the left; on the horizontal layout it puts it at the top.
 *
 * Some axes carry their own order and must keep it. A date axis is the obvious one —
 * ranking it by size destroys the trend the chart exists to show — but an aging band is
 * the same problem wearing different clothes: `Oldest Debt Band` ranked by size reads
 * None, 0-30, 121+, 31-60.
 *
 * Stacked charts rank by the TOTAL across series, because the total is the bar the
 * reader actually sees — ranking by the first series alone puts a visibly shorter bar
 * first whenever the later series dominate.
 */

/** Numeric-aware, so "31-60" precedes "121+" and "2026-02" follows "2026-01". */
const NATURAL = new Intl.Collator(undefined, { numeric: true });

const ORDERED_AXIS = /\b(date|month|quarter|year|week|day|period|band|bucket|range|age|aging)\b/i;

/**
 * Whether an axis carries an inherent order that ranking would destroy. Matched on the
 * dimension's business name, which is the only thing the chart surfaces know about it.
 */
export function isOrderedAxis(dimension: string | null | undefined): boolean {
  return Boolean(dimension && ORDERED_AXIS.test(dimension));
}

export function orderChartRows<T extends Record<string, unknown>>(
  rows: T[],
  xKey: string,
  valueKeys: string[],
  axisOrdered: boolean,
): T[] {
  if (axisOrdered) {
    return [...rows].sort((a, b) => NATURAL.compare(String(a[xKey]), String(b[xKey])));
  }
  if (!valueKeys.length) return [...rows];

  const total = (row: T) =>
    valueKeys.reduce((sum, key) => {
      const n = Number(row[key]);
      return sum + (Number.isFinite(n) ? n : 0);
    }, 0);

  // Array.prototype.sort is stable, so equal bars keep the order the query returned.
  return [...rows].sort((a, b) => total(b) - total(a));
}
