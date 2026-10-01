import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";

/** The shared frame for the not-found and error pages: brand, message, ways out. */
export function FallbackPanel({ title, children, actions }: {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="glass-panel w-full max-w-md p-8 text-center">
        <Link href="/" className="mb-6 inline-flex"><BrandMark /></Link>
        <h1 className="text-xl font-semibold text-[var(--foreground)]">{title}</h1>
        <div className="mt-2 text-sm text-[var(--foreground-muted)]">{children}</div>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {actions}
          <Link href="/" className="btn-ghost">Home</Link>
          <Link href="/reports" className="btn-ghost">Report library</Link>
        </div>
      </div>
    </main>
  );
}
