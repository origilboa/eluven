"use client";

import { useState } from "react";

import { ThreadInstructionPanel } from "@/components/instructions/thread-instruction-panel";
import { ChatInterface } from "@/components/threads/chat-interface";
import { ThreadInfoPanel } from "@/components/threads/thread-info-panel";
import { ThreadPromptSidebar } from "@/components/threads/thread-prompt-sidebar";
import type {
  ActivityLibraryEntryResponse,
  MessageResponse,
  ThreadPromptResponse,
  ThreadResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ThreadDetailClientProps = {
  locale: Locale;
  thread: ThreadResponse;
  initialMessages: MessageResponse[];
  activityEntries: ActivityLibraryEntryResponse[];
};

export function ThreadDetailClient({
  locale,
  thread,
  initialMessages,
  activityEntries,
}: ThreadDetailClientProps) {
  const [draftPrompt, setDraftPrompt] = useState<ThreadPromptResponse | null>(null);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <ChatInterface
        locale={locale}
        threadId={thread.id}
        initialMessages={initialMessages}
        draftMessage={draftPrompt?.prompt_text ?? ""}
        draftKey={draftPrompt?.id ?? null}
        promptId={draftPrompt?.id ?? null}
        onDraftConsumed={() => setDraftPrompt(null)}
      />
      <div className="space-y-6">
        <ThreadPromptSidebar
          locale={locale}
          threadId={thread.id}
          onSelectPrompt={setDraftPrompt}
        />
        <ThreadInstructionPanel locale={locale} threadId={thread.id} />
        <ThreadInfoPanel locale={locale} thread={thread} activityEntries={activityEntries} />
      </div>
    </div>
  );
}
