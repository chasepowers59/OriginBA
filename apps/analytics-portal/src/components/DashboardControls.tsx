"use client";

type DashboardControlsProps = {
  days: number;
  compare: boolean;
  onDaysChange: (days: number) => void;
  onCompareChange: (compare: boolean) => void;
};

const DAY_OPTIONS = [
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 180, label: "6 months" },
];

export function DashboardControls({
  days,
  compare,
  onDaysChange,
  onCompareChange,
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
        {compare ? "Prior period compare on" : "Compare to prior period"}
      </button>
    </div>
  );
}
