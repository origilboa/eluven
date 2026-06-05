"use client";

import { InstructionSetEditor } from "@/components/instructions/instruction-set-editor";
import type { Locale } from "@/i18n.config";

type ThreadInstructionPanelProps = {
  locale: Locale;
  threadId: string;
};

export function ThreadInstructionPanel({ locale, threadId }: ThreadInstructionPanelProps) {
  const copy =
    locale === "he"
      ? {
          title: "הוראות שרשור",
          subtitle:
            "הוראות לשרשור זה בלבד. הועתקו מברירת המחדל של סוג הפעילות בעת היצירה; ניתן לערוך כאן.",
        }
      : {
          title: "Thread instructions",
          subtitle:
            "Instructions for this thread only. Copied from the activity type default when the thread was created; edit here for this instance.",
        };

  const basePath = `/instructions/threads/${threadId}`;

  return (
    <InstructionSetEditor
      locale={locale}
      queryKey={["instructions", "thread", threadId]}
      fetchPath={basePath}
      createPath={basePath}
      activatePath={`${basePath}/activate`}
      title={copy.title}
      subtitle={copy.subtitle}
      assistantScope={{
        authoring_target: "instruction_set",
        level: "thread",
        thread_id: threadId,
      }}
    />
  );
}
