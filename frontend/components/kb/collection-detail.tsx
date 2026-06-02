"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { api } from "@/lib/api";
import type { KBDocumentResponse, KBCollectionResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".tex"];

type CollectionDetailProps = {
  locale: Locale;
  collection: KBCollectionResponse;
  initialDocuments: KBDocumentResponse[];
};

function fileTypeIcon(fileType: string): string {
  switch (fileType) {
    case "pdf":
      return "PDF";
    case "docx":
    case "doc":
      return "DOC";
    case "txt":
      return "TXT";
    case "xlsx":
    case "csv":
      return "XLS";
    case "tex":
      return "TEX";
    default:
      return fileType.toUpperCase();
  }
}

function statusClasses(status: string): string {
  switch (status) {
    case "ready":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300";
    case "processing":
      return "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-950 dark:text-blue-300";
    case "failed":
      return "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-950 dark:text-red-300";
    default:
      return "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-950 dark:text-amber-300";
  }
}

function statusLabel(status: string, locale: Locale): string {
  const labels: Record<string, { en: string; he: string }> = {
    pending: { en: "Pending", he: "ממתין" },
    processing: { en: "Processing", he: "מעבד" },
    ready: { en: "Ready", he: "מוכן" },
    failed: { en: "Failed", he: "נכשל" },
  };
  const entry = labels[status] ?? { en: status, he: status };
  return locale === "he" ? entry.he : entry.en;
}

export function CollectionDetail({
  locale,
  collection,
  initialDocuments,
}: CollectionDetailProps) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          back: "חזרה לאוספים",
          documents: "מסמכים",
          upload: "העלה מסמך",
          uploading: "מעלה…",
          empty: "אין מסמכים באוסף זה.",
          chunks: "קטעים",
          attachments: "צירופים",
          detach: "הסר",
          confirmDetach: "להסיר את הצירוף?",
          maxSize: "גודל מקסימלי: 50MB",
          formats: "PDF, Word, TXT, Excel, LaTeX",
        }
      : {
          back: "Back to collections",
          documents: "Documents",
          upload: "Upload document",
          uploading: "Uploading…",
          empty: "No documents in this collection yet.",
          chunks: "chunks",
          attachments: "Attachments",
          detach: "Remove",
          confirmDetach: "Remove this attachment?",
          maxSize: "Max size: 50MB",
          formats: "PDF, Word, TXT, Excel, LaTeX",
        };

  const { data: documents = initialDocuments } = useQuery({
    queryKey: ["kb-documents", collection.id],
    queryFn: () =>
      api.get<KBDocumentResponse[]>(`/kb/collections/${collection.id}/documents`),
    initialData: initialDocuments,
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
      api.upload<KBDocumentResponse>(`/kb/collections/${collection.id}/documents`, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-documents", collection.id] });
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      setUploadError(null);
    },
    onError: (mutationError: Error) => {
      setUploadError(mutationError.message);
    },
  });

  const detachMutation = useMutation({
    mutationFn: (attachmentId: string) =>
      api.delete(`/kb/collections/${collection.id}/attach/${attachmentId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kb-collections"] });
      queryClient.invalidateQueries({ queryKey: ["task-reference-collections"] });
      router.refresh();
    },
    onError: (mutationError: Error) => {
      window.alert(mutationError.message);
    },
  });

  function handleDetach(attachmentId: string) {
    if (!window.confirm(copy.confirmDetach)) {
      return;
    }
    detachMutation.mutate(attachmentId);
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError(
        locale === "he" ? "הקובץ חורג מ-50MB." : "File exceeds the 50MB limit.",
      );
      return;
    }

    const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setUploadError(
        locale === "he" ? "סוג קובץ לא נתמך." : "Unsupported file type.",
      );
      return;
    }

    uploadMutation.mutate(file);
  }

  return (
    <div className="space-y-6">
      <div className="text-start">
        <Link
          href={`/${locale}/kb`}
          className="text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          {copy.back}
        </Link>
        <h1 className="mt-3 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
          {collection.name}
        </h1>
        {collection.description ? (
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            {collection.description}
          </p>
        ) : null}
      </div>

      {collection.attachments.length > 0 ? (
        <section className="text-start">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            {copy.attachments}
          </h2>
          <div className="mt-2 flex flex-wrap gap-2">
            {collection.attachments.map((attachment) => (
              <span
                key={attachment.id}
                className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20 dark:bg-blue-950 dark:text-blue-300"
              >
                {attachment.entity_name}
                <button
                  type="button"
                  onClick={() => handleDetach(attachment.id)}
                  disabled={detachMutation.isPending}
                  className="text-blue-800 underline-offset-2 hover:underline dark:text-blue-200"
                >
                  {copy.detach}
                </button>
              </span>
            ))}
          </div>
        </section>
      ) : null}

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-start">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {copy.documents}
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {copy.formats} · {copy.maxSize}
            </p>
          </div>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              className="sr-only"
              onChange={handleFileChange}
            />
            <button
              type="button"
              disabled={uploadMutation.isPending}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
            >
              {uploadMutation.isPending ? copy.uploading : copy.upload}
            </button>
          </div>
        </div>

        {uploadError ? (
          <p className="text-start text-sm text-red-600 dark:text-red-400">{uploadError}</p>
        ) : null}

        {documents.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-300 px-6 py-10 text-center dark:border-zinc-700">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{copy.empty}</p>
          </div>
        ) : (
          <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-950">
            {documents.map((document) => (
              <li
                key={document.id}
                className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 items-start gap-3 text-start">
                  <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-xs font-semibold text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
                    {fileTypeIcon(document.file_type)}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-50">
                      {document.filename}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                      {document.chunk_count} {copy.chunks}
                    </p>
                  </div>
                </div>
                <span
                  className={`inline-flex w-fit items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusClasses(document.status)}`}
                >
                  {statusLabel(document.status, locale)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
