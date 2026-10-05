"use client";

/**
 * The last line: an error in the root layout itself, where error.tsx cannot help. It renders
 * its own document and inline styles because the app's layout and CSS may be what failed.
 * Like error.tsx it shows the digest the web server's log is keyed by, never the message.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#f5f7fa", color: "#1b2a3a" }}>
        <main style={{ maxWidth: 520, margin: "15vh auto", padding: 32, background: "#fff", borderRadius: 16,
                       boxShadow: "0 8px 30px rgba(0,0,0,0.08)", textAlign: "center" }}>
          <h1 style={{ fontSize: 22, margin: "0 0 12px" }}>Origin Analytics couldn&apos;t load</h1>
          <p style={{ fontSize: 14, lineHeight: 1.5, color: "#4a5b6c" }}>
            Something went wrong before the page could start. Trying again usually works; if it keeps
            happening, send the error code below to support.
          </p>
          {error.digest ? <p style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}>Error code: {error.digest}</p> : null}
          <button type="button" onClick={reset}
                  style={{ marginTop: 16, padding: "10px 20px", borderRadius: 10, border: 0, background: "#2f74b8", color: "#fff", cursor: "pointer" }}>
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
