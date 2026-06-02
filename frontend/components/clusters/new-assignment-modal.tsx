"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { api } from "@/lib/api";
import type { ClusterResponse, CreateClusterRequest } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type NewAssignmentModalProps = {
  locale: Locale;
  open: boolean;
  onClose: () => void;
};

export function NewAssignmentModal({ locale, open, onClose }: NewAssignmentModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const titleId = useId();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [workingLanguage, setWorkingLanguage] = useState<"en" | "he">("en");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "מטלה חדשה (Assignment)",
          name: "שם המטלה",
          description: "תיאור",
          language: "שפת עבודה",
          english: "אנגלית",
          hebrew: "עברית",
          cancel: "ביטול",
          create: "יצירת מטלה",
          creating: "יוצר…",
        }
      : {
          title: "New Assignment",
          name: "Assignment name",
          description: "Description",
          language: "Working language",
          english: "English",
          hebrew: "Hebrew",
          cancel: "Cancel",
          create: "Create assignment",
          creating: "Creating…",
        };

  useEffect(() => {
    if (!open) {
      return;
    }
    setName("");
    setDescription("");
    setWorkingLanguage("en");
    setError(null);
  }, [open]);

  const createMutation = useMutation({
    mutationFn: (payload: CreateClusterRequest) =>
      api.post<ClusterResponse>("/clusters", payload),
    onSuccess: async (cluster) => {
      await queryClient.invalidateQueries({ queryKey: ["clusters"] });
      onClose();
      router.push(`/${locale}/clusters/${cluster.id}`);
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
    createMutation.mutate({
      name: name.trim(),
      cluster_type: "assignment",
      description: description.trim() || null,
      working_language: workingLanguage,
    });
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
            <label htmlFor="assignment-name" className="block text-sm font-medium">
              {copy.name}
            </label>
            <input
              id="assignment-name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </div>

          <div className="space-y-2 text-start">
            <label htmlFor="assignment-description" className="block text-sm font-medium">
              {copy.description}
            </label>
            <textarea
              id="assignment-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </div>

          <div className="space-y-2 text-start">
            <label htmlFor="assignment-language" className="block text-sm font-medium">
              {copy.language}
            </label>
            <select
              id="assignment-language"
              value={workingLanguage}
              onChange={(event) => setWorkingLanguage(event.target.value as "en" | "he")}
              className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              <option value="en">{copy.english}</option>
              <option value="he">{copy.hebrew}</option>
            </select>
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
