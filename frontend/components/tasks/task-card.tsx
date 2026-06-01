import Link from "next/link";

import { formatRelativeUpdatedAt, getStatusLabel } from "@/lib/format";
import { getModuleLabel } from "@/lib/modules";
import type { TaskResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type TaskCardProps = {
  task: TaskResponse;
  locale: Locale;
};

function statusClasses(status: string): string {
  switch (status) {
    case "active":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300";
    case "complete":
      return "bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-950 dark:text-blue-300";
    case "archived":
      return "bg-zinc-100 text-zinc-600 ring-zinc-500/20 dark:bg-zinc-900 dark:text-zinc-400";
    default:
      return "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-950 dark:text-amber-300";
  }
}

export function TaskCard({ task, locale }: TaskCardProps) {
  const threadLabel =
    locale === "he"
      ? `${task.thread_count} שרשורים`
      : `${task.thread_count} thread${task.thread_count === 1 ? "" : "s"}`;

  return (
    <Link
      href={`/${locale}/tasks/${task.id}`}
      className="group block rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 dark:border-zinc-800 dark:bg-zinc-950 dark:focus-visible:ring-zinc-100"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 text-start">
          <h3 className="truncate text-base font-semibold text-zinc-900 group-hover:text-zinc-700 dark:text-zinc-50 dark:group-hover:text-zinc-200">
            {task.title}
          </h3>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            {formatRelativeUpdatedAt(task.updated_at, locale)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
            {getModuleLabel(task.module_type, locale)}
          </span>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusClasses(task.status)}`}
          >
            {getStatusLabel(task.status, locale)}
          </span>
        </div>
      </div>
      <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">{threadLabel}</p>
    </Link>
  );
}
