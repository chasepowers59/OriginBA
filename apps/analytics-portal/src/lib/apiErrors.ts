export function parseApiError(raw: string, fallback = "Request failed"): string {
  const text = raw.trim();
  if (!text) return fallback;
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    const detail = parsed.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
  } catch {
    /* plain text */
  }
  return text.length > 180 ? `${text.slice(0, 180)}…` : text;
}

/** A refused request, keeping its HTTP status so a page can say WHY (403 vs 501 vs 422). */
export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}
