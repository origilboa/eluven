import Link from "next/link";
import { notFound } from "next/navigation";

import { ThreadInstructionPanel } from "@/components/instructions/thread-instruction-panel";
import { ChatInterface } from "@/components/threads/chat-interface";
import { ThreadInfoPanel } from "@/components/threads/thread-info-panel";
import { api, ApiError } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import type {
  ActivityLibraryEntryResponse,
  MessageResponse,
  TaskResponse,
  ThreadResponse,
} from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type ThreadDetailPageProps = {
  params: Promise<{ locale: string; taskId: string; threadId: string }>;
};

export default async function ThreadDetailPage({ params }: ThreadDetailPageProps) {
  const { locale: localeParam, taskId, threadId } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let task: TaskResponse;
  let thread: ThreadResponse;
  try {
    [task, thread] = await Promise.all([
      api.get<TaskResponse>(`/tasks/${taskId}`, { accessToken: session.accessToken }),
      api.get<ThreadResponse>(`/threads/${threadId}`, { accessToken: session.accessToken }),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  if (thread.task_id !== taskId) {
    notFound();
  }

  const [messages, activityEntries] = await Promise.all([
    api.get<MessageResponse[]>(`/threads/${threadId}/messages`, {
      accessToken: session.accessToken,
    }),
    api.get<ActivityLibraryEntryResponse[]>(
      `/activity-library?module_type=${encodeURIComponent(task.module_type)}`,
      { accessToken: session.accessToken },
    ),
  ]);

  const copy =
    locale === "he"
      ? { back: "חזרה למשימה" }
      : { back: "Back to task" };

  return (
    <div className="space-y-6">
      <div className="text-start">
        <Link
          href={`/${locale}/tasks/${taskId}`}
          className="inline-flex text-sm font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
        >
          {copy.back}
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{thread.title}</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <ChatInterface locale={locale} threadId={threadId} initialMessages={messages} />
        <div className="space-y-6">
          <ThreadInstructionPanel locale={locale} threadId={threadId} />
          <ThreadInfoPanel locale={locale} thread={thread} activityEntries={activityEntries} />
        </div>
      </div>
    </div>
  );
}
