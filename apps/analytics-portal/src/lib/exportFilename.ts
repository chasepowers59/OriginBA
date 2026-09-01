/**
 * A safe, readable filename for an exported file.
 *
 * These files leave the portal by email, so the name is the only label they carry. The
 * dashboard export produced "..._Executive_Dashboard_dashboard.xlsx" -- the kind
 * appended to a title that already ended in it -- and replaced only whitespace, so a
 * client name carrying a slash or a colon would have produced something the filesystem
 * refuses or silently truncates.
 */
export function exportFilename(title: string, kind: string, extension: string): string {
  const clean = (value: string) =>
    value
      // Anything a filesystem or a mail client may object to, plus the punctuation that
      // survives a title but reads as noise in a filename.
      .replace(/[/\\:*?"<>|()[\]{}]/g, " ")
      .replace(/[^\w\s.-]/g, " ")
      .trim()
      .replace(/\s+/g, "_")
      .replace(/_{2,}/g, "_")
      .replace(/^[_.-]+|[_.-]+$/g, "");

  const base = clean(title);
  const suffix = clean(kind);
  // "Executive Dashboard" + "dashboard" is one word too many.
  const alreadySaysIt =
    suffix && base.toLowerCase().split("_").includes(suffix.toLowerCase());
  const name = [base, alreadySaysIt ? "" : suffix].filter(Boolean).join("_") || "export";
  return `${name}.${extension}`;
}
