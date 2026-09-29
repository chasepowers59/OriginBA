"use client";

import { useEffect, useState } from "react";
import { slowNotice, type SlowLoad } from "@/lib/slowNotice";

/** A line under a loading placeholder that appears once the wait is long enough to worry. */
export function SlowNotice({ load }: { load: SlowLoad }) {
  const [started] = useState(() => Date.now());
  const [now, setNow] = useState(started);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const text = slowNotice(now - started, load);
  return text ? <p className="mt-3 text-sm text-fg-muted" aria-live="polite">{text}</p> : null;
}
