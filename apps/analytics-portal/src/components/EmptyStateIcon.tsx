type EmptyStateIconProps = {
  variant: "chart" | "search";
  className?: string;
};

export function EmptyStateIcon({ variant, className = "" }: EmptyStateIconProps) {
  return (
    <div
      className={`mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--chip-bg)] text-[var(--foreground-subtle)] ${className}`}
      aria-hidden
    >
      {variant === "chart" ? (
        <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
          <path strokeLinecap="round" d="M4 19V5" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 17V11M12 17V7M16 17V13M20 17V9" />
        </svg>
      ) : (
        <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
          <circle cx="11" cy="11" r="6" />
          <path strokeLinecap="round" d="M16 16l4 4" />
        </svg>
      )}
    </div>
  );
}
