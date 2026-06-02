import type { Locale } from "@/i18n.config";

export function documentStatusClasses(status: string): string {
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

export function documentStatusLabel(status: string, locale: Locale): string {
  const labels: Record<string, { en: string; he: string }> = {
    pending: { en: "Pending", he: "ממתין" },
    processing: { en: "Processing", he: "מעבד" },
    ready: { en: "Ready", he: "מוכן" },
    failed: { en: "Failed", he: "נכשל" },
  };
  const entry = labels[status] ?? { en: status, he: status };
  return locale === "he" ? entry.he : entry.en;
}

export function fileTypeIcon(fileType: string): string {
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

export const DOCUMENT_UPLOAD_ACCEPT = ".pdf,.docx,.doc,.txt,.xlsx,.csv,.tex";
export const DOCUMENT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
