"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  InstructionSetEditor,
  type ThreadTypeOption,
} from "@/components/instructions/instruction-set-editor";
import { api } from "@/lib/api";
import type {
  ActivityLibraryEntryResponse,
  TaskThreadTypeInstructionResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type TaskInstructionPanelProps = {
  locale: Locale;
  taskId: string;
  moduleType: string;
};

type PanelTab = "task" | "thread_addendum";

export function TaskInstructionPanel({ locale, taskId, moduleType }: TaskInstructionPanelProps) {
  const [activeTab, setActiveTab] = useState<PanelTab>("task");
  const [taskThreadType, setTaskThreadType] = useState<string | null>(null);
  const [addendumThreadType, setAddendumThreadType] = useState<string>("");
  const [addendumDraft, setAddendumDraft] = useState("");
  const [addendumEditing, setAddendumEditing] = useState(false);
  const [addendumError, setAddendumError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: activityEntries } = useQuery({
    queryKey: ["activity-library", moduleType],
    queryFn: () =>
      api.get<ActivityLibraryEntryResponse[]>(
        `/activity-library?module_type=${encodeURIComponent(moduleType)}`,
      ),
  });

  const threadTypeOptions = useMemo<ThreadTypeOption[]>(() => {
    const allLabel =
      locale === "he" ? "כל סוגי השרשורים" : "All thread types";
    const options: ThreadTypeOption[] = [{ value: null, label: allLabel }];
    for (const entry of activityEntries ?? []) {
      options.push({ value: entry.thread_type, label: entry.display_name });
    }
    return options;
  }, [activityEntries, locale]);

  const resolvedAddendumType =
    addendumThreadType || activityEntries?.[0]?.thread_type || "";

  const { data: addendum, isLoading: addendumLoading } = useQuery({
    queryKey: ["instructions", "task", taskId, "thread-addendum", resolvedAddendumType],
    queryFn: () =>
      api.get<TaskThreadTypeInstructionResponse | null>(
        `/instructions/tasks/${taskId}/thread-types/${encodeURIComponent(resolvedAddendumType)}`,
      ),
    enabled: Boolean(resolvedAddendumType) && activeTab === "thread_addendum",
  });

  const upsertAddendumMutation = useMutation({
    mutationFn: (content: string) =>
      api.put<TaskThreadTypeInstructionResponse>(
        `/instructions/tasks/${taskId}/thread-types/${encodeURIComponent(resolvedAddendumType)}`,
        { content },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["instructions", "task", taskId, "thread-addendum"],
      });
      setAddendumEditing(false);
      setAddendumError(null);
    },
    onError: (error: Error) => setAddendumError(error.message),
  });

  const copy =
    locale === "he"
      ? {
          title: "הוראות Task",
          taskTab: "רמת Task",
          addendumTab: "תוספת לפי thread",
          taskSubtitle:
            "הוראות ברמת המשימה — נכללות בכל השרשורים. ניתן להגביל לסוג thread ספציפי.",
          addendumSubtitle:
            "תוספת קצרה לסוג thread מסוים (לא מנוהל בגרסאות). מצטרפת להוראות Task ברמת אותו thread.",
          threadType: "סוג thread",
          edit: "ערוך",
          save: "שמור",
          saving: "שומר…",
          cancel: "ביטול",
          content: "תוכן ההוראות",
          noAddendum: "אין תוספת עדיין לסוג thread זה.",
          loading: "טוען…",
        }
      : {
          title: "Task instructions",
          taskTab: "Task level",
          addendumTab: "Per thread type",
          taskSubtitle:
            "Task-wide instructions included in every thread. Optionally scope to one thread type.",
          addendumSubtitle:
            "Short addendum for a specific thread type (not versioned). Merged with task-level instructions for that thread type.",
          threadType: "Thread type",
          edit: "Edit",
          save: "Save",
          saving: "Saving…",
          cancel: "Cancel",
          content: "Instruction content",
          noAddendum: "No addendum yet for this thread type.",
          loading: "Loading…",
        };

  const basePath = `/instructions/tasks/${taskId}`;

  function startAddendumEdit() {
    setAddendumDraft(addendum?.content ?? "");
    setAddendumEditing(true);
    setAddendumError(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
        <button
          type="button"
          onClick={() => setActiveTab("task")}
          className={`rounded-lg px-3 py-2 text-sm font-medium ${
            activeTab === "task"
              ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
              : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
          }`}
        >
          {copy.taskTab}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("thread_addendum")}
          className={`rounded-lg px-3 py-2 text-sm font-medium ${
            activeTab === "thread_addendum"
              ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
              : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
          }`}
        >
          {copy.addendumTab}
        </button>
      </div>

      {activeTab === "task" ? (
        <InstructionSetEditor
          locale={locale}
          queryKey={["instructions", "task", taskId, "level"]}
          fetchPath={basePath}
          createPath={basePath}
          activatePath={`${basePath}/activate`}
          title={copy.title}
          subtitle={copy.taskSubtitle}
          threadTypeOptions={threadTypeOptions}
          selectedThreadType={taskThreadType}
          onThreadTypeChange={setTaskThreadType}
        />
      ) : (
        <section className="space-y-4 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          <div className="space-y-1 text-start">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {copy.addendumTab}
            </h2>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{copy.addendumSubtitle}</p>
          </div>

          <div className="space-y-2 text-start">
            <label htmlFor="addendum-thread-type" className="block text-sm font-medium">
              {copy.threadType}
            </label>
            <select
              id="addendum-thread-type"
              value={resolvedAddendumType}
              onChange={(event) => {
                setAddendumThreadType(event.target.value);
                setAddendumEditing(false);
              }}
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {(activityEntries ?? []).map((entry) => (
                <option key={entry.id} value={entry.thread_type}>
                  {entry.display_name}
                </option>
              ))}
            </select>
          </div>

          {addendumLoading ? (
            <p className="text-sm text-zinc-500">{copy.loading}</p>
          ) : addendumEditing ? (
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                if (!addendumDraft.trim()) {
                  return;
                }
                upsertAddendumMutation.mutate(addendumDraft.trim());
              }}
            >
              <textarea
                required
                rows={10}
                value={addendumDraft}
                onChange={(event) => setAddendumDraft(event.target.value)}
                className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
              {addendumError ? (
                <p className="text-sm text-red-600 dark:text-red-400">{addendumError}</p>
              ) : null}
              <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setAddendumEditing(false)}
                  className="inline-flex h-10 items-center justify-center rounded-lg border px-4 text-sm"
                >
                  {copy.cancel}
                </button>
                <button
                  type="submit"
                  disabled={upsertAddendumMutation.isPending}
                  className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {upsertAddendumMutation.isPending ? copy.saving : copy.save}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={startAddendumEdit}
                  className="inline-flex h-9 items-center rounded-lg border px-3 text-sm font-medium"
                >
                  {copy.edit}
                </button>
              </div>
              <div className="rounded-lg bg-zinc-50 p-4 text-start dark:bg-zinc-900">
                {addendum?.content ? (
                  <pre className="whitespace-pre-wrap font-mono text-sm">{addendum.content}</pre>
                ) : (
                  <p className="text-sm text-zinc-500">{copy.noAddendum}</p>
                )}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
