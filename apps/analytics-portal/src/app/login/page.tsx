"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login } from "@/lib/authApi";
import { useAuth } from "@/components/AuthProvider";
import { DEFAULT_BRAND } from "@/lib/brand";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const signedIn = await login(email, password);
      await refresh();
      if (signedIn.must_change_password) {
        router.replace("/change-password");
        return;
      }
      const next = searchParams.get("next") || "/";
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mesh-bg flex min-h-screen items-center justify-center px-4">
      <div className="glass-panel w-full max-w-md p-8">
        <div className="mb-6 text-center">
          <div className="brand-logo mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl text-lg font-bold text-white">
            BA
          </div>
          <h1 className="text-2xl font-bold portal-heading">{DEFAULT_BRAND.product}</h1>
          <p className="mt-2 text-sm portal-text-muted">Sign in to continue</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block text-sm portal-text-muted">
            Email
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-modern mt-1"
              required
            />
          </label>
          <label className="block text-sm portal-text-muted">
            Password
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-modern mt-1"
              required
            />
          </label>
          {error ? (
            <p className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {error}
            </p>
          ) : null}
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
