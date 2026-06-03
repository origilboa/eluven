"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { EntityTagsEditor } from "@/components/tags/entity-tags-editor";
import { api } from "@/lib/api";
import { MODULE_DEFINITIONS, MODULE_TYPE_EXTERNAL_PAPER_REVIEW, type ModuleType } from "@/lib/modules";
import { parseFreeformTags } from "@/lib/tags";
import type { ClusterResponse, CreateTaskRequest, TaskResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type NewTaskModalProps = {
  locale: Locale;
  open: boolean;
  onClose: () => void;
  initialValues?: Partial<CreateTaskFormState>;
};

type CreateTaskFormState = {
  title: string;
  module_type: ModuleType;
  working_language: "en" | "he";
  cluster_id: string;
  structured_tags: Record<string, string>;
  freeform_tags: string;
};

const defaultFormState: CreateTaskFormState = {
  title: "",
  module_type: "external_paper_review",
  working_language: "en",
  cluster_id: "",
  structured_tags: {},
  freeform_tags: "",
};

const EPR_TAG_FIELDS = [
  { key: "venue", label: "Venue / journal" },
  { key: "review_deadline", label: "Review deadline" },
  { key: "decision_context", label: "Decision context" },
  { key: "reporting_standard", label: "Reporting standard" },
  { key: "review_type", label: "Review type" },
] as const;

export function NewTaskModal({
  locale,
  open,
  onClose,
  initialValues,
}: NewTaskModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const titleId = useId();
  const [form, setForm] = useState<CreateTaskFormState>(defaultFormState);
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "משימה חדשה",
          taskTitle: "כותרת",
          moduleType: "סוג מודול",
          workingLanguage: "שפת עבודה",
          cluster: "אשכול (אופציונלי)",
          none: "ללא אשכול",
          english: "אנגלית",
          hebrew: "עברית",
          cancel: "ביטול",
          create: "יצירת משימה",
          creating: "יוצר…",
          loadClusters: "טוען אשכולות…",
        }
      : {
          title: "New Task",
          taskTitle: "Title",
          moduleType: "Module type",
          workingLanguage: "Working language",
          cluster: "Cluster (optional)",
          none: "No cluster",
          english: "English",
          hebrew: "Hebrew",
          cancel: "Cancel",
          create: "Create task",
          creating: "Creating…",
          loadClusters: "Loading clusters…",
        };

  useEffect(() => {
    if (!open) {
      return;
    }
    setForm({
      ...defaultFormState,
      ...initialValues,
      cluster_id: initialValues?.cluster_id ?? "",
    });
    setError(null);
  }, [initialValues, open]);

  const clustersQuery = useQuery({
    queryKey: ["clusters"],
    queryFn: () => api.get<ClusterResponse[]>("/clusters"),
    enabled: open,
  });

  const createTaskMutation = useMutation({
    mutationFn: (payload: CreateTaskRequest) =>
      api.post<TaskResponse>("/tasks", payload),
    onSuccess: async (task) => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
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

    const payload: CreateTaskRequest = {
      title: form.title.trim(),
      module_type: form.module_type,
      working_language: form.working_language,
      cluster_id: form.cluster_id ? form.cluster_id : null,
    };

    if (form.module_type === MODULE_TYPE_EXTERNAL_PAPER_REVIEW) {
      const structuredTags = Object.fromEntries(
        Object.entries(form.structured_tags).filter(([, value]) => value.trim()),
      );
      if (Object.keys(structuredTags).length > 0) {
        payload.structured_tags = structuredTags;
      }
      const freeformTags = parseFreeformTags(form.freeform_tags);
      if (freeformTags.length > 0) {
        payload.freeform_tags = freeformTags;
      }
    }

    createTaskMutation.mutate(payload);
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
              htmlFor="task-title"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.taskTitle}
            </label>
            <input
              id="task-title"
              required
              value={form.title}
              onChange={(event) =>
                setForm((current) => ({ ...current, title: event.target.value }))
              }
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            />
          </div>

          <div className="space-y-2 text-start">
            <label
              htmlFor="module-type"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.moduleType}
            </label>
            <select
              id="module-type"
              value={form.module_type}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  module_type: event.target.value as ModuleType,
                }))
              }
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            >
              {MODULE_DEFINITIONS.map((module) => (
                <option key={module.value} value={module.value}>
                  {module.label[locale]}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2 text-start">
            <label
              htmlFor="working-language"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.workingLanguage}
            </label>
            <select
              id="working-language"
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

          <div className="space-y-2 text-start">
            <label
              htmlFor="cluster-id"
              className="block text-sm font-medium text-zinc-700 dark:text-zinc-300"
            >
              {copy.cluster}
            </label>
            <select
              id="cluster-id"
              value={form.cluster_id}
              disabled={clustersQuery.isLoading}
              onChange={(event) =>
                setForm((current) => ({ ...current, cluster_id: event.target.value }))
              }
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            >
              <option value="">{copy.none}</option>
              {clustersQuery.data?.map((cluster) => (
                <option key={cluster.id} value={cluster.id}>
                  {cluster.name}
                </option>
              ))}
            </select>
            {clustersQuery.isLoading ? (
              <p className="text-xs text-zinc-500">{copy.loadClusters}</p>
            ) : null}
          </div>

          {form.module_type === MODULE_TYPE_EXTERNAL_PAPER_REVIEW ? (
            <EntityTagsEditor
              locale={locale}
              structuredTags={form.structured_tags}
              freeformTags={form.freeform_tags}
              onStructuredTagsChange={(structured_tags) =>
                setForm((current) => ({ ...current, structured_tags }))
              }
              onFreeformTagsChange={(freeform_tags) =>
                setForm((current) => ({ ...current, freeform_tags }))
              }
              structuredFields={EPR_TAG_FIELDS.map((field) => ({
                key: field.key,
                label: field.label,
              }))}
            />
          ) : null}

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
              disabled={createTaskMutation.isPending}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
            >
              {createTaskMutation.isPending ? copy.creating : copy.create}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
