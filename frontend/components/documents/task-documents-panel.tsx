"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useId, useRef, useState } from "react";

import { api } from "@/lib/api";
import {
  DOCUMENT_MAX_UPLOAD_BYTES,
  DOCUMENT_UPLOAD_ACCEPT,
  documentStatusClasses,
  documentStatusLabel,
  fileTypeIcon,
} from "@/lib/document-status";
import type {
  AttachCollectionRequest,
  DocumentDownloadUrlResponse,
  KBCollectionResponse,
  TaskDocumentResponse,
  TaskReferenceCollectionResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type TaskDocumentsPanelProps = {
  locale: Locale;
  taskId: string;
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function TaskDocumentsPanel({ locale, taskId }: TaskDocumentsPanelProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachTitleId = useId();
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [attachOpen, setAttachOpen] = useState(false);
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [attachError, setAttachError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          paperTitle: "מסמכים לבדיקה",
          paperDescription:
            "המאמרים או ההגשות שאתה בודק. מוזרקים כטקסט מלא ל-AI בכל השרשורים במשימה.",
          referenceTitle: "מאגר ידע לעיון",
          referenceDescription:
            "חומרי עזר (מדריכים, רubric, מאמרי רקע). נשלפים דרך RAG בצ׳אט — לא המסמך עצמו.",
          upload: "העלה מסמך",
          uploading: "מעלה…",
          noPaper: "לא הועלו מסמכים לבדיקה.",
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
          download: "הורד",
          clusterBadge: "מקבץ",
          taskBadge: "משימה",
          clusterNote: "מצורף ברמת מקבץ — הסר מדף מאגר הידע",
          documents: "מסמכים",
          maxSize: "גודל מקסימלי: 50MB",
        }
      : {
          paperTitle: "Papers under review",
          paperDescription:
            "Manuscripts or submissions you are reviewing. Injected as full text for AI in all threads on this task.",
          referenceTitle: "Reference knowledge base",
          referenceDescription:
            "Supporting material (guides, rubrics, background reading). Retrieved via RAG in chat — not the papers themselves.",
          upload: "Upload paper",
          uploading: "Uploading…",
          noPaper: "No papers uploaded yet.",
          noReferences: "No reference collections attached.",
          attachReference: "Attach collection",
          attachTitle: "Attach reference collection",
          selectCollection: "Select collection",
          attachAction: "Attach",
          attaching: "Attaching…",
          remove: "Remove",
          removing: "Removing…",
          confirmDetach: "Remove this collection from the task?",
          cancel: "Cancel",
          download: "Download",
          clusterBadge: "Cluster",
          taskBadge: "Task",
          clusterNote: "Attached at cluster level — remove from Knowledge Base page",
          documents: "documents",
          maxSize: "Max size: 50MB",
        };

  const { data: documents = [] } = useQuery({
    queryKey: ["task-documents", taskId],
    queryFn: () => api.get<TaskDocumentResponse[]>(`/tasks/${taskId}/documents`),
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      const hasProcessing = items.some(
        (doc) => doc.status === "pending" || doc.status === "processing",
      );
      return hasProcessing ? 3000 : false;
    },
  });

  const { data: referenceCollections = [] } = useQuery({
    queryKey: ["task-reference-collections", taskId],
    queryFn: () =>
      api.get<TaskReferenceCollectionResponse[]>(`/tasks/${taskId}/reference-collections`),
  });

  const { data: kbCollections = [] } = useQuery({
    queryKey: ["kb-collections"],
    queryFn: () => api.get<KBCollectionResponse[]>("/kb/collections"),
    enabled: attachOpen,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      api.upload<TaskDocumentResponse>(`/tasks/${taskId}/documents`, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-documents", taskId] });
      setUploadError(null);
    },
    onError: (mutationError: Error) => setUploadError(mutationError.message),
  });

  const downloadMutation = useMutation({
    mutationFn: (documentId: string) =>
      api.get<DocumentDownloadUrlResponse>(
        `/tasks/${taskId}/documents/${documentId}/download-url`,
      ),
    onSuccess: (data) => {
      window.open(data.url, "_blank", "noopener,noreferrer");
    },
  });

  const attachMutation = useMutation({
    mutationFn: (payload: { collectionId: string; body: AttachCollectionRequest }) =>
      api.post(`/kb/collections/${payload.collectionId}/attach`, payload.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-reference-collections", taskId] });
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
      queryClient.invalidateQueries({ queryKey: ["task-reference-collections", taskId] });
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
    },
  });

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    if (file.size > DOCUMENT_MAX_UPLOAD_BYTES) {
      setUploadError(copy.maxSize);
      return;
    }
    uploadMutation.mutate(file);
  }

  function handleAttachSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAttachError(null);
    if (!selectedCollectionId) {
      return;
    }
    attachMutation.mutate({
      collectionId: selectedCollectionId,
      body: { entity_type: "task", entity_id: taskId },
    });
  }

  function handleDetach(collection: TaskReferenceCollectionResponse) {
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
    <section className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.paperTitle}
        </h2>
        <p className="mt-1 text-start text-xs text-zinc-500 dark:text-zinc-400">
          {copy.paperDescription}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
            className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {uploadMutation.isPending ? copy.uploading : copy.upload}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept={DOCUMENT_UPLOAD_ACCEPT}
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {uploadError ? (
          <p className="mt-2 text-start text-xs text-red-600 dark:text-red-400">{uploadError}</p>
        ) : null}

        <ul className="mt-4 space-y-2">
          {documents.length === 0 ? (
            <li className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.noPaper}</li>
          ) : (
            documents.map((document) => (
              <li
                key={document.id}
                className="flex items-start justify-between gap-3 rounded-lg border border-zinc-100 p-3 dark:border-zinc-800"
              >
                <div className="min-w-0 text-start">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                      {fileTypeIcon(document.file_type)}
                    </span>
                    <span
                      className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ring-inset ${documentStatusClasses(document.status)}`}
                    >
                      {documentStatusLabel(document.status, locale)}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm font-medium text-zinc-900 dark:text-zinc-50">
                    {document.filename}
                  </p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    {formatBytes(document.size_bytes)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => downloadMutation.mutate(document.id)}
                  disabled={downloadMutation.isPending}
                  className="shrink-0 text-xs font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
                >
                  {copy.download}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>

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
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                        KB
                      </span>
                      <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-[10px] font-medium text-zinc-600 dark:bg-zinc-900 dark:text-zinc-300">
                        {collection.attached_via === "cluster"
                          ? copy.clusterBadge
                          : copy.taskBadge}
                      </span>
                    </div>
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
                {collection.attached_via === "task" ? (
                  <button
                    type="button"
                    onClick={() => handleDetach(collection)}
                    disabled={detachMutation.isPending}
                    className="shrink-0 text-xs font-medium text-red-600 hover:underline dark:text-red-400"
                  >
                    {detachMutation.isPending ? copy.removing : copy.remove}
                  </button>
                ) : (
                  <span className="shrink-0 max-w-[8rem] text-end text-[10px] text-zinc-500 dark:text-zinc-400">
                    {copy.clusterNote}
                  </span>
                )}
              </li>
            ))
          )}
        </ul>
      </div>

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
    </section>
  );
}
