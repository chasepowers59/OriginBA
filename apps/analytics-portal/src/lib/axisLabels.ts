/** How a tick line too long for its budget is shortened. */
type Fit = (s: string, max: number) => string;

const cutEnd: Fit = (s, max) => (s.length > max ? `${s.slice(0, max - 1).trimEnd()}…` : s);

/** Head and tail survive: utility labels share heads, so the ends tell them apart. */
const cutMiddle: Fit = (s, max) => {
  if (s.length <= max) return s;
  const head = Math.ceil((max - 1) / 2);
  const tail = max - 1 - head;
  return `${s.slice(0, head).trimEnd()}…${tail > 0 ? s.slice(-tail).trimStart() : ""}`;
};

const whole: Fit = (s) => s;

/** One-line ticks: truncate once, and never render two categories identically. */
export function tickLabels(labels: string[], max: number): string[] {
  return axisTickLines(labels, max + 1, 1).map(([line]) => line);
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
export function splitTickLabel(label: string, maxPerLine: number, fit: Fit = cutEnd): string[] {
  const trimmed = label.trim();
  if (trimmed.length <= maxPerLine || !trimmed.includes(" ")) return [fit(trimmed, maxPerLine)];

  const splits: Array<[string, string]> = [];
  for (let i = trimmed.indexOf(" "); i >= 0; i = trimmed.indexOf(" ", i + 1)) {
    splits.push([trimmed.slice(0, i).trim(), trimmed.slice(i + 1).trim()]);
  }
  const fitting = splits
    .filter(([a, b]) => a.length <= maxPerLine && b.length <= maxPerLine)
    .sort((x, y) => Math.max(x[0].length, x[1].length) - Math.max(y[0].length, y[1].length));
  const [head, rest] = fitting[0] ?? splits[0];
  return [fit(head, maxPerLine), fit(rest, maxPerLine)];
}

/**
 * Every tick on one axis, where two DIFFERENT categories may never render alike (UI-8:
 * a 15-character cut drew look-alike labels). Labels that would collide are laid out
 * again with a middle ellipsis, and as a last resort in full: an over-long tick is
 * better than two bars a reader cannot tell apart. The tooltip carries the full label.
 */
export function axisTickLines(labels: string[], maxPerLine: number, maxLines: 1 | 2 = 2): string[][] {
  const layout = (label: string, fit: Fit) =>
    maxLines === 1 ? [fit(label.trim(), maxPerLine)] : splitTickLabel(label, maxPerLine, fit);
  let out = labels.map((label) => layout(label, cutEnd));
  for (const fit of [cutMiddle, whole]) {
    const clashing = clashes(labels, out);
    if (!clashing.size) break;
    out = out.map((lines, i) => (clashing.has(i) ? layout(labels[i], fit) : lines));
  }
  return out;
}

/** Indexes whose rendering is shared with a different label. */
function clashes(labels: string[], rendered: string[][]): Set<number> {
  const owners = new Map<string, Set<string>>();
  const keys = rendered.map((lines, i) => {
    const key = lines.join("\n");
    owners.set(key, (owners.get(key) ?? new Set()).add(labels[i].trim()));
    return key;
  });
  return new Set(keys.flatMap((key, i) => ((owners.get(key)?.size ?? 0) > 1 ? [i] : [])));
}
