"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { fetchAuthStatus, login, resolveTenant } from "@/lib/authApi";
import { storeAccessToken } from "@/lib/auth";
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

  // SSO: show the button when the API is configured for it, and catch the callback's
  // #sso_token= fragment (fragments never reach server logs) exactly like a password
  // login's token.
  const [ssoEnabled, setSsoEnabled] = useState(false);
  useEffect(() => {
    fetchAuthStatus()
      .then((s) => setSsoEnabled(Boolean(s.oidc_enabled)))
      .catch(() => setSsoEnabled(false));
  }, []);
  useEffect(() => {
    const m = window.location.hash.match(/[#&]sso_token=([^&]+)/);
    if (!m) return;
    window.history.replaceState(null, "", window.location.pathname + window.location.search);
    void storeAccessToken(decodeURIComponent(m[1]), 8 * 60 * 60)
      .then(() => refresh())
      .then(() => router.replace(searchParams.get("next") || "/"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    <div className="grid min-h-screen bg-white text-slate-900 lg:grid-cols-[1fr_1.1fr]">
      {/* form column — clean, light, logo pinned top-left (reference layout) */}
      <div className="relative flex flex-col px-8 py-8 sm:px-14">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/origin-logo.png" alt="Origin" className="h-8 w-auto self-start" />

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">
            {boundToTenant ? `Sign in to ${tenantName}` : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {boundToTenant
              ? `${DEFAULT_BRAND.name} ${DEFAULT_BRAND.product} for ${tenantName}`
              : `Sign in to ${DEFAULT_BRAND.name} ${DEFAULT_BRAND.product}`}
          </p>
          <form onSubmit={onSubmit} className="mt-8 space-y-5">
            {boundToTenant ? (
              <div
                className="flex items-center gap-2 rounded-xl border border-[#2f74b8]/30 bg-[#2f74b8]/[0.07] px-4 py-3 text-sm text-[#1b3959]"
                aria-label={`Organization: ${tenantName}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/origin-mark.png" alt="" className="h-4 w-auto" aria-hidden />
                <span>
                  Organization: <strong>{tenantName}</strong>
                </span>
              </div>
            ) : (
              <label className="block text-sm font-medium text-slate-700" htmlFor="login-org">
                Organization
                <input
                  id="login-org"
                  type="text"
                  autoComplete="organization"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                  className="login-input mt-1.5"
                  placeholder="Your organization (optional)"
                />
              </label>
            )}
            <label className="block text-sm font-medium text-slate-700" htmlFor="login-email">
              Email
              <input
                id="login-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="login-input mt-1.5"
                placeholder="you@utility.gov"
                required
                autoFocus
              />
            </label>
            <label className="block text-sm font-medium text-slate-700" htmlFor="login-password">
              Password
              <div className="relative mt-1.5">
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="login-input pr-16"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-2 my-auto h-7 rounded px-2 text-xs text-slate-500 hover:underline"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </label>
            {error ? (
              <p
                role="alert"
                className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700"
              >
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-[#2f74b8] py-3 text-sm font-semibold text-white shadow-lg shadow-[#2f74b8]/25 transition hover:bg-[#28649f] disabled:opacity-60"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
            {ssoEnabled ? (
              <>
                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span className="h-px flex-1 bg-slate-200" />
                  or
                  <span className="h-px flex-1 bg-slate-200" />
                </div>
                <a
                  href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/auth/oidc/login`}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  <span aria-hidden className="grid grid-cols-2 gap-[1px]">
                    <span className="h-2 w-2 bg-[#f25022]" />
                    <span className="h-2 w-2 bg-[#7fba00]" />
                    <span className="h-2 w-2 bg-[#00a4ef]" />
                    <span className="h-2 w-2 bg-[#ffb900]" />
                  </span>
                  Sign in with Microsoft
                </a>
              </>
            ) : null}
          </form>
        </div>

        <p className="text-xs text-slate-400">
          Trouble signing in? Contact your portal administrator — accounts are provisioned
          per organization.
        </p>
      </div>

      {/* brand panel — full-bleed Origin navy with a bold tagline (reference layout) */}
      <div className="relative hidden overflow-hidden bg-[#16283c] lg:block">
        {/* subtle brand-mark pattern, like the reference's code-glyph texture */}
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage: "url(/origin-mark.png)",
            backgroundSize: "140px auto",
            backgroundRepeat: "space",
          }}
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[#0c1826]"
        />
        <div className="relative flex h-full flex-col items-center justify-center px-14 text-center">
          <h2 className="text-4xl font-bold leading-tight text-white xl:text-5xl">
            Utility intelligence,
            <br />
            <span className="text-[#6aa9dd]">governed end to end</span>
          </h2>
          <p className="mt-5 max-w-md text-sm leading-relaxed text-slate-300">
            Reporting canvases transformed from Oracle C2M and validated against your own
            live system — the numbers tie back to CIS because they are proven to, per key.
          </p>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/origin-logo-white.png" alt="" aria-hidden className="mt-14 h-10 w-auto opacity-90" />
          <p className="mt-4 text-xs text-slate-400">
            {DEFAULT_BRAND.name} {DEFAULT_BRAND.product} · SmartCity reporting platform
          </p>
        </div>
      </div>
    </div>
  );
}
