"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { api } from "@/lib/api";
import type { CreateCollectionRequest, KBCollectionResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type NewCollectionModalProps = {
  locale: Locale;
  open: boolean;
  onClose: () => void;
};

export function NewCollectionModal({ locale, open, onClose }: NewCollectionModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const titleId = useId();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "אוסף חדש",
          name: "שם",
          description: "תיאור (אופציונלי)",
          cancel: "ביטול",
          create: "צור אוסף",
          creating: "יוצר…",
        }
      : {
          title: "New Collection",
          name: "Name",
          description: "Description (optional)",
          cancel: "Cancel",
          create: "Create Collection",
          creating: "Creating…",
        };

  useEffect(() => {
    if (!open) {
      setName("");
      setDescription("");
      setError(null);
    }
  }, [open]);

  const createMutation = useMutation({
    mutationFn: (payload: CreateCollectionRequest) =>
      api.post<KBCollectionResponse>("/kb/collections", payload),
    onSuccess: (collection) => {
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      onClose();
      router.push(`/${locale}/kb/${collection.id}`);
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
      description: description.trim() ? description.trim() : null,
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
        <h2
          id={titleId}
          className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50"
        >
          {copy.title}
        </h2>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2 text-start">
            <label
              htmlFor="collection-name"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.name}
            </label>
            <input
              id="collection-name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            />
          </div>

          <div className="space-y-2 text-start">
            <label
              htmlFor="collection-description"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.description}
            </label>
            <textarea
              id="collection-description"
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            />
          </div>

          {error ? (
            <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
          ) : null}

          <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
            >
              {copy.cancel}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
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
