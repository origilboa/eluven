import Link from "next/link";
import { notFound } from "next/navigation";

import { TaskDetailToolbar } from "@/components/tasks/task-detail-toolbar";
import { TaskInstructionPanel } from "@/components/instructions/task-instruction-panel";
import { TaskMemoryPanel } from "@/components/tasks/task-memory-panel";
import { ThreadList } from "@/components/threads/thread-list";
import { WorkflowPanel } from "@/components/workflows/workflow-panel";
import { api, ApiError } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import { getStatusLabel } from "@/lib/format";
import { getModuleLabel } from "@/lib/modules";
import { orderedThreadStatusGroups, groupThreadsByStatus } from "@/lib/threads";
import type {
  ActivityLibraryEntryResponse,
  TaskMemoryResponse,
  TaskResponse,
  ThreadResponse,
} from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type TaskDetailPageProps = {
  params: Promise<{ locale: string; taskId: string }>;
};

function workingLanguageLabel(language: string | null, locale: Locale): string {
  if (language === "he") {
    return locale === "he" ? "עברית" : "Hebrew";
  }
  if (language === "en") {
    return locale === "he" ? "אנגלית" : "English";
  }
  return language ?? "—";
}

function statusGroupLabel(status: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    active: { en: "Active", he: "פעילים" },
    draft: { en: "Draft", he: "טיוטה" },
    complete: { en: "Complete", he: "הושלמו" },
    archived: { en: "Archived", he: "בארכיון" },
  };
  return labels[status]?.[locale] ?? getStatusLabel(status, locale);
}

export default async function TaskDetailPage({ params }: TaskDetailPageProps) {
  const { locale: localeParam, taskId } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let task: TaskResponse;
  try {
    task = await api.get<TaskResponse>(`/tasks/${taskId}`, {
      accessToken: session.accessToken,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [threads, memory, activityEntries] = await Promise.all([
    api.get<ThreadResponse[]>(`/tasks/${taskId}/threads`, {
      accessToken: session.accessToken,
    }),
    api.get<TaskMemoryResponse>(`/tasks/${taskId}/memory`, {
      accessToken: session.accessToken,
    }),
    api.get<ActivityLibraryEntryResponse[]>(
      `/activity-library?module_type=${encodeURIComponent(task.module_type)}`,
      { accessToken: session.accessToken },
    ),
  ]);

  const grouped = orderedThreadStatusGroups(groupThreadsByStatus(threads));

  const copy =
    locale === "he"
      ? {
          back: "חזרה ללוח הבקרה",
          module: "מודול",
          status: "סטטוס",
          language: "שפת עבודה",
          threads: "שרשורים",
          noThreads: "אין שרשורים עדיין. צור שרשור חדש כדי להתחיל.",
        }
      : {
          back: "Back to dashboard",
          module: "Module",
          status: "Status",
          language: "Working language",
          threads: "Threads",
          noThreads: "No threads yet. Create a new thread to get started.",
        };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-3 text-start">
          <Link
            href={`/${locale}/dashboard`}
            className="inline-flex text-sm font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
          >
            {copy.back}
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{task.title}</h1>
            <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-600 dark:text-zinc-400">
              <div>
                <dt className="inline">{copy.module}: </dt>
                <dd className="inline font-medium text-zinc-900 dark:text-zinc-100">
                  {getModuleLabel(task.module_type, locale)}
                </dd>
              </div>
              <div>
                <dt className="inline">{copy.status}: </dt>
                <dd className="inline font-medium text-zinc-900 dark:text-zinc-100">
                  {getStatusLabel(task.status, locale)}
                </dd>
              </div>
              <div>
                <dt className="inline">{copy.language}: </dt>
                <dd className="inline font-medium text-zinc-900 dark:text-zinc-100">
                  {workingLanguageLabel(task.working_language, locale)}
                </dd>
              </div>
            </dl>
          </div>
        </div>
        <TaskDetailToolbar
          locale={locale}
          taskId={taskId}
          moduleType={task.module_type}
          workingLanguage={task.working_language}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="space-y-6">
          <h2 className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            {copy.threads}
          </h2>

          {grouped.length === 0 ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{copy.noThreads}</p>
          ) : (
            grouped.map(({ status, threads: statusThreads }) => (
              <div key={status} className="space-y-3">
                <h3 className="text-start text-sm font-semibold uppercase tracking-wide text-zinc-500">
                  {statusGroupLabel(status, locale)}
                </h3>
                <ThreadList
                  locale={locale}
                  taskId={taskId}
                  threads={statusThreads}
                  activityEntries={activityEntries}
                />
              </div>
            ))
          )}
        </section>

        <div className="space-y-6">
          <TaskInstructionPanel
            locale={locale}
            taskId={taskId}
            moduleType={task.module_type}
          />
          <TaskMemoryPanel locale={locale} memory={memory} />
          <WorkflowPanel locale={locale} taskId={taskId} moduleType={task.module_type} />
        </div>
      </div>
    </div>
  );
}
