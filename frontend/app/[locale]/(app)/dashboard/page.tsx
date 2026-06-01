import { DashboardEmptyWrapper } from "@/components/dashboard/dashboard-client";
import { DashboardToolbar } from "@/components/dashboard/dashboard-toolbar";
import { TaskCard } from "@/components/tasks/task-card";
import { api } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import {
  getModuleLabel,
  groupTasksByModule,
  MODULE_DEFINITIONS,
} from "@/lib/modules";
import type { TaskResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type DashboardPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function DashboardPage({ params }: DashboardPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let tasks: TaskResponse[] = [];
  try {
    tasks = await api.get<TaskResponse[]>("/tasks", {
      accessToken: session.accessToken,
    });
  } catch {
    tasks = [];
  }

  const grouped = groupTasksByModule(tasks);
  const moduleOrder = MODULE_DEFINITIONS.map((module) => module.value);

  return (
    <div className="space-y-8">
      <DashboardToolbar locale={locale} />

      {tasks.length === 0 ? (
        <DashboardEmptyWrapper locale={locale} />
      ) : (
        <div className="space-y-8">
          {moduleOrder.map((moduleType) => {
            const moduleTasks = grouped.get(moduleType);
            if (!moduleTasks?.length) {
              return null;
            }

            return (
              <section key={moduleType} className="space-y-4">
                <div className="text-start">
                  <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                    {getModuleLabel(moduleType, locale)}
                  </h2>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {locale === "he"
                      ? `${moduleTasks.length} משימות`
                      : `${moduleTasks.length} task${moduleTasks.length === 1 ? "" : "s"}`}
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {moduleTasks.map((task) => (
                    <TaskCard key={task.id} task={task} locale={locale} />
                  ))}
                </div>
              </section>
            );
          })}

          {[...grouped.entries()]
            .filter(([moduleType]) => !moduleOrder.includes(moduleType as (typeof moduleOrder)[number]))
            .map(([moduleType, moduleTasks]) => (
              <section key={moduleType} className="space-y-4">
                <div className="text-start">
                  <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                    {getModuleLabel(moduleType, locale)}
                  </h2>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {moduleTasks.map((task) => (
                    <TaskCard key={task.id} task={task} locale={locale} />
                  ))}
                </div>
              </section>
            ))}
        </div>
      )}
    </div>
  );
}
