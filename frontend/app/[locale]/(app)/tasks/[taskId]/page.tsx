import Link from "next/link";

import { requireAuthSession } from "@/lib/auth-session";
import { isLocale, type Locale } from "@/i18n.config";

type TaskDetailPageProps = {
  params: Promise<{ locale: string; taskId: string }>;
};

export default async function TaskDetailPage({ params }: TaskDetailPageProps) {
  const { locale: localeParam, taskId } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  await requireAuthSession(locale);

  const copy =
    locale === "he"
      ? {
          title: "פרטי משימה",
          body: "תצוגת משימה מלאה תגיע בשלב הבא.",
          back: "חזרה ללוח הבקרה",
        }
      : {
          title: "Task detail",
          body: "Full task workspace coming in a later build step.",
          back: "Back to dashboard",
        };

  return (
    <div className="space-y-4 text-start">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{copy.body}</p>
      <p className="text-xs text-zinc-500">Task ID: {taskId}</p>
      <Link
        href={`/${locale}/dashboard`}
        className="inline-flex text-sm font-medium text-zinc-900 underline-offset-4 hover:underline dark:text-zinc-100"
      >
        {copy.back}
      </Link>
    </div>
  );
}
