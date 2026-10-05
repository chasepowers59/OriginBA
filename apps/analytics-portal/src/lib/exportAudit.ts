import { activeOrganizationHeader, authHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Tell the API a CSV or Excel file left the portal, for its audit trail (POST
 * /portal/export/record). PDFs are built and recorded by the API itself. Fire and forget:
 * a download is never held up or stopped by the record failing.
 */
export function noteExport(format: "csv" | "xlsx", file: string, rows: number): void {
  if (typeof window === "undefined") return;
  try {
    void fetch(`${API_BASE}/portal/export/record`, {
      method: "POST",
      keepalive: true,
      headers: { "Content-Type": "application/json", ...authHeaders(), ...activeOrganizationHeader() },
      body: JSON.stringify({ format, file: file.slice(0, 200), rows }),
    }).catch(() => undefined);
  } catch {
    /* recording is best effort */
  }
}
