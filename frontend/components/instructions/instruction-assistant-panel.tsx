"use client";

import { useCallback, useMemo, useState } from "react";

import { streamInstructionAssistant } from "@/lib/stream";
import type { InstructionAssistantScope, StreamEvent } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
};

type InstructionAssistantPanelProps = {
  locale: Locale;
  scope: InstructionAssistantScope;
  draftContent: string;
  onApplyDraft: (content: string) => void;
  disabled?: boolean;
};

const PROPOSED_DRAFT_MARKER = "## Proposed instruction draft";

function extractProposedDraft(content: string): string {
  const markerIndex = content.indexOf(PROPOSED_DRAFT_MARKER);
  if (markerIndex >= 0) {
    return content.slice(markerIndex + PROPOSED_DRAFT_MARKER.length).trim();
  }
  return content.trim();
}

function StreamingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      <span className="size-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:-0.2s]" />
      <span className="size-1.5 animate-bounce rounded-full bg-zinc-500 [animation-delay:-0.1s]" />
      <span className="size-1.5 animate-bounce rounded-full bg-zinc-500" />
    </span>
  );
}

export function InstructionAssistantPanel({
  locale,
  scope,
  draftContent,
  onApplyDraft,
  disabled = false,
}: InstructionAssistantPanelProps) {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = useMemo(
    () =>
      locale === "he"
        ? {
            title: "עוזר הוראות",
            subtitle: "שוחח כדי לנסח או לשפר את ההוראות בשכבה זו.",
            placeholder: "בקש טיוטה, ביקורת, או שיפור…",
            send: "שליחה",
            sending: "שולח…",
            empty: "שאל את העוזר לעזור בניסוח ההוראות.",
            apply: "החל על הטיוטה",
            applyConfirm: "להחליף את תוכן ההוראות בטיוטה שהעוזר הציע?",
            statusPreparing: "מכין תשובה…",
          }
        : {
            title: "Instruction assistant",
            subtitle: "Chat to draft or refine instructions for this layer.",
            placeholder: "Ask for a draft, review, or improvement…",
            send: "Send",
            sending: "Sending…",
            empty: "Ask the assistant to help author instructions.",
            apply: "Apply to draft",
            applyConfirm: "Replace the instruction textarea with the assistant's proposed draft?",
            statusPreparing: "Preparing response…",
          },
    [locale],
  );

  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant" && message.content),
    [messages],
  );

  const handleStreamEvent = useCallback((event: StreamEvent, assistantId: string) => {
    if (event.type === "status") {
      setStatusMessage(event.message);
      return;
    }
    if (event.type === "text") {
      setStatusMessage(null);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? { ...message, content: message.content + event.text }
            : message,
        ),
      );
      return;
    }
    if (event.type === "error") {
      setError(event.message);
      setStatusMessage(null);
      setMessages((current) => current.filter((message) => message.id !== assistantId));
      return;
    }
    if (event.type === "done") {
      setStatusMessage(null);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, isStreaming: false } : message,
        ),
      );
    }
  }, []);

  async function sendMessage() {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) {
      return;
    }

    const userMessage: AssistantMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    const assistantId = crypto.randomUUID();
    const nextMessages = [
      ...messages,
      userMessage,
      { id: assistantId, role: "assistant" as const, content: "", isStreaming: true },
    ];

    setMessages(nextMessages);
    setInput("");
    setError(null);
    setIsStreaming(true);
    setStatusMessage(copy.statusPreparing);

    try {
      await streamInstructionAssistant(
        {
          scope,
          draft_content: draftContent,
          messages: nextMessages
            .filter((message) => !message.isStreaming)
            .map((message) => ({
              role: message.role,
              content: message.content,
            })),
          locale,
        },
        (streamEvent) => handleStreamEvent(streamEvent, assistantId),
      );
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Stream failed");
      setMessages((current) => current.filter((message) => message.id !== assistantId));
    } finally {
      setIsStreaming(false);
      setStatusMessage(null);
    }
  }

  function handleApplyDraft() {
    if (!lastAssistantMessage?.content) {
      return;
    }
    const proposed = extractProposedDraft(lastAssistantMessage.content);
    if (!proposed) {
      return;
    }
    if (!window.confirm(copy.applyConfirm)) {
      return;
    }
    onApplyDraft(proposed);
  }

  return (
    <aside className="flex h-full min-h-[20rem] flex-col rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="border-b border-zinc-200 px-4 py-3 text-start dark:border-zinc-800">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h3>
        <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {!messages.length ? (
          <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.empty}</p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`text-start text-sm leading-6 ${
                message.role === "user"
                  ? "ms-auto max-w-[95%] rounded-lg bg-zinc-900 px-3 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "max-w-[95%] whitespace-pre-wrap text-zinc-800 dark:text-zinc-200"
              }`}
            >
              {message.isStreaming && !message.content ? <StreamingDots /> : message.content}
            </div>
          ))
        )}
        {statusMessage ? (
          <p className="text-start text-xs text-zinc-500 dark:text-zinc-400">{statusMessage}</p>
        ) : null}
        {error ? (
          <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
        ) : null}
      </div>

      <div className="space-y-2 border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
        {lastAssistantMessage && !isStreaming ? (
          <button
            type="button"
            onClick={handleApplyDraft}
            disabled={disabled}
            className="inline-flex h-9 w-full items-center justify-center rounded-lg border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
          >
            {copy.apply}
          </button>
        ) : null}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void sendMessage();
              }
            }}
            placeholder={copy.placeholder}
            disabled={disabled || isStreaming}
            className="block min-w-0 flex-1 rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950"
          />
          <button
            type="button"
            onClick={() => void sendMessage()}
            disabled={disabled || isStreaming || !input.trim()}
            className="inline-flex h-10 shrink-0 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {isStreaming ? copy.sending : copy.send}
          </button>
        </div>
      </div>
    </aside>
  );
}
