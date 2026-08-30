"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { login, resolveTenant } from "@/lib/authApi";
import { useAuth } from "@/components/AuthProvider";
import { DEFAULT_BRAND } from "@/lib/brand";

/**
 * Sign-in: a split layout that sells the platform on the left and signs in on the
 * right. The value panel states what the reader gets in utility language --
 * governed canvases, exec KPIs, data-quality worklists -- never generic SaaS copy.
 */
export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [organization, setOrganization] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Multi-tenant: a /<slug> URL redirects here with ?tenant=<slug>. When present the org
  // is fixed by the URL (no org field); at the root the user types the organization.
  const tenantSlug = searchParams.get("tenant");
  const [tenantName, setTenantName] = useState<string | null>(null);
  useEffect(() => {
    if (!tenantSlug) {
      setTenantName(null);
      return;
    }
    let active = true;
    resolveTenant(tenantSlug)
      .then((org) => {
        if (active) setTenantName(org.display_name);
      })
      .catch(() => {
        // Unknown slug: fall back to the root experience (show the org field).
        if (active) setTenantName(null);
      });
    return () => {
      active = false;
    };
  }, [tenantSlug]);

  const boundToTenant = Boolean(tenantSlug && tenantName);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const org = boundToTenant ? tenantSlug : organization.trim() || undefined;
      const signedIn = await login(email, password, org);
      await refresh();
      if (signedIn.must_change_password) {
        router.replace("/change-password");
        return;
      }
      const next = searchParams.get("next") || "/";
      router.replace(next);
    } catch (err) {
      setError(
        err instanceof Error && err.message
          ? err.message
          : "Sign-in failed — check your email and password.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mesh-bg flex min-h-screen items-center justify-center px-4 py-8">
      <div className="glass-panel grid w-full max-w-4xl overflow-hidden md:grid-cols-2">
        {/* value panel */}
        <div className="hidden flex-col justify-between bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900 p-10 text-white md:flex">
          <div>
            <div className="brand-logo mb-6 flex h-12 w-12 items-center justify-center rounded-xl text-base font-bold">
              BA
            </div>
            <h2 className="text-2xl font-semibold leading-snug text-[#f8fafc]">
              Utility intelligence on governed data
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-200/90">
              Reporting canvases transformed from Oracle C2M and validated against
              your own live system — the numbers tie back to CIS because they are
              proven to, per key.
            </p>
          </div>
          <ul className="space-y-3 text-sm text-[#e2e8f0]">
            {[
              "Executive KPIs with period comparison",
              "Billing, payments, collections, and usage analytics",
              "Data-quality worklists with exact CIS actions",
              "Ad hoc exploration over every governed canvas",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span aria-hidden className="mt-0.5 text-teal-300">
                  ✓
                </span>
                {item}
              </li>
            ))}
          </ul>
          <p className="text-xs text-[#94a3b8]">
            {DEFAULT_BRAND.product} · SmartCity reporting platform
          </p>
        </div>

        {/* sign-in panel */}
        <div className="p-8 md:p-10">
          <div className="mb-6 md:hidden">
            <div className="brand-logo mb-3 flex h-12 w-12 items-center justify-center rounded-xl text-base font-bold text-white">
              BA
            </div>
          </div>
          <h1 className="portal-heading text-2xl font-bold">Welcome back</h1>
          <p className="portal-text-muted mt-1 text-sm">
            {boundToTenant ? (
              <>
                Sign in to{" "}
                <span className="portal-heading font-semibold">{tenantName}</span>
              </>
            ) : (
              <>Sign in to {DEFAULT_BRAND.product}</>
            )}
          </p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            {boundToTenant ? (
              <div
                className="flex items-center gap-2 rounded-lg border border-sky-400/30 bg-sky-500/10 px-3 py-2 text-sm text-sky-700 dark:text-sky-300"
                aria-label={`Organization: ${tenantName}`}
              >
                <span aria-hidden>🏢</span>
                <span>
                  Organization: <strong>{tenantName}</strong>
                </span>
              </div>
            ) : (
              <label className="portal-text-muted block text-sm" htmlFor="login-org">
                Organization
                <input
                  id="login-org"
                  type="text"
                  autoComplete="organization"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                  className="input-modern mt-1"
                  placeholder="Your organization (optional)"
                />
              </label>
            )}
            <label className="portal-text-muted block text-sm" htmlFor="login-email">
              Email
              <input
                id="login-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-modern mt-1"
                placeholder="you@utility.gov"
                required
                autoFocus
              />
            </label>
            <label
              className="portal-text-muted block text-sm"
              htmlFor="login-password"
            >
              Password
              <div className="relative mt-1">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-modern pr-16"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="portal-text-muted absolute inset-y-0 right-2 my-auto h-7 rounded px-2 text-xs hover:underline"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </label>
            {error ? (
              <p
                role="alert"
                className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-300"
              >
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting}
              className="btn-primary w-full disabled:opacity-60"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
            <p className="portal-text-muted text-xs">
              Trouble signing in? Contact your portal administrator — accounts are
              provisioned per organization.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
