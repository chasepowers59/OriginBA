"use client";

import { prettifyFieldName } from "@/lib/businessLabels";

/**
 * The "you are looking at a slice" banner, in one place.
 *
 * This markup existed three times — ExecutiveDashboard, WorkstreamDashboard and
 * CustomDashboardPage — byte-identical apart from one word ("Cross-filter active:"
 * against "Cross-filter:"). All three interpolated `filter.field` RAW, so on the six
 * legacy orgs the banner read "Cross-filter: ACCOUNTING_DT = ..." while the dev org,
 * whose canvas fields are already Title Case, looked perfectly fine. That is why it
 * survived: the shape we develop against hides it.
 *
 * "active" is dropped because the banner only exists when a filter is active.
 */
export function CrossFilterBanner({
  field,
  value,
  onClear,
}: {
  field: string;
  value: string;
  onClear: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-warn bg-warn-bg px-4 py-2 text-sm text-warn">
      <span>
        Cross-filter: <strong>{prettifyFieldName(field)}</strong> = {value}
      </span>
      <button type="button" onClick={onClear} className="btn-ghost text-xs">
        Clear
      </button>
    </div>
  );
}
