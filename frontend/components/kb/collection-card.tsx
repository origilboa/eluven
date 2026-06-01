"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { api } from "@/lib/api";
import type {
  AttachCollectionRequest,
  ClusterResponse,
  KBCollectionResponse,
  TaskResponse,
  UpdateCollectionRequest,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type CollectionCardProps = {
  collection: KBCollectionResponse;
  locale: Locale;
};

function attachmentLabel(
  entityType: string,
  entityName: string,
  locale: Locale,
): string {
  if (locale === "he") {
    return entityType === "cluster" ? `קבוצה: ${entityName}` : `משימה: ${entityName}`;
  }
  return entityType === "cluster" ? `Cluster: ${entityName}` : `Task: ${entityName}`;
}

export function CollectionCard({ collection, locale }: CollectionCardProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const renameTitleId = useId();
  const attachTitleId = useId();

  const [menuOpen, setMenuOpen] = useState(false);
  const [renameOpen, setRenameOpen] = useState(false);
  const [attachOpen, setAttachOpen] = useState(false);
  const [name, setName] = useState(collection.name);
  const [description, setDescription] = useState(collection.description ?? "");
  const [entityType, setEntityType] = useState<"task" | "cluster">("task");
  const [entityId, setEntityId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          documents: "מסמכים",
          attachments: "צירופים",
          actions: "פעולות",
          rename: "שנה שם",
          delete: "מחק",
          attach: "צרף למשימה/קבוצה",
          cancel: "ביטול",
          save: "שמור",
          saving: "שומר…",
          attachTitle: "צרף אוסף",
          entityType: "סוג יעד",
          task: "משימה",
          cluster: "קבוצה",
          target: "יעד",
          attachAction: "צרף",
          attaching: "מצרף…",
          confirmDelete: "למחוק את האוסף?",
          noAttachments: "לא מצורף",
        }
      : {
          documents: "documents",
          attachments: "attachments",
          actions: "Actions",
          rename: "Rename",
          delete: "Delete",
          attach: "Attach to task/cluster",
          cancel: "Cancel",
          save: "Save",
          saving: "Saving…",
          attachTitle: "Attach collection",
          entityType: "Target type",
          task: "Task",
          cluster: "Cluster",
          target: "Target",
          attachAction: "Attach",
          attaching: "Attaching…",
          confirmDelete: "Delete this collection?",
          noAttachments: "Not attached",
        };

  const { data: tasks = [] } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => api.get<TaskResponse[]>("/tasks"),
    enabled: attachOpen,
  });

  const { data: clusters = [] } = useQuery({
    queryKey: ["clusters"],
    queryFn: () => api.get<ClusterResponse[]>("/clusters"),
    enabled: attachOpen,
  });

  const renameMutation = useMutation({
    mutationFn: (payload: UpdateCollectionRequest) =>
      api.patch<KBCollectionResponse>(`/kb/collections/${collection.id}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      setRenameOpen(false);
      router.refresh();
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/kb/collections/${collection.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      router.refresh();
    },
    onError: (mutationError: Error) => {
      window.alert(mutationError.message);
    },
  });

  const attachMutation = useMutation({
    mutationFn: (payload: AttachCollectionRequest) =>
      api.post(`/kb/collections/${collection.id}/attach`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      setAttachOpen(false);
      setEntityId("");
      router.refresh();
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const documentLabel =
    locale === "he"
      ? `${collection.document_count} מסמכים`
      : `${collection.document_count} document${collection.document_count === 1 ? "" : "s"}`;

  const attachmentCountLabel =
    locale === "he"
      ? `${collection.attachments.length} צירופים`
      : `${collection.attachments.length} attachment${collection.attachments.length === 1 ? "" : "s"}`;

  function handleRenameSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    renameMutation.mutate({
      name: name.trim(),
      description: description.trim() ? description.trim() : null,
    });
  }

  function handleAttachSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!entityId) {
      return;
    }
    attachMutation.mutate({ entity_type: entityType, entity_id: entityId });
  }

  function handleDelete() {
    if (!window.confirm(copy.confirmDelete)) {
      return;
    }
    deleteMutation.mutate();
  }

  const targetOptions = entityType === "task" ? tasks : clusters;

  return (
    <>
      <article className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 text-start">
            <Link
              href={`/${locale}/kb/${collection.id}`}
              className="block truncate text-base font-semibold text-zinc-900 hover:text-zinc-700 dark:text-zinc-50 dark:hover:text-zinc-200"
            >
              {collection.name}
            </Link>
            {collection.description ? (
              <p className="mt-1 line-clamp-2 text-sm text-zinc-600 dark:text-zinc-400">
                {collection.description}
              </p>
            ) : null}
          </div>

          <div className="relative">
            <button
              type="button"
              aria-label={copy.actions}
              onClick={() => setMenuOpen((current) => !current)}
              className="inline-flex size-8 items-center justify-center rounded-lg border border-zinc-300 text-zinc-600 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
            >
              ⋯
            </button>
            {menuOpen ? (
              <div className="absolute end-0 z-10 mt-1 w-48 rounded-lg border border-zinc-200 bg-white py-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-950">
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-start text-sm text-zinc-700 hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-900"
                  onClick={() => {
                    setMenuOpen(false);
                    setName(collection.name);
                    setDescription(collection.description ?? "");
                    setRenameOpen(true);
                  }}
                >
                  {copy.rename}
                </button>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-start text-sm text-zinc-700 hover:bg-zinc-50 dark:text-zinc-200 dark:hover:bg-zinc-900"
                  onClick={() => {
                    setMenuOpen(false);
                    setAttachOpen(true);
                  }}
                >
                  {copy.attach}
                </button>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-start text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
                  onClick={() => {
                    setMenuOpen(false);
                    handleDelete();
                  }}
                >
                  {copy.delete}
                </button>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 text-start">
          <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
            {documentLabel}
          </span>
          <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
            {attachmentCountLabel}
          </span>
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-start">
          {collection.attachments.length === 0 ? (
            <span className="text-xs text-zinc-500 dark:text-zinc-400">{copy.noAttachments}</span>
          ) : (
            collection.attachments.map((attachment) => (
              <span
                key={attachment.id}
                className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20 dark:bg-blue-950 dark:text-blue-300"
              >
                {attachmentLabel(attachment.entity_type, attachment.entity_name, locale)}
              </span>
            ))
          )}
        </div>
      </article>

      {renameOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/50 px-4"
          role="presentation"
          onClick={() => setRenameOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={renameTitleId}
            className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-950"
            onClick={(event) => event.stopPropagation()}
          >
            <h2
              id={renameTitleId}
              className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50"
            >
              {copy.rename}
            </h2>
            <form className="mt-6 space-y-4" onSubmit={handleRenameSubmit}>
              <div className="space-y-2 text-start">
                <label htmlFor={`rename-name-${collection.id}`} className="block text-sm font-medium">
                  {locale === "he" ? "שם" : "Name"}
                </label>
                <input
                  id={`rename-name-${collection.id}`}
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </div>
              <div className="space-y-2 text-start">
                <label
                  htmlFor={`rename-description-${collection.id}`}
                  className="block text-sm font-medium"
                >
                  {locale === "he" ? "תיאור" : "Description"}
                </label>
                <textarea
                  id={`rename-description-${collection.id}`}
                  rows={3}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </div>
              {error ? (
                <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
              ) : null}
              <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setRenameOpen(false)}
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium"
                >
                  {copy.cancel}
                </button>
                <button
                  type="submit"
                  disabled={renameMutation.isPending}
                  className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {renameMutation.isPending ? copy.saving : copy.save}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {attachOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/50 px-4"
          role="presentation"
          onClick={() => setAttachOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={attachTitleId}
            className="w-full max-w-lg rounded-2xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-800 dark:bg-zinc-950"
            onClick={(event) => event.stopPropagation()}
          >
            <h2
              id={attachTitleId}
              className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50"
            >
              {copy.attachTitle}
            </h2>
            <form className="mt-6 space-y-4" onSubmit={handleAttachSubmit}>
              <div className="space-y-2 text-start">
                <label htmlFor={`attach-type-${collection.id}`} className="block text-sm font-medium">
                  {copy.entityType}
                </label>
                <select
                  id={`attach-type-${collection.id}`}
                  value={entityType}
                  onChange={(event) => {
                    setEntityType(event.target.value as "task" | "cluster");
                    setEntityId("");
                  }}
                  className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                >
                  <option value="task">{copy.task}</option>
                  <option value="cluster">{copy.cluster}</option>
                </select>
              </div>
              <div className="space-y-2 text-start">
                <label htmlFor={`attach-target-${collection.id}`} className="block text-sm font-medium">
                  {copy.target}
                </label>
                <select
                  id={`attach-target-${collection.id}`}
                  required
                  value={entityId}
                  onChange={(event) => setEntityId(event.target.value)}
                  className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                >
                  <option value="">{locale === "he" ? "בחר…" : "Select…"}</option>
                  {targetOptions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {"title" in item ? item.title : item.name}
                    </option>
                  ))}
                </select>
              </div>
              {error ? (
                <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
              ) : null}
              <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setAttachOpen(false)}
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium"
                >
                  {copy.cancel}
                </button>
                <button
                  type="submit"
                  disabled={attachMutation.isPending}
                  className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {attachMutation.isPending ? copy.attaching : copy.attachAction}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
}
