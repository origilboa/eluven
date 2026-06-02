import Link from "next/link";

import { ClustersToolbar } from "@/components/clusters/clusters-toolbar";
import { api } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import type { ClusterResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type ClustersPageProps = {
  params: Promise<{ locale: string }>;
};

function isAssignmentCluster(clusterType: string): boolean {
  return clusterType === "assignment" || clusterType === "student_paper_review";
}

export default async function ClustersPage({ params }: ClustersPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let clusters: ClusterResponse[] = [];
  try {
    clusters = await api.get<ClusterResponse[]>("/clusters", {
      accessToken: session.accessToken,
    });
  } catch {
    clusters = [];
  }

  const assignments = clusters.filter((cluster) => isAssignmentCluster(cluster.cluster_type));

  const copy =
    locale === "he"
      ? {
          title: "מטלות (Assignments)",
          subtitle: "קבוצות הגשות לסקירת עבודות סטודנטים",
          empty: "אין מטלות עדיין. צור Assignment חדש כדי להתחיל.",
          submissions: "הגשות",
        }
      : {
          title: "Assignments",
          subtitle: "Student Paper Review assignment clusters",
          empty: "No assignments yet. Create a new Assignment to get started.",
          submissions: "submissions",
        };

  return (
    <div className="space-y-8">
      <ClustersToolbar locale={locale} />

      {assignments.length === 0 ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{copy.empty}</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {assignments.map((cluster) => (
            <Link
              key={cluster.id}
              href={`/${locale}/clusters/${cluster.id}`}
              className="rounded-2xl border border-zinc-200 bg-white p-5 text-start transition-colors hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-zinc-600"
            >
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{cluster.name}</h2>
              {cluster.description ? (
                <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{cluster.description}</p>
              ) : null}
              <p className="mt-3 text-xs text-zinc-500">
                {cluster.task_count} {copy.submissions}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
