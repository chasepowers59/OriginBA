/**
 * "Trusted additive measure" — the ones the contract says are safe to SUM.
 *
 * The lookup used to be built by upper-casing the trusted names and testing the raw
 * field id against it. That worked while every id was CISADM's UPPER_SNAKE and matched
 * nothing at all once the canvases arrived with Title Case ids: on rpt_financial_txn,
 * five trusted measures against five identically-named fields produced zero badges.
 *
 * Case is the only thing that differs between the two dialects' spellings, so it is the
 * only thing folded — punctuation and spacing stay significant, because
 * "Total Amount (Payoff)" and "Total Amount Payoff" are not the same column.
 */
export function trustedMeasureSet(trustedMeasures: string[] | undefined | null): {
  has: (fieldId: string) => boolean;
} {
  const folded = new Set((trustedMeasures ?? []).map((m) => m.toLowerCase()));
  return { has: (fieldId: string) => folded.has(String(fieldId).toLowerCase()) };
}
