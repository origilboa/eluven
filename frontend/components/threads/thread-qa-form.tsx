"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { QAQuestionResponse, SubmitQARequest } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ThreadQaFormProps = {
  locale: Locale;
  taskId: string;
  threadId: string;
  questions: QAQuestionResponse[];
};

export function ThreadQaForm({ locale, taskId, threadId, questions }: ThreadQaFormProps) {
  const router = useRouter();
  const openingQuestions = questions.filter((question) => question.stage === "opening");
  const [answers, setAnswers] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const question of openingQuestions) {
      initial[question.id] = question.response_text ?? "";
    }
    return initial;
  });
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "שאלות פתיחה",
          subtitle: "ענה על השאלות לפני תחילת השרשור.",
          continue: "המשך לשרשור",
          submitting: "שומר…",
        }
      : {
          title: "Opening questions",
          subtitle: "Answer these before starting the thread.",
          continue: "Continue to thread",
          submitting: "Saving…",
        };

  const submitMutation = useMutation({
    mutationFn: (payload: SubmitQARequest) =>
      api.post<QAQuestionResponse[]>(`/threads/${threadId}/qa`, payload),
    onSuccess: () => {
      router.push(`/${locale}/tasks/${taskId}/threads/${threadId}`);
      router.refresh();
    },
    onError: (mutationError: Error) => {
      setError(mutationError.message);
    },
  });

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const payload: SubmitQARequest = {
      responses: openingQuestions.map((question) => ({
        question_id: question.id,
        response_text: answers[question.id]?.trim() || null,
      })),
    };

    submitMutation.mutate(payload);
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <div className="text-start">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {openingQuestions.map((question) => (
          <div key={question.id} className="space-y-2 text-start">
            <label
              htmlFor={`qa-${question.id}`}
              className="block text-sm font-medium text-zinc-800 dark:text-zinc-200"
            >
              {question.question_text}
            </label>
            <textarea
              id={`qa-${question.id}`}
              required={question.is_required}
              rows={3}
              value={answers[question.id] ?? ""}
              onChange={(event) =>
                setAnswers((current) => ({
                  ...current,
                  [question.id]: event.target.value,
                }))
              }
              className="block w-full rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            />
          </div>
        ))}

        {error ? (
          <p
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={submitMutation.isPending}
          className="inline-flex h-11 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
        >
          {submitMutation.isPending ? copy.submitting : copy.continue}
        </button>
      </form>
    </div>
  );
}
