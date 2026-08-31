"use client";

/**
 * The official Origin horizontal logo (mark + wordmark). Full-colour on light surfaces,
 * a white version on dark ones, swapped by theme. `mark` renders just the infinity mark
 * (theme-independent) for compact spots. Assets live in public/ (origin-logo*.png,
 * origin-mark.png), rasterised from the vendor's vector.
 */
export function BrandMark({
  className = "h-8 w-auto",
  mark = false,
}: {
  className?: string;
  mark?: boolean;
}) {
  if (mark) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src="/origin-mark.png" alt="Origin" className={`shrink-0 ${className}`} />;
  }
  return (
    <span className="inline-flex shrink-0 items-center transition group-hover:scale-105">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/origin-logo.png" alt="Origin" className={`${className} dark:hidden`} />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/origin-logo-white.png" alt="Origin" className={`${className} hidden dark:block`} />
    </span>
  );
}
