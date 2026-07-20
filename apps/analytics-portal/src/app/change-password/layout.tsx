import { Suspense, type ReactNode } from "react";

export default function ChangePasswordLayout({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="mesh-bg min-h-screen" />}>{children}</Suspense>;
}
