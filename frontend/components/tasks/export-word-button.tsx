"use client";

import { api } from "@/lib/api";
import type { Locale } from "@/i18n.config";

type ExportWordButtonProps = {
  locale: Locale;
  taskId: string;
};

export function ExportWordButton({ locale, taskId }: ExportWordButtonProps) {
  const label = locale === "he" ? "ייצוא Word" : "Export Word";

  async function handleExport() {
    const { blob, filename } = await api.download(`/tasks/${taskId}/export/word`);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename ?? "task_export.docx";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      type="button"
      onClick={() => void handleExport()}
      className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-white dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-950"
    >
      {label}
    </button>
  );
}
