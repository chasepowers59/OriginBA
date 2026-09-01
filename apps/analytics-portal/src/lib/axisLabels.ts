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
