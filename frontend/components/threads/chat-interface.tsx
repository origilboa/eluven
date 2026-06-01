"use client";

import { useCallback, useMemo, useState } from "react";

import { streamThreadMessage } from "@/lib/stream";
import type {
  MessageResponse,
  StreamEvent,
  TaskMemoryEntryResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  memoryEntries?: TaskMemoryEntryResponse[];
  isStreaming?: boolean;
};

type ChatInterfaceProps = {
  locale: Locale;
  threadId: string;
  initialMessages: MessageResponse[];
};

function toChatMessages(messages: MessageResponse[]): ChatMessage[] {
  return messages
    .filter((message) => message.role === "user" || message.role === "assistant")
    .map((message) => ({
      id: message.id,
      role: message.role as "user" | "assistant",
      content: message.content,
    }));
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

function MemoryInlineCard({
  entry,
  locale,
}: {
  entry: TaskMemoryEntryResponse;
  locale: Locale;
}) {
  return (
    <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-start text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">
      <p className="text-xs font-semibold uppercase tracking-wide">
        {locale === "he" ? "רשומת זיכרון" : "Memory entry"} · {entry.entry_type}
      </p>
      <p className="mt-1 leading-6">{entry.content}</p>
    </div>
  );
}

export function ChatInterface({ locale, threadId, initialMessages }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => toChatMessages(initialMessages));
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const copy = useMemo(
    () =>
      locale === "he"
        ? {
            placeholder: "כתוב הודעה…",
            send: "שליחה",
            sending: "שולח…",
            empty: "התחל שיחה עם העוזר.",
          }
        : {
            placeholder: "Write a message…",
            send: "Send",
            sending: "Sending…",
            empty: "Start a conversation with the assistant.",
          },
    [locale],
  );

  const handleStreamEvent = useCallback(
    (event: StreamEvent, assistantId: string) => {
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

      if (event.type === "memory_entry") {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  memoryEntries: [...(message.memoryEntries ?? []), event.entry],
                }
              : message,
          ),
        );
        return;
      }

      if (event.type === "error") {
        setError(event.message);
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
    },
    [],
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = input.trim();
    if (!content || isStreaming) {
      return;
    }

    setError(null);
    setInput("");

    const userId = `user-${Date.now()}`;
    const assistantId = `assistant-${Date.now()}`;

    setMessages((current) => [
      ...current,
      { id: userId, role: "user", content },
      { id: assistantId, role: "assistant", content: "", isStreaming: true, memoryEntries: [] },
    ]);
    setIsStreaming(true);

    try {
      await streamThreadMessage(threadId, content, (streamEvent) =>
        handleStreamEvent(streamEvent, assistantId),
      );
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Stream failed");
      setMessages((current) => current.filter((message) => message.id !== assistantId));
    } finally {
      setIsStreaming(false);
      setStatusMessage(null);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, isStreaming: false } : message,
        ),
      );
    }
  }

  return (
    <div className="flex h-[min(70vh,720px)] flex-col rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{copy.empty}</p>
        ) : null}

        {messages.map((message) => {
          const isUser = message.role === "user";
          return (
            <div
              key={message.id}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-start text-sm leading-6 ${
                  isUser
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "bg-zinc-100 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-50"
                }`}
              >
                {message.content ? <p className="whitespace-pre-wrap">{message.content}</p> : null}
                {message.isStreaming && !message.content ? <StreamingDots /> : null}
                {message.memoryEntries?.map((entry) => (
                  <MemoryInlineCard key={entry.id} entry={entry} locale={locale} />
                ))}
              </div>
            </div>
          );
        })}

        {statusMessage ? (
          <p className="text-start text-xs text-zinc-500 dark:text-zinc-400">{statusMessage}</p>
        ) : null}

        {error ? (
          <p
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            role="alert"
          >
            {error}
          </p>
        ) : null}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-zinc-200 p-4 dark:border-zinc-800"
      >
        <div className="flex items-end gap-3">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            rows={2}
            placeholder={copy.placeholder}
            disabled={isStreaming}
            className="min-h-11 flex-1 resize-none rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {isStreaming ? copy.sending : copy.send}
          </button>
        </div>
      </form>
    </div>
  );
}
