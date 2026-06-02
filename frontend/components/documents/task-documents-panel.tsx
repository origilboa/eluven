"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState } from "react";

import { api } from "@/lib/api";
import {
  DOCUMENT_MAX_UPLOAD_BYTES,
  DOCUMENT_UPLOAD_ACCEPT,
  documentStatusClasses,
  documentStatusLabel,
  fileTypeIcon,
} from "@/lib/document-status";
import type {
  DocumentDownloadUrlResponse,
  TaskReferenceCollectionResponse,
  TaskThreadDocumentResponse,
  ThreadDocumentResponse,
  ThreadResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type TaskDocumentsPanelProps = {
  locale: Locale;
  taskId: string;
  threads: ThreadResponse[];
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

export function TaskDocumentsPanel({ locale, taskId, threads }: TaskDocumentsPanelProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadThreadId, setUploadThreadId] = useState(threads[0]?.id ?? "");

  const copy =
    locale === "he"
      ? {
          paperTitle: "מסמך לבדיקה",
          paperDescription:
            "המאמר או ההגשה שאתה בודק. מועלה לשרשור ומוזרם כטקסט מלא ל-AI.",
          referenceTitle: "מאגר ידע לעיון",
          referenceDescription:
            "חומרי עזר (מדריכים, רubric, מאמרי רקע). נשלפים דרך RAG בצ׳אט — לא המסמך עצמו.",
          upload: "העלה מסמך",
          uploading: "מעלה…",
          noPaper: "לא הועלה מסמך לבדיקה.",
          noReferences: "לא מצורף מאגר ידע. צרף אוסף מדף מאגר הידע.",
          manageKb: "נהל במאגר הידע",
          download: "הורד",
          thread: "שרשור",
          selectThread: "העלה לשרשור",
          noThreads: "צור שרשור לפני העלאת מסמך.",
          clusterBadge: "מקבץ",
          taskBadge: "משימה",
          documents: "מסמכים",
          maxSize: "גודל מקסימלי: 50MB",
        }
      : {
          paperTitle: "Paper under review",
          paperDescription:
            "The manuscript or student submission you are reviewing. Uploaded to a thread and injected as full text for AI.",
          referenceTitle: "Reference knowledge base",
          referenceDescription:
            "Supporting material (guides, rubrics, background reading). Retrieved via RAG in chat — not the paper itself.",
          upload: "Upload paper",
          uploading: "Uploading…",
          noPaper: "No paper uploaded yet.",
          noReferences: "No reference collections attached. Attach one from the Knowledge Base page.",
          manageKb: "Manage in Knowledge Base",
          download: "Download",
          thread: "Thread",
          selectThread: "Upload to thread",
          noThreads: "Create a thread before uploading a paper.",
          clusterBadge: "Cluster",
          taskBadge: "Task",
          documents: "documents",
          maxSize: "Max size: 50MB",
        };

  const { data: documents = [] } = useQuery({
    queryKey: ["task-documents", taskId],
    queryFn: () => api.get<TaskThreadDocumentResponse[]>(`/tasks/${taskId}/documents`),
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

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      api.upload<ThreadDocumentResponse>(`/threads/${uploadThreadId}/documents`, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-documents", taskId] });
      queryClient.invalidateQueries({ queryKey: ["thread-documents"] });
      setUploadError(null);
    },
    onError: (mutationError: Error) => setUploadError(mutationError.message),
  });

  const downloadMutation = useMutation({
    mutationFn: ({ threadId, documentId }: { threadId: string; documentId: string }) =>
      api.get<DocumentDownloadUrlResponse>(
        `/threads/${threadId}/documents/${documentId}/download-url`,
      ),
    onSuccess: (data) => {
      window.open(data.url, "_blank", "noopener,noreferrer");
    },
  });

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !uploadThreadId) {
      return;
    }
    if (file.size > DOCUMENT_MAX_UPLOAD_BYTES) {
      setUploadError(copy.maxSize);
      return;
    }
    uploadMutation.mutate(file);
  }

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.paperTitle}
        </h2>
        <p className="mt-1 text-start text-xs text-zinc-500 dark:text-zinc-400">
          {copy.paperDescription}
        </p>

        {threads.length === 0 ? (
          <p className="mt-3 text-start text-sm text-zinc-500 dark:text-zinc-400">
            {copy.noThreads}
          </p>
        ) : (
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <label className="text-start text-xs text-zinc-500 dark:text-zinc-400">
              <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
                {copy.selectThread}
              </span>
              <select
                value={uploadThreadId}
                onChange={(event) => setUploadThreadId(event.target.value)}
                className="rounded-lg border border-zinc-200 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              >
                {threads.map((thread) => (
                  <option key={thread.id} value={thread.id}>
                    {thread.title}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending || !uploadThreadId}
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
        )}

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
                    {formatBytes(document.size_bytes)} · {copy.thread}: {document.thread_title}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    downloadMutation.mutate({
                      threadId: document.thread_id,
                      documentId: document.id,
                    })
                  }
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
          <Link
            href={`/${locale}/kb`}
            className="shrink-0 text-xs font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
          >
            {copy.manageKb}
          </Link>
        </div>

        <ul className="mt-4 space-y-2">
          {referenceCollections.length === 0 ? (
            <li className="text-start text-sm text-zinc-500 dark:text-zinc-400">
              {copy.noReferences}
            </li>
          ) : (
            referenceCollections.map((collection) => (
              <li key={collection.id}>
                <Link
                  href={`/${locale}/kb/${collection.id}`}
                  className="flex items-start justify-between gap-3 rounded-lg border border-zinc-100 p-3 transition hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-600"
                >
                  <div className="min-w-0 text-start">
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
                  </div>
                  <span className="shrink-0 text-xs text-zinc-500 dark:text-zinc-400">
                    {collection.document_count} {copy.documents}
                  </span>
                </Link>
              </li>
            ))
          )}
        </ul>
      </div>
    </section>
  );
}
