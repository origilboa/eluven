"use client";

import { useState } from "react";

import { ExportWordButton } from "@/components/tasks/export-word-button";
import { NewThreadModal } from "@/components/threads/new-thread-modal";
import type { Locale } from "@/i18n.config";

type TaskDetailToolbarProps = {
  locale: Locale;
  taskId: string;
  moduleType: string;
  workingLanguage: string | null;
  showWordExport?: boolean;
};

export function TaskDetailToolbar({
  locale,
  taskId,
  moduleType,
  workingLanguage,
  showWordExport = true,
}: TaskDetailToolbarProps) {
  const [open, setOpen] = useState(false);

  const label = locale === "he" ? "שרשור חדש" : "New Thread";

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        {showWordExport ? <ExportWordButton locale={locale} taskId={taskId} /> : null}
        <button
          type="button"
          data-testid="new-thread-button"
          onClick={() => setOpen(true)}
          className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
        >
          {label}
        </button>
      </div>
      <NewThreadModal
        locale={locale}
        taskId={taskId}
        moduleType={moduleType}
        defaultWorkingLanguage={workingLanguage}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
