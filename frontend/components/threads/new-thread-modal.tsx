"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { api } from "@/lib/api";
import { hasPendingOpeningQA } from "@/lib/threads";
import type {
  ActivityLibraryEntryResponse,
  CreateThreadRequest,
  QAQuestionResponse,
  ThreadResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type NewThreadModalProps = {
  locale: Locale;
  taskId: string;
  moduleType: string;
  defaultWorkingLanguage: string | null;
  open: boolean;
  onClose: () => void;
};

type FormState = {
  thread_type: string;
  title: string;
  working_language: "en" | "he";
};

export function NewThreadModal({
  locale,
  taskId,
  moduleType,
  defaultWorkingLanguage,
  open,
  onClose,
}: NewThreadModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const titleId = useId();
  const [form, setForm] = useState<FormState>({
    thread_type: "",
    title: "",
    working_language: (defaultWorkingLanguage === "he" ? "he" : "en") as "en" | "he",
  });
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "שרשור חדש",
          threadType: "סוג שרשור",
          threadTitle: "כותרת (אופציונלי)",
          workingLanguage: "שפת עבודה",
          english: "אנגלית",
          hebrew: "עברית",
          cancel: "ביטול",
          create: "יצירת שרשור",
          creating: "יוצר…",
          loadTypes: "טוען סוגי שרשור…",
        }
      : {
          title: "New Thread",
          threadType: "Thread type",
          threadTitle: "Title (optional)",
          workingLanguage: "Working language",
          english: "English",
          hebrew: "Hebrew",
          cancel: "Cancel",
          create: "Create thread",
          creating: "Creating…",
          loadTypes: "Loading thread types…",
        };

  const activityQuery = useQuery({
    queryKey: ["activity-library", moduleType],
    queryFn: () =>
      api.get<ActivityLibraryEntryResponse[]>(
        `/activity-library?module_type=${encodeURIComponent(moduleType)}`,
      ),
    enabled: open,
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    setError(null);
    setForm({
      thread_type: activityQuery.data?.[0]?.thread_type ?? "",
      title: "",
      working_language: (defaultWorkingLanguage === "he" ? "he" : "en") as "en" | "he",
    });
  }, [activityQuery.data, defaultWorkingLanguage, open]);

  useEffect(() => {
    if (activityQuery.data?.[0]?.thread_type && !form.thread_type) {
      setForm((current) => ({
        ...current,
        thread_type: activityQuery.data[0].thread_type,
      }));
    }
  }, [activityQuery.data, form.thread_type]);

  const createMutation = useMutation({
    mutationFn: (payload: CreateThreadRequest) =>
      api.post<ThreadResponse>(`/tasks/${taskId}/threads`, payload),
    onSuccess: async (thread) => {
      await queryClient.invalidateQueries({ queryKey: ["threads", taskId] });
      onClose();

      const qaQuestions = await api.get<QAQuestionResponse[]>(`/threads/${thread.id}/qa`);
      if (hasPendingOpeningQA(qaQuestions)) {
        router.push(`/${locale}/tasks/${taskId}/threads/${thread.id}/qa`);
        return;
      }

      router.push(`/${locale}/tasks/${taskId}/threads/${thread.id}`);
      router.refresh();
    },
    onError: (mutationError: Error) => {
      setError(mutationError.message);
    },
  });

  if (!open) {
    return null;
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const payload: CreateThreadRequest = {
      thread_type: form.thread_type,
      working_language: form.working_language,
    };
    if (form.title.trim()) {
      payload.title = form.title.trim();
    }

    createMutation.mutate(payload);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/50 px-4"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-950"
        onClick={(event) => event.stopPropagation()}
      >
        <h2
          id={titleId}
          className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50"
        >
          {copy.title}
        </h2>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2 text-start">
            <label
              htmlFor="thread-type"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.threadType}
            </label>
            <select
              id="thread-type"
              required
              disabled={activityQuery.isLoading}
              value={form.thread_type}
              onChange={(event) =>
                setForm((current) => ({ ...current, thread_type: event.target.value }))
              }
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            >
              {activityQuery.data?.map((entry) => (
                <option key={entry.id} value={entry.thread_type}>
                  {entry.display_name}
                </option>
              ))}
            </select>
            {activityQuery.isLoading ? (
              <p className="text-xs text-zinc-500">{copy.loadTypes}</p>
            ) : null}
          </div>

          <div className="space-y-2 text-start">
            <label
              htmlFor="thread-title"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.threadTitle}
            </label>
            <input
              id="thread-title"
              value={form.title}
              onChange={(event) =>
                setForm((current) => ({ ...current, title: event.target.value }))
              }
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            />
          </div>

          <div className="space-y-2 text-start">
            <label
              htmlFor="thread-working-language"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.workingLanguage}
            </label>
            <select
              id="thread-working-language"
              value={form.working_language}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  working_language: event.target.value as "en" | "he",
                }))
              }
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            >
              <option value="en">{copy.english}</option>
              <option value="he">{copy.hebrew}</option>
            </select>
          </div>

          {error ? (
            <p
              className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
              role="alert"
            >
              {error}
            </p>
          ) : null}

          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
            >
              {copy.cancel}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || !form.thread_type}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
            >
              {createMutation.isPending ? copy.creating : copy.create}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
