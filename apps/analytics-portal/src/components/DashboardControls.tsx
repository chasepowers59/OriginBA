"use client";

export type CompareMode = "prior_period" | "mom" | "yoy";

type DashboardControlsProps = {
  days: number;
  compare: boolean;
  compareMode?: CompareMode;
  onDaysChange: (days: number) => void;
  onCompareChange: (compare: boolean) => void;
  onCompareModeChange?: (mode: CompareMode) => void;
};

const DAY_OPTIONS = [
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 180, label: "6 months" },
];

// The three honest comparisons a utility asks for: rolling window, calendar
// month vs previous month, and the same window last year (seasonality --
// July vs June is weather; July vs last July is signal).
const COMPARE_OPTIONS: { value: CompareMode; label: string }[] = [
  { value: "prior_period", label: "Prior period" },
  { value: "mom", label: "Month / month" },
  { value: "yoy", label: "Year / year" },
];

export function DashboardControls({
  days,
  compare,
  compareMode = "prior_period",
  onDaysChange,
  onCompareChange,
  onCompareModeChange,
}: DashboardControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex flex-wrap gap-2">
        {DAY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onDaysChange(opt.value)}
            className={`chip ${days === opt.value ? "chip-active" : ""}`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={() => onCompareChange(!compare)}
        className={`chip ${compare ? "chip-active" : ""}`}
      >
        {compare ? "Compare on" : "Compare"}
      </button>
      {compare && onCompareModeChange ? (
        <div className="flex flex-wrap gap-2">
          {COMPARE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onCompareModeChange(opt.value)}
              className={`chip ${compareMode === opt.value ? "chip-active" : ""}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
