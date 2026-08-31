"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { changePassword } from "@/lib/authApi";
import { DEFAULT_BRAND } from "@/lib/brand";

export default function ChangePasswordPage() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await changePassword(currentPassword, newPassword);
      await refresh();
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed");
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
          <h1 className="text-2xl font-bold portal-heading">Set a new password</h1>
          <p className="mt-2 text-sm portal-text-muted">
            {user?.email
              ? `A new password is required for ${user.email} before continuing.`
              : "Choose a new password to continue."}
          </p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block text-sm portal-text-muted">
            Current password
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="input-modern mt-1"
              required
            />
          </label>
          <label className="block text-sm portal-text-muted">
            New password
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input-modern mt-1"
              minLength={8}
              required
            />
          </label>
          <label className="block text-sm portal-text-muted">
            Confirm new password
            <input
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input-modern mt-1"
              minLength={8}
              required
            />
          </label>
          {error ? (
            <p className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-600 dark:text-red-300">
              {error}
            </p>
          ) : null}
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? "Updating…" : "Update password"}
          </button>
          <p className="text-center text-xs portal-text-subtle">{DEFAULT_BRAND.product}</p>
        </form>
      </div>
    </div>
  );
}
