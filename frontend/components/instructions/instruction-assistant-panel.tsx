"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  streamInstructionAssistant,
  streamInstructionIntegrityRemediate,
} from "@/lib/stream";
import type {
  InstructionAssistantScope,
  InstructionIntegrityIssue,
  StreamEvent,
} from "@/lib/types/api";
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
  integrityIssues?: InstructionIntegrityIssue[];
  onIntegrityIssuesChange?: () => void;
};

const PROPOSED_PARTIAL_FIX_MARKERS = ["## Proposed partial fix", "# Proposed partial fix"];
const PROPOSED_DRAFT_MARKERS = ["## Proposed instruction draft", "# Proposed instruction draft"];

function findProposalMarker(
  content: string,
  markers: string[],
): { marker: string; index: number } | null {
  let best: { marker: string; index: number } | null = null;
  for (const marker of markers) {
    const index = content.indexOf(marker);
    if (index >= 0 && (best === null || index < best.index)) {
      best = { marker, index };
    }
  }
  return best;
}

function stripProposalCommentary(text: string): string {
  const withoutRule = text.split(/\n---\n/)[0] ?? text;
  const withoutChangelog = withoutRule.split(/\n\*\*Changes made:\*\*/i)[0] ?? withoutRule;
  return withoutChangelog.trim();
}

function hasApplyableProposal(content: string): boolean {
  return (
    findProposalMarker(content, PROPOSED_PARTIAL_FIX_MARKERS) !== null ||
    findProposalMarker(content, PROPOSED_DRAFT_MARKERS) !== null
  );
}

function extractProposedDraft(content: string): string {
  const partial = findProposalMarker(content, PROPOSED_PARTIAL_FIX_MARKERS);
  if (partial) {
    const raw = content.slice(partial.index + partial.marker.length).trim();
    return stripProposalCommentary(raw);
  }
  const draft = findProposalMarker(content, PROPOSED_DRAFT_MARKERS);
  if (draft) {
    const raw = content.slice(draft.index + draft.marker.length).trim();
    return stripProposalCommentary(raw);
  }
  return "";
}

function applyPartialFix(base: string, fix: string): string {
  const trimmedFix = fix.trim();
  if (!trimmedFix) {
    return base;
  }
  if (base.includes(trimmedFix)) {
    return base;
  }
  return `${base.trimEnd()}\n\n${trimmedFix}`;
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
  integrityIssues = [],
  onIntegrityIssuesChange,
}: InstructionAssistantPanelProps) {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [input, setInput] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remediationMode, setRemediationMode] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, statusMessage, error, isStreaming]);

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
            applyPartial: "החל תיקון חלקי",
            applyConfirm: "להחליף את תוכן ההוראות בטיוטה שהעוזר הציע?",
            applyPartialConfirm: "להוסיף את התיקון החלקי לטיוטה?",
            statusPreparing: "מכין תשובה…",
            reviewCompleteness: "בדיקת שלמות תוכן",
            reviewCompletenessPrompt:
              "הרץ בדיקת שלמות תוכן — מה חסר או דל בטיוטה לעומת השכבות שמעל?",
            reviewCompletenessEmpty: "הוסף טקסט לטיוטה לפני בדיקת שלמות תוכן.",
            fixWithAssistant: "תקן עם העוזר",
            exitRemediation: "יציאה מתיקון",
            remediationHint: "מצב תיקון פעיל — העוזר יציע תיקונים מבוססי ממצאים.",
          }
        : {
            title: "Instruction assistant",
            subtitle: "Chat to draft or refine instructions for this layer.",
            placeholder: "Ask for a draft, review, or improvement…",
            send: "Send",
            sending: "Sending…",
            empty: "Ask the assistant to help author instructions.",
            apply: "Apply to draft",
            applyPartial: "Apply partial fix",
            applyConfirm: "Replace the instruction textarea with the assistant's proposed draft?",
            applyPartialConfirm: "Append the assistant's partial fix to the draft?",
            statusPreparing: "Preparing response…",
            reviewCompleteness: "Review completeness",
            reviewCompletenessPrompt:
              "Run a completeness review — what is missing or thin compared to inherited layers?",
            reviewCompletenessEmpty: "Add draft text before running a completeness review.",
            fixWithAssistant: "Fix with assistant",
            exitRemediation: "Exit remediation",
            remediationHint: "Remediation mode — the assistant proposes fixes from findings.",
          },
    [locale],
  );

  const lastAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant" && message.content),
    [messages],
  );

  const hasPartialFix = Boolean(
    lastAssistantMessage &&
      findProposalMarker(lastAssistantMessage.content, PROPOSED_PARTIAL_FIX_MARKERS),
  );

  const canApplyProposal = Boolean(
    lastAssistantMessage && hasApplyableProposal(lastAssistantMessage.content),
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

  async function sendMessage(
    messageText?: string,
    options?: { completenessReview?: boolean },
  ) {
    const trimmed = (messageText ?? input).trim();
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
    if (!messageText) {
      setInput("");
    }
    setError(null);
    setIsStreaming(true);
    setStatusMessage(copy.statusPreparing);

    const chatPayload = nextMessages
      .filter((message) => !message.isStreaming)
      .map((message) => ({
        role: message.role,
        content: message.content,
      }));

    try {
      if (remediationMode && integrityIssues.length > 0) {
        await streamInstructionIntegrityRemediate(
          {
            scope,
            draft_content: draftContent,
            issues: integrityIssues,
            messages: chatPayload,
            locale,
          },
          (streamEvent) => handleStreamEvent(streamEvent, assistantId),
        );
      } else {
        await streamInstructionAssistant(
          {
            scope,
            draft_content: draftContent,
            messages: chatPayload,
            locale,
            completeness_review: options?.completenessReview ?? false,
          },
          (streamEvent) => handleStreamEvent(streamEvent, assistantId),
        );
      }
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Stream failed");
      setMessages((current) => current.filter((message) => message.id !== assistantId));
    } finally {
      setIsStreaming(false);
      setStatusMessage(null);
    }
  }

  function handleApplyDraft(partial: boolean) {
    if (!lastAssistantMessage?.content) {
      return;
    }
    const proposed = extractProposedDraft(lastAssistantMessage.content);
    if (!proposed) {
      return;
    }
    const confirmText = partial ? copy.applyPartialConfirm : copy.applyConfirm;
    if (!window.confirm(confirmText)) {
      return;
    }
    onIntegrityIssuesChange?.();
    if (partial) {
      onApplyDraft(applyPartialFix(draftContent, proposed));
      return;
    }
    onApplyDraft(proposed);
  }

  function startRemediation() {
    if (!integrityIssues.length) {
      return;
    }
    setRemediationMode(true);
    setMessages([]);
    setError(null);
  }

  return (
    <aside className="flex max-h-[min(36rem,70vh)] min-h-[20rem] flex-col overflow-hidden rounded-lg border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="shrink-0 border-b border-zinc-200 px-4 py-3 text-start dark:border-zinc-800">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h3>
        <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
        {remediationMode ? (
          <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">{copy.remediationHint}</p>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3">
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
        <div ref={messagesEndRef} />
      </div>

      <div className="shrink-0 space-y-2 border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
        {integrityIssues.length > 0 && !remediationMode ? (
          <button
            type="button"
            onClick={startRemediation}
            disabled={disabled || isStreaming}
            className="inline-flex h-9 w-full items-center justify-center rounded-lg border border-amber-300 bg-amber-50 px-3 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-100 disabled:opacity-60 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
          >
            {copy.fixWithAssistant}
          </button>
        ) : null}
        {remediationMode ? (
          <button
            type="button"
            onClick={() => setRemediationMode(false)}
            disabled={isStreaming}
            className="inline-flex h-9 w-full items-center justify-center rounded-lg border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200"
          >
            {copy.exitRemediation}
          </button>
        ) : null}
        {!remediationMode ? (
          <>
            <button
              type="button"
              onClick={() => {
                if (!draftContent.trim()) {
                  setError(copy.reviewCompletenessEmpty);
                  return;
                }
                void sendMessage(copy.reviewCompletenessPrompt, { completenessReview: true });
              }}
              disabled={disabled || isStreaming || !draftContent.trim()}
              className="inline-flex h-9 w-full items-center justify-center rounded-lg border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
            >
              {copy.reviewCompleteness}
            </button>
          </>
        ) : null}
        {lastAssistantMessage && !isStreaming && canApplyProposal ? (
          <>
            {hasPartialFix ? (
              <button
                type="button"
                onClick={() => handleApplyDraft(true)}
                disabled={disabled}
                className="inline-flex h-9 w-full items-center justify-center rounded-lg border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                {copy.applyPartial}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => handleApplyDraft(false)}
              disabled={disabled}
              className="inline-flex h-9 w-full items-center justify-center rounded-lg border border-zinc-300 bg-white px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
            >
              {copy.apply}
            </button>
          </>
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
