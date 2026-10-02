"use client";

import { FallbackPanel } from "@/components/FallbackPanel";

// The raw message can carry SQL or database detail, so the reader gets the digest the web
// server's log is keyed by, never the message itself.
export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <FallbackPanel
      title="Something went wrong"
      actions={<button type="button" className="btn-primary" onClick={reset}>Try again</button>}
    >
      This page could not finish loading. Trying again usually works; if it keeps happening,
      send the error code below to support.
      {/* the web server's digest, not an API request reference: Settings' lookup does not know it */}
      {error.digest ? <p className="mt-3 font-mono text-xs">Error code: {error.digest}</p> : null}
    </FallbackPanel>
  );
}
