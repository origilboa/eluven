import type { ActivityLibraryEntryResponse, ThreadResponse } from "@/lib/types/api";

export type ThreadStatusGroup = "active" | "draft" | "complete" | "archived";

const GROUP_ORDER: ThreadStatusGroup[] = ["active", "draft", "complete", "archived"];

export function groupThreadsByStatus(
  threads: ThreadResponse[],
): Map<ThreadStatusGroup, ThreadResponse[]> {
  const grouped = new Map<ThreadStatusGroup, ThreadResponse[]>();

  for (const thread of threads) {
    const status = thread.status as ThreadStatusGroup;
    const bucket = grouped.get(status) ?? [];
    bucket.push(thread);
    grouped.set(status, bucket);
  }

  for (const [status, items] of grouped) {
    grouped.set(
      status,
      [...items].sort(
        (left, right) =>
          new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
      ),
    );
  }

  return grouped;
}

export function orderedThreadStatusGroups(
  grouped: Map<ThreadStatusGroup, ThreadResponse[]>,
): Array<{ status: ThreadStatusGroup; threads: ThreadResponse[] }> {
  return GROUP_ORDER.flatMap((status) => {
    const threads = grouped.get(status);
    if (!threads?.length) {
      return [];
    }
    return [{ status, threads }];
  });
}

export function activityDisplayName(
  threadType: string,
  entries: ActivityLibraryEntryResponse[],
): string {
  const match = entries.find((entry) => entry.thread_type === threadType);
  return match?.display_name ?? threadType;
}

export function hasPendingOpeningQA(questions: Array<{ stage: string; responded_at: string | null; is_required: boolean }>): boolean {
  return questions.some(
    (question) =>
      question.stage === "opening" &&
      question.is_required &&
      question.responded_at === null,
  );
}
