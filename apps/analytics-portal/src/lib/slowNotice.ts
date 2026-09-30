/** After this long a load says what it is doing, so slow never reads as stuck. */
export const SLOW_AFTER_MS = 5_000;

export type SlowLoad = { doing: string; typical: string };

export function slowNotice(elapsedMs: number, load: SlowLoad): string | null {
  if (elapsedMs < SLOW_AFTER_MS) return null;
  const s = Math.floor(elapsedMs / 1000);
  const took = s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${s % 60} s`;
  return `${load.doing}: ${load.typical} (${took} so far).`;
}
