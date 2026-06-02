import Link from "next/link";
import { notFound } from "next/navigation";

import { ClusterDetailToolbar } from "@/components/clusters/cluster-detail-toolbar";
import { TaskCard } from "@/components/tasks/task-card";
import { api, ApiError } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import type { ClusterResponse, TaskResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type ClusterDetailPageProps = {
  params: Promise<{ locale: string; clusterId: string }>;
};

export default async function ClusterDetailPage({ params }: ClusterDetailPageProps) {
  const { locale: localeParam, clusterId } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let cluster: ClusterResponse;
  try {
    cluster = await api.get<ClusterResponse>(`/clusters/${clusterId}`, {
      accessToken: session.accessToken,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const submissions = await api.get<TaskResponse[]>(`/clusters/${clusterId}/submissions`, {
    accessToken: session.accessToken,
  });

  const copy =
    locale === "he"
      ? {
          back: "חזרה למטלות",
          submissions: "הגשות",
          empty: "אין הגשות עדיין.",
        }
      : {
          back: "Back to assignments",
          submissions: "Submissions",
          empty: "No submissions yet.",
        };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-3 text-start">
          <Link
            href={`/${locale}/clusters`}
            className="inline-flex text-sm font-medium text-zinc-600 underline-offset-4 hover:underline"
          >
            {copy.back}
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{cluster.name}</h1>
            {cluster.description ? (
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{cluster.description}</p>
            ) : null}
          </div>
        </div>
        <ClusterDetailToolbar locale={locale} clusterId={clusterId} />
      </div>

      <section className="space-y-4">
        <h2 className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.submissions}
        </h2>
        {submissions.length === 0 ? (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">{copy.empty}</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {submissions.map((task) => (
              <TaskCard key={task.id} task={task} locale={locale} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
