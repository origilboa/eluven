"use client";

import { getStatusLabel } from "@/lib/format";
import { activityDisplayName } from "@/lib/threads";
import type { ActivityLibraryEntryResponse, ThreadResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ThreadInfoPanelProps = {
  locale: Locale;
  thread: ThreadResponse;
  activityEntries: ActivityLibraryEntryResponse[];
};

export function ThreadInfoPanel({ locale, thread, activityEntries }: ThreadInfoPanelProps) {
  const usagePercent =
    thread.token_budget && thread.token_budget > 0
      ? Math.min(100, Math.round((thread.tokens_used / thread.token_budget) * 100))
      : null;

  const copy =
    locale === "he"
      ? {
          title: "פרטי שרשור",
          type: "סוג",
          status: "סטטוס",
          language: "שפת עבודה",
          tokens: "שימוש בטוקנים",
          automated: "אוטומטי",
          yes: "כן",
          no: "לא",
        }
      : {
          title: "Thread info",
          type: "Type",
          status: "Status",
          language: "Working language",
          tokens: "Token usage",
          automated: "Automated",
          yes: "Yes",
          no: "No",
        };

  return (
    <aside className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
        {copy.title}
      </h2>

      <dl className="mt-4 space-y-4 text-start text-sm">
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">{copy.type}</dt>
          <dd className="mt-1 font-medium text-zinc-900 dark:text-zinc-50">
            {activityDisplayName(thread.thread_type, activityEntries)}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">{copy.status}</dt>
          <dd className="mt-1 font-medium text-zinc-900 dark:text-zinc-50">
            {getStatusLabel(thread.status, locale)}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">{copy.language}</dt>
          <dd className="mt-1 font-medium text-zinc-900 dark:text-zinc-50">
            {thread.working_language ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">{copy.automated}</dt>
          <dd className="mt-1 font-medium text-zinc-900 dark:text-zinc-50">
            {thread.is_automated ? copy.yes : copy.no}
          </dd>
        </div>
        <div>
          <dt className="text-zinc-500 dark:text-zinc-400">{copy.tokens}</dt>
          <dd className="mt-2">
            <div className="flex items-center justify-between gap-2 text-xs text-zinc-600 dark:text-zinc-400">
              <span>{thread.tokens_used.toLocaleString()}</span>
              {thread.token_budget !== null ? (
                <span>{thread.token_budget.toLocaleString()}</span>
              ) : null}
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-900">
              <div
                className="h-full rounded-full bg-zinc-900 transition-all dark:bg-zinc-100"
                style={{ width: `${usagePercent ?? (thread.tokens_used > 0 ? 8 : 0)}%` }}
              />
            </div>
          </dd>
        </div>
      </dl>
    </aside>
  );
}
