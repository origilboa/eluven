"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { api } from "@/lib/api";
import {
  DOCUMENT_MAX_UPLOAD_BYTES,
  DOCUMENT_UPLOAD_ACCEPT,
  documentStatusClasses,
  documentStatusLabel,
  fileTypeIcon,
} from "@/lib/document-status";
import type { DocumentDownloadUrlResponse, ThreadDocumentResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ThreadDocumentsPanelProps = {
  locale: Locale;
  threadId: string;
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

export function ThreadDocumentsPanel({ locale, threadId }: ThreadDocumentsPanelProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "מסמך לבדיקה",
          description: "העלה את המאמר או ההגשה לשרשור זה. הטקסט המלא יוזרם ל-AI בצ׳אט.",
          upload: "העלה מסמך",
          uploading: "מעלה…",
          empty: "לא הועלה מסמך לשרשור זה.",
          download: "הורד",
          maxSize: "גודל מקסימלי: 50MB",
          formats: "PDF, Word, TXT, Excel, LaTeX",
        }
      : {
          title: "Paper for this thread",
          description:
            "Upload the manuscript or submission for this thread. Full text is injected into AI chat context.",
          upload: "Upload document",
          uploading: "Uploading…",
          empty: "No document uploaded to this thread yet.",
          download: "Download",
          maxSize: "Max size: 50MB",
          formats: "PDF, Word, TXT, Excel, LaTeX",
        };

  const { data: documents = [] } = useQuery({
    queryKey: ["thread-documents", threadId],
    queryFn: () => api.get<ThreadDocumentResponse[]>(`/threads/${threadId}/documents`),
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      const hasProcessing = items.some(
        (doc) => doc.status === "pending" || doc.status === "processing",
      );
      return hasProcessing ? 3000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      api.upload<ThreadDocumentResponse>(`/threads/${threadId}/documents`, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["thread-documents", threadId] });
      queryClient.invalidateQueries({ queryKey: ["task-documents"] });
      setUploadError(null);
    },
    onError: (mutationError: Error) => setUploadError(mutationError.message),
  });

  const downloadMutation = useMutation({
    mutationFn: (documentId: string) =>
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
    if (!file) {
      return;
    }
    if (file.size > DOCUMENT_MAX_UPLOAD_BYTES) {
      setUploadError(copy.maxSize);
      return;
    }
    uploadMutation.mutate(file);
  }

  return (
    <aside className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
        {copy.title}
      </h2>
      <p className="mt-1 text-start text-xs text-zinc-500 dark:text-zinc-400">
        {copy.description}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          {uploadMutation.isPending ? copy.uploading : copy.upload}
        </button>
        <span className="text-xs text-zinc-500 dark:text-zinc-400">
          {copy.formats} · {copy.maxSize}
        </span>
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
          <li className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.empty}</li>
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
    </aside>
  );
}
