/** Links and paste-in snippets for a saved view embedded in another site. */

export const EMBED_LIFETIMES = [
  { label: "1 hour", minutes: 60 },
  { label: "8 hours", minutes: 8 * 60 },
  { label: "1 day", minutes: 24 * 60 },
] as const;

export function embedLink(origin: string, token: string): string {
  return `${origin}/embed/${token}`;
}

const escapeAttr = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export function embedSnippet(origin: string, token: string, title: string): string {
  return `<iframe src="${embedLink(origin, token)}" title="${escapeAttr(title)}" width="100%" height="480" style="border:0"></iframe>`;
}
