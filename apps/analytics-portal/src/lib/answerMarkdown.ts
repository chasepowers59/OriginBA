/**
 * The assistant's light markdown, parsed into plain data the panel renders as React elements.
 *
 * Only the forms the model actually writes: paragraphs, **bold**, `code`, "- " bullets and
 * GFM tables. Nothing is ever injected as HTML: a tag in the model's text stays text.
 */

export type Inline = { kind: "text" | "bold" | "code"; text: string };
export type Block =
  | { kind: "p"; lines: Inline[][] }
  | { kind: "ul"; items: Inline[][] }
  | { kind: "table"; header: string[]; align: ("left" | "right" | "center")[]; rows: string[][] };

const INLINE = /(\*\*[^*\n]+?\*\*|`[^`\n]+?`)/g;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    const at = m.index ?? 0;
    const token = m[0];
    // "2 ** 3" is arithmetic, not bold: a bold run must hug its text on both sides.
    if (token.startsWith("**") && (/^\*\*\s/.test(token) || /\s\*\*$/.test(token))) continue;
    if (at > last) out.push({ kind: "text", text: text.slice(last, at) });
    out.push(token.startsWith("**") ? { kind: "bold", text: token.slice(2, -2) } : { kind: "code", text: token.slice(1, -1) });
    last = at + token.length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return mergeText(out);
}

function mergeText(parts: Inline[]): Inline[] {
  const out: Inline[] = [];
  for (const p of parts) {
    const prev = out[out.length - 1];
    if (prev && prev.kind === "text" && p.kind === "text") prev.text += p.text;
    else out.push({ ...p });
  }
  return out;
}

const cells = (line: string) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
const isTableRow = (line: string) => /^\s*\|.*\|\s*$/.test(line);
const isDivider = (line: string) => isTableRow(line) && cells(line).every((c) => /^:?-{3,}:?$/.test(c));
const bullet = /^\s*[-*]\s+(.*)$/;

export function parseAnswer(text: string): Block[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }

    if (isTableRow(line) && i + 1 < lines.length && isDivider(lines[i + 1])) {
      const header = cells(line);
      const align = cells(lines[i + 1]).map((c) =>
        c.startsWith(":") && c.endsWith(":") ? "center" : c.endsWith(":") ? "right" : "left") as ("left" | "right" | "center")[];
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) { rows.push(cells(lines[i])); i += 1; }
      blocks.push({ kind: "table", header, align, rows });
      continue;
    }

    if (bullet.test(line)) {
      const items: Inline[][] = [];
      while (i < lines.length && bullet.test(lines[i])) {
        items.push(parseInline((lines[i].match(bullet) as RegExpMatchArray)[1]));
        i += 1;
      }
      blocks.push({ kind: "ul", items });
      continue;
    }

    const para: Inline[][] = [];
    while (i < lines.length && lines[i].trim() && !bullet.test(lines[i])
           && !(isTableRow(lines[i]) && i + 1 < lines.length && isDivider(lines[i + 1]))) {
      para.push(parseInline(lines[i].trim()));
      i += 1;
    }
    blocks.push({ kind: "p", lines: para });
  }
  return blocks;
}
