"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { InstructionAssistantPanel } from "@/components/instructions/instruction-assistant-panel";
import { api } from "@/lib/api";
import type {
  ActivateInstructionVersionRequest,
  CreateInstructionVersionRequest,
  InstructionAssistantScope,
  InstructionSetResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

export type ThreadTypeOption = {
  value: string | null;
  label: string;
};

type InstructionSetEditorProps = {
  locale: Locale;
  canEdit?: boolean;
  queryKey: readonly unknown[];
  fetchPath: string;
  createPath: string;
  activatePath: string;
  title: string;
  subtitle?: string;
  readOnlyMessage?: string;
  threadTypeOptions?: ThreadTypeOption[];
  selectedThreadType?: string | null;
  onThreadTypeChange?: (threadType: string | null) => void;
  assistantScope?: InstructionAssistantScope;
};

function formatTimestamp(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale === "he" ? "he-IL" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function withThreadTypeQuery(path: string, threadType: string | null | undefined): string {
  if (!threadType) {
    return path;
  }
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}thread_type=${encodeURIComponent(threadType)}`;
}

export function InstructionSetEditor({
  locale,
  canEdit = true,
  queryKey,
  fetchPath,
  createPath,
  activatePath,
  title,
  subtitle,
  readOnlyMessage,
  threadTypeOptions,
  selectedThreadType = null,
  onThreadTypeChange,
  assistantScope,
}: InstructionSetEditorProps) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draftContent, setDraftContent] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          scope: "היקף thread",
          allThreadTypes: "כל סוגי השרשורים",
          activeVersion: "גרסה פעילה",
          noActive: "אין גרסה פעילה עדיין.",
          edit: "ערוך",
          cancel: "ביטול",
          save: "שמור גרסה",
          saving: "שומר…",
          changeNote: "הערת שינוי (אופציונלי)",
          content: "תוכן ההוראות",
          history: "היסטוריית גרסאות",
          noVersions: "אין גרסאות עדיין.",
          setActive: "הגדר כפעיל",
          activating: "מגדיר…",
          activeBadge: "פעיל",
          version: "גרסה",
          readOnly: "תצוגה בלבד.",
          loading: "טוען…",
        }
      : {
          scope: "Thread scope",
          allThreadTypes: "All thread types",
          activeVersion: "Active version",
          noActive: "No active version yet.",
          edit: "Edit",
          cancel: "Cancel",
          save: "Save version",
          saving: "Saving…",
          changeNote: "Change note (optional)",
          content: "Instruction content",
          history: "Version history",
          noVersions: "No versions yet.",
          setActive: "Set as Active",
          activating: "Activating…",
          activeBadge: "Active",
          version: "Version",
          readOnly: "Read-only.",
          loading: "Loading…",
        };

  const resolvedFetchPath = withThreadTypeQuery(fetchPath, selectedThreadType);
  const resolvedCreatePath = withThreadTypeQuery(createPath, selectedThreadType);
  const resolvedActivatePath = withThreadTypeQuery(activatePath, selectedThreadType);

  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, selectedThreadType],
    queryFn: () => api.get<InstructionSetResponse>(resolvedFetchPath),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateInstructionVersionRequest) =>
      api.post<InstructionSetResponse>(resolvedCreatePath, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setEditing(false);
      setDraftContent("");
      setChangeNote("");
      setError(null);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const activateMutation = useMutation({
    mutationFn: (payload: ActivateInstructionVersionRequest) =>
      api.post<InstructionSetResponse>(resolvedActivatePath, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  function startEditing() {
    setDraftContent(data?.active_version?.content ?? "");
    setChangeNote("");
    setEditing(true);
    setError(null);
  }

  function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draftContent.trim()) {
      return;
    }
    createMutation.mutate({
      content: draftContent.trim(),
      change_note: changeNote.trim() ? changeNote.trim() : null,
    });
  }

  const activeContent = data?.active_version?.content ?? null;

  const resolvedAssistantScope = assistantScope
    ? {
        ...assistantScope,
        thread_type: assistantScope.thread_type ?? selectedThreadType,
      }
    : undefined;

  return (
    <section className="space-y-4 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="space-y-1 text-start">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{title}</h2>
        {subtitle ? (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">{subtitle}</p>
        ) : null}
      </div>

      {threadTypeOptions && onThreadTypeChange ? (
        <div className="space-y-2 text-start">
          <label htmlFor={`thread-scope-${fetchPath}`} className="block text-sm font-medium">
            {copy.scope}
          </label>
          <select
            id={`thread-scope-${fetchPath}`}
            value={selectedThreadType ?? ""}
            onChange={(event) =>
              onThreadTypeChange(event.target.value ? event.target.value : null)
            }
            className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          >
            {threadTypeOptions.map((option) => (
              <option key={option.value ?? "all"} value={option.value ?? ""}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {isLoading ? (
        <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.loading}</p>
      ) : (
        <div className="space-y-6">
          <div className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="text-start text-base font-semibold text-zinc-900 dark:text-zinc-50">
                {copy.activeVersion}
              </h3>
              {canEdit && !editing ? (
                <button
                  type="button"
                  onClick={startEditing}
                  className="inline-flex h-9 items-center justify-center rounded-lg border border-zinc-300 px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
                >
                  {copy.edit}
                </button>
              ) : null}
            </div>

            {!canEdit ? (
              <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">
                {readOnlyMessage ?? copy.readOnly}
              </p>
            ) : null}

            {editing ? (
              <div
                className={
                  resolvedAssistantScope
                    ? "grid gap-4 lg:grid-cols-2 lg:items-start"
                    : "space-y-4"
                }
              >
                <form className="space-y-4" onSubmit={handleSave}>
                  <div className="space-y-2 text-start">
                    <label
                      htmlFor={`instruction-content-${fetchPath}`}
                      className="block text-sm font-medium"
                    >
                      {copy.content}
                    </label>
                    <textarea
                      id={`instruction-content-${fetchPath}`}
                      required
                      rows={10}
                      value={draftContent}
                      onChange={(event) => setDraftContent(event.target.value)}
                      className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 font-mono text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                    />
                  </div>
                  <div className="space-y-2 text-start">
                    <label htmlFor={`instruction-note-${fetchPath}`} className="block text-sm font-medium">
                      {copy.changeNote}
                    </label>
                    <input
                      id={`instruction-note-${fetchPath}`}
                      value={changeNote}
                      onChange={(event) => setChangeNote(event.target.value)}
                      className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                    />
                  </div>
                  {error ? (
                    <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
                  ) : null}
                  <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                    <button
                      type="button"
                      onClick={() => setEditing(false)}
                      className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium"
                    >
                      {copy.cancel}
                    </button>
                    <button
                      type="submit"
                      disabled={createMutation.isPending}
                      className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                    >
                      {createMutation.isPending ? copy.saving : copy.save}
                    </button>
                  </div>
                </form>
                {resolvedAssistantScope ? (
                  <InstructionAssistantPanel
                    locale={locale}
                    scope={resolvedAssistantScope}
                    draftContent={draftContent}
                    onApplyDraft={setDraftContent}
                  />
                ) : null}
              </div>
            ) : (
              <div className="rounded-lg bg-zinc-50 p-4 text-start dark:bg-zinc-900">
                {activeContent ? (
                  <pre className="whitespace-pre-wrap font-mono text-sm text-zinc-800 dark:text-zinc-200">
                    {activeContent}
                  </pre>
                ) : (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">{copy.noActive}</p>
                )}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <h3 className="text-start text-base font-semibold text-zinc-900 dark:text-zinc-50">
              {copy.history}
            </h3>
            {!data?.versions.length ? (
              <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.noVersions}</p>
            ) : (
              <ul className="space-y-3">
                {data.versions.map((version) => (
                  <li
                    key={version.id}
                    className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div className="text-start">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                            {copy.version} {version.version_number}
                          </p>
                          {version.is_active ? (
                            <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300">
                              {copy.activeBadge}
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                          {formatTimestamp(version.created_at, locale)}
                        </p>
                        {version.change_note ? (
                          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
                            {version.change_note}
                          </p>
                        ) : null}
                      </div>
                      {canEdit && !version.is_active ? (
                        <button
                          type="button"
                          disabled={activateMutation.isPending}
                          onClick={() => activateMutation.mutate({ version_id: version.id })}
                          className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg border border-zinc-300 px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
                        >
                          {activateMutation.isPending ? copy.activating : copy.setActive}
                        </button>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
