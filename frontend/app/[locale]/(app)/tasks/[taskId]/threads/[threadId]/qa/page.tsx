import { notFound, redirect } from "next/navigation";

import { ThreadQaForm } from "@/components/threads/thread-qa-form";
import { api, ApiError } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import { hasPendingOpeningQA } from "@/lib/threads";
import type { QAQuestionResponse, TaskResponse, ThreadResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type ThreadQaPageProps = {
  params: Promise<{ locale: string; taskId: string; threadId: string }>;
};

export default async function ThreadQaPage({ params }: ThreadQaPageProps) {
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

  const questions = await api.get<QAQuestionResponse[]>(`/threads/${threadId}/qa`, {
    accessToken: session.accessToken,
  });

  if (!hasPendingOpeningQA(questions)) {
    redirect(`/${locale}/tasks/${taskId}/threads/${threadId}`);
  }

  return <ThreadQaForm locale={locale} taskId={taskId} threadId={threadId} questions={questions} />;
}
