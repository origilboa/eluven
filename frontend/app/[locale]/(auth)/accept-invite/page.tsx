"use client";

import { signIn } from "next-auth/react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { InvitationPreviewResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

export default function AcceptInvitePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const localeParam = params.locale;
  const locale: Locale =
    typeof localeParam === "string" && isLocale(localeParam) ? localeParam : "en";
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [preview, setPreview] = useState<InvitationPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const copy =
    locale === "he"
      ? {
          title: "קבלת הזמנה",
          subtitle: "הגדר סיסמה כדי להצטרף ל-Eluven",
          password: "סיסמה",
          confirm: "אימות סיסמה",
          submit: "צור חשבון",
          submitting: "יוצר…",
          invalid: "ההזמנה אינה תקפה",
          mismatch: "הסיסמאות אינן תואמות",
          login: "התחברות",
          org: "ארגון",
        }
      : {
          title: "Accept invitation",
          subtitle: "Set a password to join Eluven",
          password: "Password",
          confirm: "Confirm password",
          submit: "Create account",
          submitting: "Creating…",
          invalid: "This invitation is not valid",
          mismatch: "Passwords do not match",
          login: "Sign in",
          org: "Organization",
        };

  useEffect(() => {
    if (!token) {
      setError(copy.invalid);
      return;
    }
    api
      .get<InvitationPreviewResponse>(
        `/auth/invitations/preview?token=${encodeURIComponent(token)}`,
      )
      .then((data) => {
        setPreview(data);
        if (!data.is_valid) {
          setError(copy.invalid);
        }
      })
      .catch(() => setError(copy.invalid));
  }, [token, copy.invalid]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError(copy.mismatch);
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("/auth/accept-invite", { token, password });
      const result = await signIn("credentials", {
        email: preview?.email ?? "",
        password,
        redirect: false,
      });
      if (result?.error) {
        router.push(`/${locale}/login`);
        return;
      }
      router.push(`/${locale}/dashboard`);
      router.refresh();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : copy.invalid);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <div className="text-start">
            <p className="text-sm font-medium uppercase tracking-wide text-zinc-500">Eluven</p>
            <h1 className="mt-2 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
              {copy.title}
            </h1>
            <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
            {preview ? (
              <div className="mt-4 rounded-lg bg-zinc-50 p-3 text-sm dark:bg-zinc-900">
                <p className="font-medium text-zinc-900 dark:text-zinc-50">{preview.name}</p>
                <p className="text-zinc-600 dark:text-zinc-400">{preview.email}</p>
                <p className="mt-1 text-xs text-zinc-500">
                  {copy.org}: {preview.org_name}
                </p>
              </div>
            ) : null}
          </div>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2 text-start">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                {copy.password}
              </label>
              <input
                id="password"
                type="password"
                minLength={8}
                required
                disabled={!preview?.is_valid}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
            </div>
            <div className="space-y-2 text-start">
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
              >
                {copy.confirm}
              </label>
              <input
                id="confirmPassword"
                type="password"
                minLength={8}
                required
                disabled={!preview?.is_valid}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
            </div>

            {error ? (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={isSubmitting || !preview?.is_valid}
              className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {isSubmitting ? copy.submitting : copy.submit}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm text-zinc-600 dark:text-zinc-400">
          <Link
            href={`/${locale}/login`}
            className="font-medium text-zinc-900 underline-offset-4 hover:underline dark:text-zinc-100"
          >
            {copy.login}
          </Link>
        </p>
      </div>
    </main>
  );
}
