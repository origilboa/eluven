import Link from "next/link";

import { isRTL, type Locale } from "@/i18n.config";

type HomePageProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function HomePage({ params }: HomePageProps) {
  const { locale } = await params;
  const rtl = isRTL(locale);

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-lg text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-zinc-500">
          Eluven
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-zinc-900 dark:text-zinc-50">
          {locale === "he" ? "מרחב מחקר אקדמי מונחה AI" : "AI-powered academic research workspace"}
        </h1>
        <p className="mt-4 text-base leading-7 text-zinc-600 dark:text-zinc-400">
          {locale === "he"
            ? "התחבר כדי לנהל משימות, שרשורים וזרימות עבודה."
            : "Sign in to manage Tasks, Threads, and Workflows."}
        </p>
        <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Link
            href={`/${locale}/login`}
            className="inline-flex h-11 items-center justify-center rounded-lg bg-zinc-900 px-6 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {locale === "he" ? "התחברות" : "Sign in"}
          </Link>
          <Link
            href={rtl ? "/en" : "/he"}
            className="inline-flex h-11 items-center justify-center rounded-lg border border-zinc-300 px-6 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
          >
            {locale === "he" ? "English UI" : "ממשק בעברית"}
          </Link>
        </div>
      </div>
    </main>
  );
}
