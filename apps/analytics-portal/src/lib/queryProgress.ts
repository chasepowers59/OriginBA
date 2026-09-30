/** Shown in place of the bare skeleton once a query has run past two seconds. */
export function runningLabel(elapsedMs: number): string | null {
  return elapsedMs < 2000 ? null : `Running… ${Math.floor(elapsedMs / 1000)}s`;
}
