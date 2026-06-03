"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "@/lib/api";
import type { ThreadPromptResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ThreadPromptSidebarProps = {
  locale: Locale;
  threadId: string;
  onSelectPrompt: (prompt: ThreadPromptResponse) => void;
};

export function ThreadPromptSidebar({
  locale,
  threadId,
  onSelectPrompt,
}: ThreadPromptSidebarProps) {
  const queryClient = useQueryClient();
  const [showUsed, setShowUsed] = useState(false);

  const copy =
    locale === "he"
      ? {
          title: "הצעות לשיחה",
          empty: "אין הצעות לסוג פעילות זה.",
          allUsed: "כל ההצעות כוסו — המשך בצ'אט.",
          showUsed: "הצג שנוצלו",
          hideUsed: "הסתר שנוצלו",
        }
      : {
          title: "Suggested prompts",
          empty: "No prompts for this activity type.",
          allUsed: "All suggested prompts covered — continue in chat.",
          showUsed: "Show used",
          hideUsed: "Hide used",
        };

  const promptsQuery = useQuery({
    queryKey: ["thread-prompts", threadId],
    queryFn: () => api.get<ThreadPromptResponse[]>(`/threads/${threadId}/prompts`),
  });

  const markUsedMutation = useMutation({
    mutationFn: (promptId: string) =>
      api.post<ThreadPromptResponse>(`/threads/${threadId}/prompts/${promptId}/mark-used`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["thread-prompts", threadId] });
    },
  });

  const prompts = promptsQuery.data ?? [];
  const activePrompts = useMemo(
    () => prompts.filter((prompt) => showUsed || prompt.used_at === null),
    [prompts, showUsed],
  );
  const hasUsed = prompts.some((prompt) => prompt.used_at !== null);

  if (promptsQuery.isLoading) {
    return null;
  }

  if (prompts.length === 0) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.title}
        </h2>
        {hasUsed ? (
          <button
            type="button"
            onClick={() => setShowUsed((current) => !current)}
            className="text-xs font-medium text-zinc-600 underline-offset-2 hover:underline dark:text-zinc-400"
          >
            {showUsed ? copy.hideUsed : copy.showUsed}
          </button>
        ) : null}
      </div>

      {activePrompts.length === 0 ? (
        <p className="mt-3 text-start text-sm text-zinc-500">{copy.allUsed}</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {activePrompts.map((prompt) => (
            <li key={prompt.id}>
              <button
                type="button"
                onClick={() => {
                  onSelectPrompt(prompt);
                  if (prompt.used_at === null) {
                    markUsedMutation.mutate(prompt.id);
                  }
                }}
                className="w-full rounded-xl border border-zinc-200 px-3 py-2 text-start text-sm leading-5 text-zinc-800 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                {prompt.prompt_text}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
