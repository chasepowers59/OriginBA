/**
 * Label a time bucket for a chart axis.
 *
 * A bucket arrives as the raw start of its period -- both date_trunc and Oracle's TRUNC
 * return a timestamp -- so an axis fell back to the generic truncation and read
 * "2022-07-01T00:0…". The caller knows the grain it asked for, so the label can name the
 * period instead of showing its first instant.
 *
 * Parsed manually rather than with `new Date(...)`: these strings carry no zone, and
 * Date would shift them into the viewer's, which can move a bucket into the previous
 * month.
 */
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const ISO = /^(\d{4})-(\d{2})-(\d{2})(?:[T ]|$)/;

export function formatTimeBucket(value: string, grain?: string | null): string {
  const m = ISO.exec(value);
  if (!m) return value;

  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  if (month < 1 || month > 12) return value;

  switch (grain) {
    case "year":
      return String(year);
    case "quarter":
      return `Q${Math.floor((month - 1) / 3) + 1} ${year}`;
    case "day":
    case "week":
      return `${day} ${MONTHS[month - 1]} ${year}`;
    default:
      return `${MONTHS[month - 1]} ${year}`;
  }
}
