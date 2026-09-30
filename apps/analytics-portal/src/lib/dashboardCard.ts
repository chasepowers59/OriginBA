/**
 * What a saved dashboard contains, in one line.
 *
 * The list card showed "4 tiles · last 180 days", which distinguishes nothing: two
 * boards built from different templates read identically until you open both. Every
 * tile's title was already in the response and thrown away.
 *
 * Two names then a count, because the card is one line and a list of four titles wraps
 * into a paragraph nobody scans.
 */
// Only `title` is read; the rest of a tile rides along from the API.
export function tileSummary(
  tiles: { title?: string; [k: string]: unknown }[] | undefined | null,
): string {
  const titles = (tiles ?? []).map((t) => (t.title || "").trim()).filter(Boolean);
  if (!titles.length) return "";
  if (titles.length === 1) return titles[0];
  if (titles.length === 2) return `${titles[0]} and ${titles[1]}`;
  return `${titles[0]}, ${titles[1]} and ${titles.length - 2} more`;
}
