"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useId, useState } from "react";

import { api } from "@/lib/api";
import type {
  AttachCollectionRequest,
  ClusterReferenceCollectionResponse,
  KBCollectionResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ClusterReferenceCollectionsPanelProps = {
  locale: Locale;
  clusterId: string;
};

export function ClusterReferenceCollectionsPanel({
  locale,
  clusterId,
}: ClusterReferenceCollectionsPanelProps) {
  const queryClient = useQueryClient();
  const attachTitleId = useId();
  const [attachOpen, setAttachOpen] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [attachError, setAttachError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          referenceTitle: "מאגר ידע לעיון",
          referenceDescription:
            "חומרי עזר (מדריכים, rubric, מאמרי רקע) המשותפים לכל ההגשות. נשלפים דרך RAG בשרשורי הבדיקה.",
          noReferences: "לא מצורף מאגר ידע.",
          attachReference: "צרף מאגר",
          attachTitle: "צרף מאגר ידע",
          selectCollection: "בחר אוסף",
          attachAction: "צרף",
          attaching: "מצרף…",
          remove: "הסר",
          removing: "מסיר…",
          confirmDetach: "להסיר את הקישור למאגר זה?",
          cancel: "ביטול",
          documents: "מסמכים",
        }
      : {
          referenceTitle: "Reference knowledge base",
          referenceDescription:
            "Supporting material (guides, rubrics, background reading) shared across all submissions. Retrieved via RAG in review threads.",
          noReferences: "No reference collections attached.",
          attachReference: "Attach collection",
          attachTitle: "Attach reference collection",
          selectCollection: "Select collection",
          attachAction: "Attach",
          attaching: "Attaching…",
          remove: "Remove",
          removing: "Removing…",
          confirmDetach: "Remove this collection from the assignment?",
          cancel: "Cancel",
          documents: "documents",
        };

  const { data: referenceCollections = [] } = useQuery({
    queryKey: ["cluster-reference-collections", clusterId],
    queryFn: () =>
      api.get<ClusterReferenceCollectionResponse[]>(
        `/clusters/${clusterId}/reference-collections`,
      ),
  });

  const { data: kbCollections = [] } = useQuery({
    queryKey: ["kb-collections"],
    queryFn: () => api.get<KBCollectionResponse[]>("/kb/collections"),
    enabled: attachOpen,
  });

  const attachMutation = useMutation({
    mutationFn: (payload: { collectionId: string; body: AttachCollectionRequest }) =>
      api.post(`/kb/collections/${payload.collectionId}/attach`, payload.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cluster-reference-collections", clusterId] });
      queryClient.invalidateQueries({ queryKey: ["task-reference-collections"] });
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      setAttachOpen(false);
      setSelectedCollectionId("");
      setAttachError(null);
    },
    onError: (mutationError: Error) => setAttachError(mutationError.message),
  });

  const detachMutation = useMutation({
    mutationFn: (payload: { collectionId: string; attachmentId: string }) =>
      api.delete(`/kb/collections/${payload.collectionId}/attach/${payload.attachmentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cluster-reference-collections", clusterId] });
      queryClient.invalidateQueries({ queryKey: ["task-reference-collections"] });
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
    },
  });

  function handleAttachSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAttachError(null);
    if (!selectedCollectionId) {
      return;
    }
    attachMutation.mutate({
      collectionId: selectedCollectionId,
      body: { entity_type: "cluster", entity_id: clusterId },
    });
  }

  function handleDetach(collection: ClusterReferenceCollectionResponse) {
    if (!window.confirm(copy.confirmDetach)) {
      return;
    }
    detachMutation.mutate({
      collectionId: collection.id,
      attachmentId: collection.attachment_id,
    });
  }

  const attachedCollectionIds = new Set(referenceCollections.map((collection) => collection.id));
  const availableCollections = kbCollections.filter(
    (collection) => !attachedCollectionIds.has(collection.id),
  );

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            {copy.referenceTitle}
          </h2>
          <p className="mt-1 text-start text-xs text-zinc-500 dark:text-zinc-400">
            {copy.referenceDescription}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAttachOpen(true)}
          className="shrink-0 rounded-lg border border-zinc-200 px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
        >
          {copy.attachReference}
        </button>
      </div>

      <ul className="mt-4 space-y-2">
        {referenceCollections.length === 0 ? (
          <li className="text-start text-sm text-zinc-500 dark:text-zinc-400">
            {copy.noReferences}
          </li>
        ) : (
          referenceCollections.map((collection) => (
            <li
              key={collection.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-zinc-100 p-3 dark:border-zinc-800"
            >
              <Link
                href={`/${locale}/kb/${collection.id}`}
                className="min-w-0 flex-1 transition hover:opacity-80"
              >
                <div className="text-start">
                  <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                    KB
                  </span>
                  <p className="mt-1 text-sm font-medium text-zinc-900 dark:text-zinc-50">
                    {collection.name}
                  </p>
                  {collection.description ? (
                    <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">
                      {collection.description}
                    </p>
                  ) : null}
                  <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                    {collection.document_count} {copy.documents}
                  </p>
                </div>
              </Link>
              <button
                type="button"
                onClick={() => handleDetach(collection)}
                disabled={detachMutation.isPending}
                className="shrink-0 text-xs font-medium text-red-600 hover:underline dark:text-red-400"
              >
                {detachMutation.isPending ? copy.removing : copy.remove}
              </button>
            </li>
          ))
        )}
      </ul>

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
            <form className="mt-4 space-y-4" onSubmit={handleAttachSubmit}>
              <label className="block text-start text-sm">
                <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
                  {copy.selectCollection}
                </span>
                <select
                  value={selectedCollectionId}
                  onChange={(event) => setSelectedCollectionId(event.target.value)}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                  required
                >
                  <option value="">—</option>
                  {availableCollections.map((collection) => (
                    <option key={collection.id} value={collection.id}>
                      {collection.name}
                    </option>
                  ))}
                </select>
              </label>
              {attachError ? (
                <p className="text-start text-sm text-red-600 dark:text-red-400">{attachError}</p>
              ) : null}
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAttachOpen(false)}
                  className="rounded-lg px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
                >
                  {copy.cancel}
                </button>
                <button
                  type="submit"
                  disabled={attachMutation.isPending || !selectedCollectionId}
                  className="rounded-lg bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {attachMutation.isPending ? copy.attaching : copy.attachAction}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
