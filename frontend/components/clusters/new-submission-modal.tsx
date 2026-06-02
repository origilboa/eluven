"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { api } from "@/lib/api";
import type { CreateSubmissionRequest, TaskResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type NewSubmissionModalProps = {
  locale: Locale;
  clusterId: string;
  open: boolean;
  onClose: () => void;
};

export function NewSubmissionModal({
  locale,
  clusterId,
  open,
  onClose,
}: NewSubmissionModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const titleId = useId();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "הגשה חדשה",
          submissionTitle: "שם ההגשה",
          cancel: "ביטול",
          create: "יצירת הגשה",
          creating: "יוצר…",
        }
      : {
          title: "New Submission",
          submissionTitle: "Submission title",
          cancel: "Cancel",
          create: "Create submission",
          creating: "Creating…",
        };

  useEffect(() => {
    if (!open) {
      return;
    }
    setTitle("");
    setError(null);
  }, [open]);

  const createMutation = useMutation({
    mutationFn: (payload: CreateSubmissionRequest) =>
      api.post<TaskResponse>(`/clusters/${clusterId}/submissions`, payload),
    onSuccess: async (task) => {
      await queryClient.invalidateQueries({ queryKey: ["cluster-submissions", clusterId] });
      onClose();
      router.push(`/${locale}/tasks/${task.id}`);
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
    createMutation.mutate({ title: title.trim() });
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
        <h2 id={titleId} className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.title}
        </h2>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2 text-start">
            <label htmlFor="submission-title" className="block text-sm font-medium">
              {copy.submissionTitle}
            </label>
            <input
              id="submission-title"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </div>

          {error ? (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          ) : null}

          <div className="flex flex-col-reverse gap-3 pt-2 sm:flex-row sm:justify-end">
            <button type="button" onClick={onClose} className="rounded-lg border px-4 py-2 text-sm">
              {copy.cancel}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {createMutation.isPending ? copy.creating : copy.create}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
