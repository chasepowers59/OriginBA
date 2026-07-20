"use client";

import { useBrand } from "@/components/PortalThemeProvider";

export function BrandMark({ className = "" }: { className?: string }) {
  const brand = useBrand();

  return (
    <div
      className={`brand-logo flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-sm font-bold tracking-tight text-white shadow-lg transition group-hover:scale-105 ${className}`}
      aria-hidden
    >
      {brand.logo_initials}
    </div>
  );
}
