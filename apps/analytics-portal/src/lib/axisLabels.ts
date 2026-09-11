/**
 * Axis tick labels: truncate once, and never render two categories identically.
 * Utility labels share long prefixes ("Residential Water" / "Residential Waste"),
 * so when a tail-truncated axis would collide, the whole axis switches to a
 * head…tail form — uniform, and the ends are what distinguish these names.
 */
export function tickLabels(labels: string[], max: number): string[] {
  const tail = (s: string) => (s.length > max ? `${s.slice(0, max)}…` : s);
  const simple = labels.map(tail);
  if (new Set(simple).size === simple.length) return simple;

  const head = Math.ceil((max - 1) / 2);
  const end = max - 1 - head;
  return labels.map((s) =>
    s.length > max ? `${s.slice(0, head)}…${end > 0 ? s.slice(-end) : ""}` : s,
  );
}

/**
 * A tick as up to two WHOLE lines before any ellipsis.
 *
 * Utility category names are two or three words -- "Electric Residential", "Waste
 * Water Residential" -- and a 9-character single line rendered them "Elec…tial" and
 * "Elec…cial": a reader could not tell the KPI cards' bars apart at a glance
 * (screenshot, demo25 home page, 2026-09-04). The split is the space that lets BOTH
 * lines fit, the most balanced one when several do ("Waste Water" / "Residential",
 * not "Waste" / "Water Resi…"); when none fits, the first space keeps the head word
 * whole and only the remainder is truncated.
 */
export function splitTickLabel(label: string, maxPerLine: number): string[] {
  const fit = (s: string) => (s.length > maxPerLine ? `${s.slice(0, maxPerLine - 1)}…` : s);
  const trimmed = label.trim();
  if (trimmed.length <= maxPerLine || !trimmed.includes(" ")) return [fit(trimmed)];

  const splits: Array<[string, string]> = [];
  for (let i = trimmed.indexOf(" "); i >= 0; i = trimmed.indexOf(" ", i + 1)) {
    splits.push([trimmed.slice(0, i).trim(), trimmed.slice(i + 1).trim()]);
  }
  const fitting = splits
    .filter(([a, b]) => a.length <= maxPerLine && b.length <= maxPerLine)
    .sort((x, y) => Math.max(x[0].length, x[1].length) - Math.max(y[0].length, y[1].length));
  const [head, rest] = fitting[0] ?? splits[0];
  return [fit(head), fit(rest)];
}
