"use client";

import type { ReactNode } from "react";

import { InstructionAssistantPanel } from "@/components/instructions/instruction-assistant-panel";
import { AuthoringSplitLayout } from "@/components/shared/authoring-split-layout";
import {
  useInstructionDraftGate,
  type InstructionDraftGateState,
} from "@/lib/use-instruction-draft-gate";
import type { InstructionAssistantScope } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type InstructionAuthoringWorkbenchProps = {
  locale: Locale;
  scope: InstructionAssistantScope;
  draftContent: string;
  onDraftChange: (content: string) => void;
  disabled?: boolean;
  contentLabel: string;
  textareaId: string;
  rows?: number;
  footer?: ReactNode;
  onSave: (payload: { integrityApprovalToken: string }) => void;
  savePending?: boolean;
  saveLabel: string;
  savingLabel: string;
  showSaveButton?: boolean;
  gate?: InstructionDraftGateState;
  onCancel?: () => void;
  cancelLabel?: string;
};

export function InstructionAuthoringWorkbench({
  locale,
  scope,
  draftContent,
  onDraftChange,
  disabled = false,
  contentLabel,
  textareaId,
  rows = 10,
  footer,
  onSave,
  savePending = false,
  saveLabel,
  savingLabel,
  showSaveButton = true,
  gate: externalGate,
  onCancel,
  cancelLabel,
}: InstructionAuthoringWorkbenchProps) {
  const internalGate = useInstructionDraftGate(scope, draftContent, locale);
  const gate = externalGate ?? internalGate;

  const copy =
    locale === "he"
      ? {
          gateIdle: "יש להריץ בדיקת שלמות לפני שמירה.",
          gateChecking: "מריץ בדיקת שלמות…",
          gatePassed: "בדיקת השלמות עברה — ניתן לשמור.",
          gateFailed: "נמצאו בעיות שלמות — תקן לפני שמירה.",
          gateStale: "הטיוטה השתנתה — הרץ בדיקת שלמות שוב.",
          runCheck: "הרץ בדיקת שלמות",
          saveBlocked: "הרץ בדיקת שלמות מוצלחת לפני שמירה.",
          issuesHeading: "ממצאי שלמות",
        }
      : {
          gateIdle: "Run an integrity check before saving.",
          gateChecking: "Running integrity check…",
          gatePassed: "Integrity check passed — you may save.",
          gateFailed: "Integrity issues found — fix before saving.",
          gateStale: "Draft changed — re-run integrity check.",
          runCheck: "Run integrity check",
          saveBlocked: "Pass an integrity check before saving.",
          issuesHeading: "Integrity findings",
        };

  const gateMessage =
    gate.status === "checking"
      ? copy.gateChecking
      : gate.status === "passed"
        ? copy.gatePassed
        : gate.status === "failed"
          ? copy.gateFailed
          : gate.status === "stale"
            ? copy.gateStale
            : copy.gateIdle;

  const gateTone =
    gate.status === "passed"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
      : gate.status === "failed" || gate.checkError
        ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
        : gate.status === "stale"
          ? "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200"
          : "border-zinc-200 bg-zinc-50 text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300";

  function handleSave(event: React.FormEvent) {
    event.preventDefault();
    if (!gate.canSave || !gate.approvalToken) {
      return;
    }
    onSave({ integrityApprovalToken: gate.approvalToken });
  }

  return (
    <AuthoringSplitLayout
      form={
        <form className="space-y-4" onSubmit={handleSave}>
          <div className="space-y-2 text-start">
            <label htmlFor={textareaId} className="block text-sm font-medium">
              {contentLabel}
            </label>
            <textarea
              id={textareaId}
              required
              rows={rows}
              value={draftContent}
              onChange={(event) => onDraftChange(event.target.value)}
              disabled={disabled}
              className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 font-mono text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
            />
          </div>

          <div className={`rounded-lg border px-3 py-2 text-start text-sm ${gateTone}`}>
            <p>{gateMessage}</p>
            {gate.summary && gate.status !== "idle" ? (
              <p className="mt-1 text-xs opacity-90">{gate.summary}</p>
            ) : null}
            {gate.checkError ? <p className="mt-1 text-xs">{gate.checkError}</p> : null}
          </div>

          {gate.issues.length > 0 ? (
            <div className="space-y-2 text-start">
              <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                {copy.issuesHeading}
              </h4>
              <ul className="space-y-2">
                {gate.issues.map((issue, index) => (
                  <li
                    key={`${issue.code}-${index}`}
                    className="rounded-lg border border-zinc-200 bg-white p-3 text-sm dark:border-zinc-800 dark:bg-zinc-950"
                  >
                    <p className="font-medium text-zinc-900 dark:text-zinc-50">{issue.title}</p>
                    <p className="mt-1 text-zinc-600 dark:text-zinc-400">{issue.message}</p>
                    <p className="mt-2 text-zinc-700 dark:text-zinc-300">{issue.recommendation}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {footer}

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void gate.runIntegrityCheck(draftContent)}
                disabled={disabled || gate.status === "checking" || !draftContent.trim()}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 bg-white px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                {gate.status === "checking" ? copy.gateChecking : copy.runCheck}
              </button>
              {showSaveButton ? (
                <button
                  type="submit"
                  disabled={savePending || !gate.canSave || disabled}
                  title={!gate.canSave ? copy.saveBlocked : undefined}
                  className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {savePending ? savingLabel : saveLabel}
                </button>
              ) : null}
            </div>
            {onCancel ? (
              <button
                type="button"
                onClick={onCancel}
                disabled={disabled || savePending}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                {cancelLabel}
              </button>
            ) : null}
          </div>
        </form>
      }
      assistant={
        <InstructionAssistantPanel
          locale={locale}
          scope={scope}
          draftContent={draftContent}
          onApplyDraft={onDraftChange}
          disabled={disabled}
          integrityIssues={gate.issues}
          onIntegrityIssuesChange={() => gate.resetGate()}
        />
      }
    />
  );
}

export type { InstructionDraftGateState };
export { useInstructionDraftGate } from "@/lib/use-instruction-draft-gate";
