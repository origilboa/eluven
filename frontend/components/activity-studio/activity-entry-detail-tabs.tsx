"use client";

import { useMemo, useState } from "react";

import { PromptAssistantPanel } from "@/components/activity-studio/prompt-assistant-panel";
import { InstructionAssistantPanel } from "@/components/instructions/instruction-assistant-panel";
import { AuthoringSplitLayout } from "@/components/shared/authoring-split-layout";
import type { InstructionAssistantScope, PromptAssistantScope } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

export type PromptDraft = {
  prompt_text: string;
  stage?: "opening" | "mid" | "closing";
};

export type EntryFormState = {
  display_name: string;
  description: string;
  default_instruction_content: string;
  default_model_id: string;
  fallback_model_id: string;
  token_budget: string;
  token_budget_warning_threshold: string;
  supports_automation: boolean;
  is_active: boolean;
};

type DetailTab = "settings" | "instructions" | "prompts";

type ActivityEntryDetailTabsProps = {
  locale: Locale;
  mode: "create" | "edit";
  moduleType: string;
  threadType: string;
  onThreadTypeChange?: (value: string) => void;
  entryId?: string;
  scopeLevel?: "platform" | "org";
  form: EntryFormState;
  setForm: React.Dispatch<React.SetStateAction<EntryFormState>>;
  prompts: PromptDraft[];
  setPrompts: React.Dispatch<React.SetStateAction<PromptDraft[]>>;
  onSaveSettings: () => void;
  onSavePrompts: () => void;
  onCreate?: () => void;
  isSavingSettings: boolean;
  isSavingPrompts: boolean;
  isCreating?: boolean;
  copy: Record<string, string>;
};

function parseTokenBudget(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function ActivityEntryDetailTabs({
  locale,
  mode,
  moduleType,
  threadType,
  onThreadTypeChange,
  entryId,
  scopeLevel = "platform",
  form,
  setForm,
  prompts,
  setPrompts,
  onSaveSettings,
  onSavePrompts,
  onCreate,
  isSavingSettings,
  isSavingPrompts,
  isCreating = false,
  copy,
}: ActivityEntryDetailTabsProps) {
  const [activeTab, setActiveTab] = useState<DetailTab>("settings");

  const tabCopy =
    locale === "he"
      ? { settings: "הגדרות", instructions: "הוראות", prompts: "הצעות" }
      : { settings: "Settings", instructions: "Instructions", prompts: "Prompts" };

  const activityDraft = useMemo(
    () => ({
      display_name: form.display_name || null,
      description: form.description || null,
      thread_type: threadType || null,
      module_type: moduleType || null,
      supports_automation: form.supports_automation,
    }),
    [form.description, form.display_name, form.supports_automation, moduleType, threadType],
  );

  const instructionScope: InstructionAssistantScope = useMemo(
    () => ({
      authoring_target: "activity_library_default",
      level: scopeLevel,
      thread_type: threadType || null,
      module_type: moduleType || null,
      ...(mode === "edit" && entryId ? { activity_entry_id: entryId } : {}),
      ...(mode === "create" ? { activity_draft: activityDraft } : {}),
    }),
    [activityDraft, entryId, mode, moduleType, scopeLevel, threadType],
  );

  const promptScope: PromptAssistantScope = useMemo(
    () => ({
      authoring_mode: mode === "create" ? "create" : "edit",
      level: scopeLevel,
      thread_type: threadType || null,
      module_type: moduleType || null,
      supports_automation: form.supports_automation,
      default_instruction_content: form.default_instruction_content || null,
      ...(mode === "edit" && entryId ? { activity_entry_id: entryId } : {}),
      ...(mode === "create" ? { activity_draft: activityDraft } : {}),
    }),
    [
      activityDraft,
      entryId,
      form.default_instruction_content,
      form.supports_automation,
      mode,
      moduleType,
      scopeLevel,
      threadType,
    ],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
        {(["settings", "instructions", "prompts"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
            }`}
          >
            {tabCopy[tab]}
          </button>
        ))}
      </div>

      {activeTab === "settings" ? (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (mode === "create" && onCreate) {
              onCreate();
            } else {
              onSaveSettings();
            }
          }}
        >
          {mode === "create" ? (
            <label className="block text-start text-sm">
              <span className="font-medium">{copy.threadType}</span>
              <input
                required
                value={threadType}
                onChange={(event) => onThreadTypeChange?.(event.target.value)}
                pattern="[a-z][a-z0-9_]*"
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-900"
              />
            </label>
          ) : null}
          <SettingsFields form={form} setForm={setForm} copy={copy} />
          <button
            type="submit"
            disabled={isSavingSettings || isCreating}
            className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {mode === "create"
              ? isCreating
                ? copy.creating
                : copy.create
              : isSavingSettings
                ? copy.saving
                : copy.saveEntry}
          </button>
        </form>
      ) : null}

      {activeTab === "instructions" ? (
        <AuthoringSplitLayout
          form={
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                onSaveSettings();
              }}
            >
              <label className="block text-start text-sm">
                <span className="font-medium">{copy.defaultInstructions}</span>
                <textarea
                  rows={12}
                  value={form.default_instruction_content}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      default_instruction_content: event.target.value,
                    }))
                  }
                  className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>
              {mode === "edit" ? (
                <button
                  type="submit"
                  disabled={isSavingSettings}
                  className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {isSavingSettings ? copy.saving : copy.saveEntry}
                </button>
              ) : null}
            </form>
          }
          assistant={
            threadType && moduleType ? (
              <InstructionAssistantPanel
                locale={locale}
                scope={instructionScope}
                draftContent={form.default_instruction_content}
                onApplyDraft={(content) =>
                  setForm((current) => ({ ...current, default_instruction_content: content }))
                }
              />
            ) : null
          }
        />
      ) : null}

      {activeTab === "prompts" ? (
        <AuthoringSplitLayout
          form={
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-start text-sm font-semibold">{copy.activityPrompts}</h4>
                <button
                  type="button"
                  onClick={() => setPrompts((current) => [...current, { prompt_text: "" }])}
                  className="text-sm font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
                >
                  {copy.addPrompt}
                </button>
              </div>
              {prompts.map((prompt, index) => (
                <div
                  key={`prompt-${index}`}
                  className="space-y-2 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
                >
                  <label className="block text-start text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{copy.prompt}</span>
                      <button
                        type="button"
                        disabled={isSavingPrompts || (form.supports_automation && prompts.length <= 1)}
                        onClick={() =>
                          setPrompts((current) => current.filter((_, itemIndex) => itemIndex !== index))
                        }
                        className="text-xs font-medium text-red-600 hover:underline disabled:cursor-not-allowed disabled:text-zinc-400 dark:text-red-400"
                      >
                        {copy.remove}
                      </button>
                    </div>
                    <textarea
                      required
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
                      className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                    />
                  </label>
                </div>
              ))}
              {mode === "edit" ? (
                <button
                  type="button"
                  disabled={isSavingPrompts || !entryId}
                  onClick={onSavePrompts}
                  className="inline-flex h-9 items-center rounded-lg border px-3 text-sm font-medium"
                >
                  {isSavingPrompts ? copy.saving : copy.savePrompts}
                </button>
              ) : null}
            </div>
          }
          assistant={
            threadType && moduleType ? (
              <PromptAssistantPanel
                locale={locale}
                scope={promptScope}
                draftPrompts={prompts}
                defaultInstructionContent={form.default_instruction_content}
                onApplyPrompts={(next) => setPrompts(next)}
              />
            ) : null
          }
        />
      ) : null}
    </div>
  );
}

type SettingsFieldsProps = {
  form: EntryFormState;
  setForm: React.Dispatch<React.SetStateAction<EntryFormState>>;
  copy: Record<string, string>;
};

function SettingsFields({ form, setForm, copy }: SettingsFieldsProps) {
  return (
    <>
      <label className="block text-start text-sm">
        <span className="font-medium">{copy.displayName}</span>
        <input
          required
          value={form.display_name}
          onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))}
          className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <label className="block text-start text-sm">
        <span className="font-medium">{copy.description}</span>
        <textarea
          rows={2}
          value={form.description}
          onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
          className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-start text-sm">
          <span className="font-medium">{copy.defaultModel}</span>
          <input
            value={form.default_model_id}
            onChange={(event) =>
              setForm((current) => ({ ...current, default_model_id: event.target.value }))
            }
            className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-xs dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="block text-start text-sm">
          <span className="font-medium">{copy.fallbackModel}</span>
          <input
            value={form.fallback_model_id}
            onChange={(event) =>
              setForm((current) => ({ ...current, fallback_model_id: event.target.value }))
            }
            className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-xs dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-start text-sm">
          <span className="font-medium">{copy.tokenBudget}</span>
          <input
            inputMode="numeric"
            value={form.token_budget}
            onChange={(event) =>
              setForm((current) => ({ ...current, token_budget: event.target.value }))
            }
            className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
        <label className="block text-start text-sm">
          <span className="font-medium">{copy.budgetThreshold}</span>
          <input
            inputMode="decimal"
            value={form.token_budget_warning_threshold}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                token_budget_warning_threshold: event.target.value,
              }))
            }
            className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.supports_automation}
            onChange={(event) =>
              setForm((current) => ({ ...current, supports_automation: event.target.checked }))
            }
          />
          {copy.supportsAutomation}
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
          />
          {copy.isActive}
        </label>
      </div>
    </>
  );
}

export { parseTokenBudget };
