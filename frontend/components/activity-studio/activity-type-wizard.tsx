"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ActivityOrchestratorPanel } from "@/components/activity-studio/activity-orchestrator-panel";
import { PromptAssistantPanel } from "@/components/activity-studio/prompt-assistant-panel";
import {
  type EntryFormState,
  type PromptDraft,
  parseTokenBudget,
} from "@/components/activity-studio/activity-entry-detail-tabs";
import { InstructionAssistantPanel } from "@/components/instructions/instruction-assistant-panel";
import { AuthoringSplitLayout } from "@/components/shared/authoring-split-layout";
import { api } from "@/lib/api";
import { MODULE_DEFINITIONS, MODULE_TYPE_EXTERNAL_PAPER_REVIEW } from "@/lib/modules";
import type {
  ActivityAssistantStep,
  ActivityTypeDraft,
  AdminActivityLibraryDetailResponse,
  CreateActivityLibraryEntryRequest,
  ReplaceActivityPromptsRequest,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

const STEPS: ActivityAssistantStep[] = [
  "purpose",
  "identity",
  "mode",
  "instructions",
  "prompts",
  "routing",
  "review",
];

const EMPTY_FORM: EntryFormState = {
  display_name: "",
  description: "",
  default_instruction_content: "",
  default_model_id: "",
  fallback_model_id: "",
  token_budget: "",
  token_budget_warning_threshold: "0.8",
  supports_automation: true,
  is_active: true,
};

type ActivityTypeWizardProps = {
  locale: Locale;
};

function buildPromptsPayload(prompts: PromptDraft[]): ReplaceActivityPromptsRequest {
  return {
    prompts: prompts
      .filter((prompt) => prompt.prompt_text.trim())
      .map((prompt) => ({ prompt_text: prompt.prompt_text.trim() })),
  };
}

export function ActivityTypeWizard({ locale }: ActivityTypeWizardProps) {
  const router = useRouter();
  const [stepIndex, setStepIndex] = useState(0);
  const [moduleType, setModuleType] = useState(MODULE_TYPE_EXTERNAL_PAPER_REVIEW);
  const [purposeNotes, setPurposeNotes] = useState("");
  const [threadType, setThreadType] = useState("");
  const [form, setForm] = useState<EntryFormState>(EMPTY_FORM);
  const [prompts, setPrompts] = useState<PromptDraft[]>([]);
  const [error, setError] = useState<string | null>(null);

  const step = STEPS[stepIndex];

  const copy =
    locale === "he"
      ? {
          title: "הגדרה מודרכת של סוג פעילות",
          back: "חזרה לספרייה",
          previous: "הקודם",
          next: "המשך",
          publish: "פרסם",
          publishing: "מפרסם…",
          purpose: "מטרה",
          identity: "זהות",
          mode: "מצב",
          instructions: "הוראות",
          prompts: "הצעות",
          routing: "ניתוב",
          review: "סקירה",
          module: "מודול",
          purposeNotes: "הערות מטרה",
        }
      : {
          title: "Guided activity type setup",
          back: "Back to library",
          previous: "Back",
          next: "Continue",
          publish: "Publish",
          publishing: "Publishing…",
          purpose: "Purpose",
          identity: "Identity",
          mode: "Mode",
          instructions: "Instructions",
          prompts: "Prompts",
          routing: "Routing",
          review: "Review",
          module: "Module",
          purposeNotes: "Purpose notes",
        };

  const stepLabels: Record<ActivityAssistantStep, string> = {
    purpose: copy.purpose,
    identity: copy.identity,
    mode: copy.mode,
    instructions: copy.instructions,
    prompts: copy.prompts,
    routing: copy.routing,
    review: copy.review,
  };

  const draft: ActivityTypeDraft = useMemo(
    () => ({
      module_type: moduleType,
      purpose_notes: purposeNotes || null,
      thread_type: threadType || null,
      display_name: form.display_name || null,
      description: form.description || null,
      supports_automation: form.supports_automation,
      default_instruction_content: form.default_instruction_content || null,
      prompts: prompts.map((prompt, index) => ({
        prompt_text: prompt.prompt_text,
        stage: prompt.stage ?? "opening",
        sequence_index: index,
      })),
      default_model_id: form.default_model_id || null,
      fallback_model_id: form.fallback_model_id || null,
      token_budget: parseTokenBudget(form.token_budget),
      token_budget_warning_threshold: Number.parseFloat(form.token_budget_warning_threshold),
      scope_level: "platform",
    }),
    [form, moduleType, prompts, purposeNotes, threadType],
  );

  const publishMutation = useMutation({
    mutationFn: async () => {
      const body: CreateActivityLibraryEntryRequest = {
        thread_type: threadType.trim(),
        module_type: moduleType,
        display_name: form.display_name.trim(),
        description: form.description.trim() ? form.description.trim() : null,
        default_instruction_content: form.default_instruction_content.trim()
          ? form.default_instruction_content.trim()
          : null,
        default_model_id: form.default_model_id.trim() || null,
        fallback_model_id: form.fallback_model_id.trim() ? form.fallback_model_id.trim() : null,
        token_budget: parseTokenBudget(form.token_budget),
        token_budget_warning_threshold: Number.parseFloat(form.token_budget_warning_threshold),
        supports_automation: form.supports_automation,
        is_active: form.is_active,
      };
      const detail = await api.post<AdminActivityLibraryDetailResponse>(
        "/admin/activity-library",
        body,
      );
      const promptPayload = buildPromptsPayload(prompts);
      if (promptPayload.prompts.length > 0) {
        return api.put<AdminActivityLibraryDetailResponse>(
          `/admin/activity-library/${detail.id}/prompts`,
          promptPayload,
        );
      }
      return detail;
    },
    onSuccess: () => {
      router.push(`/${locale}/admin`);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const showOrchestrator = step === "purpose" || step === "identity" || step === "mode" || step === "routing";

  const stepBody = (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      {step === "purpose" ? (
        <div className="space-y-4">
          <label className="block text-start text-sm">
            <span className="font-medium">{copy.module}</span>
            <select
              value={moduleType}
              onChange={(event) => setModuleType(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {MODULE_DEFINITIONS.map((module) => (
                <option key={module.value} value={module.value}>
                  {module.label[locale]}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-start text-sm">
            <span className="font-medium">{copy.purposeNotes}</span>
            <textarea
              rows={4}
              value={purposeNotes}
              onChange={(event) => setPurposeNotes(event.target.value)}
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
        </div>
      ) : null}

      {step === "identity" ? (
        <div className="space-y-4">
          <label className="block text-start text-sm">
            <span className="font-medium">Type slug</span>
            <input
              required
              value={threadType}
              onChange={(event) => setThreadType(event.target.value)}
              pattern="[a-z][a-z0-9_]*"
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="block text-start text-sm">
            <span className="font-medium">Display name</span>
            <input
              required
              value={form.display_name}
              onChange={(event) => setForm((c) => ({ ...c, display_name: event.target.value }))}
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="block text-start text-sm">
            <span className="font-medium">Description</span>
            <textarea
              rows={3}
              value={form.description}
              onChange={(event) => setForm((c) => ({ ...c, description: event.target.value }))}
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
        </div>
      ) : null}

      {step === "mode" ? (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.supports_automation}
            onChange={(event) =>
              setForm((c) => ({ ...c, supports_automation: event.target.checked }))
            }
          />
          Supports automation
        </label>
      ) : null}

      {step === "instructions" ? (
        <AuthoringSplitLayout
          form={
            <label className="block text-start text-sm">
              <span className="font-medium">Default instructions</span>
              <textarea
                rows={12}
                value={form.default_instruction_content}
                onChange={(event) =>
                  setForm((c) => ({ ...c, default_instruction_content: event.target.value }))
                }
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
            </label>
          }
          assistant={
            threadType && moduleType ? (
              <InstructionAssistantPanel
                locale={locale}
                scope={{
                  authoring_target: "activity_library_default",
                  level: "platform",
                  thread_type: threadType,
                  module_type: moduleType,
                  activity_draft: {
                    display_name: form.display_name,
                    description: form.description,
                    thread_type: threadType,
                    module_type: moduleType,
                    supports_automation: form.supports_automation,
                  },
                }}
                draftContent={form.default_instruction_content}
                onApplyDraft={(content) =>
                  setForm((c) => ({ ...c, default_instruction_content: content }))
                }
              />
            ) : null
          }
        />
      ) : null}

      {step === "prompts" ? (
        <AuthoringSplitLayout
          form={
            <div className="space-y-3">
              <button
                type="button"
                onClick={() => setPrompts((current) => [...current, { prompt_text: "" }])}
                className="text-sm font-medium text-zinc-600 underline-offset-4 hover:underline"
              >
                Add prompt
              </button>
              {prompts.map((prompt, index) => (
                <textarea
                  key={`wizard-prompt-${index}`}
                  rows={2}
                  value={prompt.prompt_text}
                  onChange={(event) =>
                    setPrompts((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, prompt_text: event.target.value }
                          : item,
                      ),
                    )
                  }
                  className="block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              ))}
            </div>
          }
          assistant={
            threadType && moduleType ? (
              <PromptAssistantPanel
                locale={locale}
                scope={{
                  authoring_mode: "create",
                  level: "platform",
                  thread_type: threadType,
                  module_type: moduleType,
                  supports_automation: form.supports_automation,
                  default_instruction_content: form.default_instruction_content,
                  activity_draft: {
                    display_name: form.display_name,
                    description: form.description,
                    thread_type: threadType,
                    module_type: moduleType,
                  },
                }}
                draftPrompts={prompts}
                defaultInstructionContent={form.default_instruction_content}
                onApplyPrompts={(next) => setPrompts(next)}
              />
            ) : null
          }
        />
      ) : null}

      {step === "routing" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-start text-sm">
            <span className="font-medium">Default model</span>
            <input
              value={form.default_model_id}
              onChange={(event) =>
                setForm((c) => ({ ...c, default_model_id: event.target.value }))
              }
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-xs dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="block text-start text-sm">
            <span className="font-medium">Token budget</span>
            <input
              value={form.token_budget}
              onChange={(event) => setForm((c) => ({ ...c, token_budget: event.target.value }))}
              className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
        </div>
      ) : null}

      {step === "review" ? (
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-zinc-50 p-4 text-start font-mono text-xs dark:bg-zinc-900">
          {JSON.stringify(draft, null, 2)}
        </pre>
      ) : null}
    </div>
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-start">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
          <Link
            href={`/${locale}/admin`}
            className="mt-1 inline-block text-sm text-zinc-500 underline-offset-4 hover:underline"
          >
            {copy.back}
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
        {STEPS.map((item, index) => (
          <button
            key={item}
            type="button"
            onClick={() => setStepIndex(index)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              stepIndex === index
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
            }`}
          >
            {stepLabels[item]}
          </button>
        ))}
      </div>

      {showOrchestrator ? (
        <AuthoringSplitLayout
          form={stepBody}
          assistant={<ActivityOrchestratorPanel locale={locale} step={step} draft={draft} />}
        />
      ) : (
        stepBody
      )}

      <div className="flex justify-between gap-2">
        <button
          type="button"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex((current) => Math.max(0, current - 1))}
          className="inline-flex h-10 items-center rounded-lg border px-4 text-sm font-medium disabled:opacity-50"
        >
          {copy.previous}
        </button>
        {step === "review" ? (
          <button
            type="button"
            disabled={publishMutation.isPending || !threadType.trim() || !form.display_name.trim()}
            onClick={() => publishMutation.mutate()}
            className="inline-flex h-10 items-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {publishMutation.isPending ? copy.publishing : copy.publish}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setStepIndex((current) => Math.min(STEPS.length - 1, current + 1))}
            className="inline-flex h-10 items-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            {copy.next}
          </button>
        )}
      </div>

      {error ? (
        <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}
    </div>
  );
}
