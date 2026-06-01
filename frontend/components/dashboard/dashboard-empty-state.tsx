"use client";

import {
  MODULE_TYPE_EXTERNAL_PAPER_REVIEW,
  MODULE_TYPE_STUDENT_PAPER_REVIEW,
} from "@/lib/modules";
import type { Locale } from "@/i18n.config";

type DashboardEmptyStateProps = {
  locale: Locale;
  onSampleEpr: () => void;
  onSampleSpr: () => void;
};

export function DashboardEmptyState({
  locale,
  onSampleEpr,
  onSampleSpr,
}: DashboardEmptyStateProps) {
  const copy =
    locale === "he"
      ? {
          title: "אין משימות עדיין",
          body: "צור משימה חדשה כדי להתחיל לעבוד עם מסמכים, שרשורים וזיכרון משימה.",
          sampleEpr: "צור משימת סקירת מאמר לדוגמה",
          sampleSpr: "צור משימת סקירת סטודנט לדוגמה",
        }
      : {
          title: "No tasks yet",
          body: "Create a task to start working with documents, threads, and task memory.",
          sampleEpr: "Create a sample External Paper Review task",
          sampleSpr: "Create a sample Student Paper Review task",
        };

  return (
    <div className="rounded-2xl border border-dashed border-zinc-300 bg-white px-6 py-12 text-center dark:border-zinc-700 dark:bg-zinc-950">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-600 dark:text-zinc-400">
        {copy.body}
      </p>
      <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
        <button
          type="button"
          onClick={onSampleEpr}
          className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
        >
          {copy.sampleEpr}
        </button>
        <button
          type="button"
          onClick={onSampleSpr}
          className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
        >
          {copy.sampleSpr}
        </button>
      </div>
    </div>
  );
}
