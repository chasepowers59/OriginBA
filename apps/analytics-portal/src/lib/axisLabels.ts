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
 * A tick as up to two WHOLE lines, split at the first space, before any ellipsis.
 *
 * Utility category names are two words -- "Electric Residential", "Gas Commercial" --
 * and a 9-character single line rendered them "Elec…tial" and "Elec…cial": a reader
 * could not tell the KPI cards' bars apart at a glance (screenshot, demo25 home page,
 * 2026-09-04). Word per line shows both words whole; only a word that STILL does not
 * fit is truncated.
 */
export function splitTickLabel(label: string, maxPerLine: number): string[] {
  const fit = (s: string) => (s.length > maxPerLine ? `${s.slice(0, maxPerLine - 1)}…` : s);
  const trimmed = label.trim();
  const space = trimmed.indexOf(" ");
  if (space < 0 || trimmed.length <= maxPerLine) return [fit(trimmed)];
  return [fit(trimmed.slice(0, space)), fit(trimmed.slice(space + 1).trim())];
}
