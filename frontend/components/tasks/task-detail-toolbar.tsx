"use client";

import { useState } from "react";

import { NewThreadModal } from "@/components/threads/new-thread-modal";
import type { Locale } from "@/i18n.config";

type TaskDetailToolbarProps = {
  locale: Locale;
  taskId: string;
  moduleType: string;
  workingLanguage: string | null;
};

export function TaskDetailToolbar({
  locale,
  taskId,
  moduleType,
  workingLanguage,
}: TaskDetailToolbarProps) {
  const [open, setOpen] = useState(false);

  const label = locale === "he" ? "שרשור חדש" : "New Thread";

  return (
    <>
      <button
        type="button"
        data-testid="new-thread-button"
        onClick={() => setOpen(true)}
        className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
      >
        {label}
      </button>
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
