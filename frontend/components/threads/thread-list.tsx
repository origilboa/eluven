import Link from "next/link";

import { formatRelativeUpdatedAt, getStatusLabel } from "@/lib/format";
import { activityDisplayName } from "@/lib/threads";
import type { ActivityLibraryEntryResponse, ThreadResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ThreadListProps = {
  locale: Locale;
  taskId: string;
  threads: ThreadResponse[];
  activityEntries: ActivityLibraryEntryResponse[];
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

function tokenLabel(thread: ThreadResponse, locale: Locale): string {
  if (thread.token_budget === null) {
    return locale === "he"
      ? `${thread.tokens_used.toLocaleString()} טוקנים`
      : `${thread.tokens_used.toLocaleString()} tokens`;
  }

  return locale === "he"
    ? `${thread.tokens_used.toLocaleString()} / ${thread.token_budget.toLocaleString()} טוקנים`
    : `${thread.tokens_used.toLocaleString()} / ${thread.token_budget.toLocaleString()} tokens`;
}

export function ThreadList({
  locale,
  taskId,
  threads,
  activityEntries,
}: ThreadListProps) {
  if (threads.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-3">
      {threads.map((thread) => (
        <Link
          key={thread.id}
          href={`/${locale}/tasks/${taskId}/threads/${thread.id}`}
          className="block rounded-xl border border-zinc-200 bg-white p-4 transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-950"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1 text-start">
              <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
                {activityDisplayName(thread.thread_type, activityEntries)}
              </p>
              <h3 className="mt-1 truncate text-base font-semibold text-zinc-900 dark:text-zinc-50">
                {thread.title}
              </h3>
              <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                {formatRelativeUpdatedAt(thread.created_at, locale)}
              </p>
            </div>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusClasses(thread.status)}`}
            >
              {getStatusLabel(thread.status, locale)}
            </span>
          </div>
          <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">{tokenLabel(thread, locale)}</p>
        </Link>
      ))}
    </div>
  );
}
