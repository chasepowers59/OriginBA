/** One free-text field to a clean address list — commas, semicolons or newlines. */
export function parseRecipients(raw: string): string[] {
  return raw
    .split(/[,;\s]+/)
    .map((r) => r.trim())
    .filter(Boolean);
}
