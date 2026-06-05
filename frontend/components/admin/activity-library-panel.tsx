"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ActivityEntryDetailTabs,
  type EntryFormState,
  type PromptDraft,
  parseTokenBudget,
} from "@/components/activity-studio/activity-entry-detail-tabs";
import { api } from "@/lib/api";
import { isAppAdmin } from "@/lib/admin-access";
import { MODULE_DEFINITIONS, MODULE_TYPE_EXTERNAL_PAPER_REVIEW } from "@/lib/modules";
import type {
  AdminActivityLibraryDetailResponse,
  AdminActivityLibraryEntryResponse,
  CreateActivityLibraryEntryRequest,
  ReplaceActivityPromptsRequest,
  UpdateActivityLibraryEntryRequest,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ActivityLibraryPanelProps = {
  locale: Locale;
  userRole: string;
};

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

function formFromDetail(detail: AdminActivityLibraryDetailResponse): EntryFormState {
  return {
    display_name: detail.display_name,
    description: detail.description ?? "",
    default_instruction_content: detail.default_instruction_content ?? "",
    default_model_id: detail.default_model_id,
    fallback_model_id: detail.fallback_model_id ?? "",
    token_budget: detail.token_budget !== null ? String(detail.token_budget) : "",
    token_budget_warning_threshold: String(detail.token_budget_warning_threshold),
    supports_automation: detail.supports_automation,
    is_active: detail.is_active,
  };
}

function promptsFromDetail(detail: AdminActivityLibraryDetailResponse): PromptDraft[] {
  return detail.prompts.map((prompt) => ({
    prompt_text: prompt.prompt_text,
  }));
}

function buildPromptsPayload(prompts: PromptDraft[]): ReplaceActivityPromptsRequest {
  return {
    prompts: prompts
      .filter((prompt) => prompt.prompt_text.trim())
      .map((prompt) => ({
        prompt_text: prompt.prompt_text.trim(),
      })),
  };
}

export function ActivityLibraryPanel({ locale, userRole }: ActivityLibraryPanelProps) {
  const queryClient = useQueryClient();
  const [moduleFilter, setModuleFilter] = useState<string>(MODULE_TYPE_EXTERNAL_PAPER_REVIEW);
  const [includeInactive, setIncludeInactive] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createThreadType, setCreateThreadType] = useState("");
  const [form, setForm] = useState<EntryFormState>(EMPTY_FORM);
  const [prompts, setPrompts] = useState<PromptDraft[]>([]);
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "ספריית פעילויות",
          subtitle: "ניהול סוגי שרשור, הוראות ברירת מחדל והצעות פעילות",
          module: "מודול",
          allModules: "כל המודולים",
          includeInactive: "הצג לא פעילים",
          guidedSetup: "הגדרה מודרכת",
          quickCreate: "יצירה מהירה",
          newType: "סוג חדש",
          selectHint: "בחר סוג פעילות לעריכה",
          threadType: "מזהה סוג (slug)",
          displayName: "שם תצוגה",
          description: "תיאור",
          defaultInstructions: "הוראות ברירת מחדל",
          defaultModel: "מודל ברירת מחדל",
          fallbackModel: "מודל גיבוי",
          tokenBudget: "תקציב טוקנים",
          budgetThreshold: "סף אזהרת תקציב (0–1)",
          supportsAutomation: "תומך באוטומציה",
          isActive: "פעיל",
          activityPrompts: "הצעות פעילות",
          addPrompt: "הוסף הצעה",
          prompt: "הצעה",
          remove: "הסר",
          saveEntry: "שמור הגדרות",
          savePrompts: "שמור הצעות",
          saving: "שומר…",
          create: "צור סוג",
          creating: "יוצר…",
          cancel: "ביטול",
          active: "פעיל",
          inactive: "לא פעיל",
          prompts: "הצעות",
          empty: "אין סוגי פעילות.",
          loading: "טוען…",
        }
      : {
          title: "Activity library",
          subtitle: "Manage thread types, default instructions, and activity prompts",
          module: "Module",
          allModules: "All modules",
          includeInactive: "Show inactive",
          guidedSetup: "Guided setup",
          quickCreate: "Quick create",
          newType: "New type",
          selectHint: "Select an activity type to edit",
          threadType: "Type slug",
          displayName: "Display name",
          description: "Description",
          defaultInstructions: "Default instructions",
          defaultModel: "Default model",
          fallbackModel: "Fallback model",
          tokenBudget: "Token budget",
          budgetThreshold: "Budget warning threshold (0–1)",
          supportsAutomation: "Supports automation",
          isActive: "Active",
          activityPrompts: "Activity prompts",
          addPrompt: "Add prompt",
          prompt: "Prompt",
          remove: "Remove",
          saveEntry: "Save settings",
          savePrompts: "Save prompts",
          saving: "Saving…",
          create: "Create type",
          creating: "Creating…",
          cancel: "Cancel",
          active: "Active",
          inactive: "Inactive",
          prompts: "prompts",
          empty: "No activity types.",
          loading: "Loading…",
        };

  const listQuery = useQuery({
    queryKey: ["admin-activity-library", moduleFilter, includeInactive],
    queryFn: () => {
      const params = new URLSearchParams();
      if (moduleFilter) {
        params.set("module_type", moduleFilter);
      }
      if (includeInactive) {
        params.set("include_inactive", "true");
      }
      const query = params.toString();
      return api.get<AdminActivityLibraryEntryResponse[]>(
        `/admin/activity-library${query ? `?${query}` : ""}`,
      );
    },
    enabled: isAppAdmin(userRole),
  });

  const detailQuery = useQuery({
    queryKey: ["admin-activity-library", selectedId],
    queryFn: () =>
      api.get<AdminActivityLibraryDetailResponse>(`/admin/activity-library/${selectedId}`),
    enabled: isAppAdmin(userRole) && Boolean(selectedId) && !isCreating,
  });

  const entries = listQuery.data ?? [];

  const selectedSummary = useMemo(
    () => entries.find((entry) => entry.id === selectedId) ?? null,
    [entries, selectedId],
  );

  function selectEntry(entry: AdminActivityLibraryEntryResponse) {
    setIsCreating(false);
    setSelectedId(entry.id);
    setForm(EMPTY_FORM);
    setPrompts([]);
    setError(null);
  }

  function startCreate() {
    setIsCreating(true);
    setSelectedId(null);
    setCreateThreadType("");
    setForm(EMPTY_FORM);
    setPrompts([]);
    setError(null);
  }

  function loadDetailIntoForm(detail: AdminActivityLibraryDetailResponse) {
    setForm(formFromDetail(detail));
    setPrompts(promptsFromDetail(detail));
  }

  useEffect(() => {
    if (!isCreating && detailQuery.data && selectedId === detailQuery.data.id) {
      loadDetailIntoForm(detailQuery.data);
    }
  }, [detailQuery.data, isCreating, selectedId]);

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-activity-library"] });
  };

  const updateMutation = useMutation({
    mutationFn: ({
      entryId,
      body,
    }: {
      entryId: string;
      body: UpdateActivityLibraryEntryRequest;
    }) => api.patch<AdminActivityLibraryDetailResponse>(`/admin/activity-library/${entryId}`, body),
    onSuccess: async (detail) => {
      await invalidate();
      loadDetailIntoForm(detail);
      setError(null);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const promptsMutation = useMutation({
    mutationFn: ({
      entryId,
      body,
    }: {
      entryId: string;
      body: ReplaceActivityPromptsRequest;
    }) =>
      api.put<AdminActivityLibraryDetailResponse>(
        `/admin/activity-library/${entryId}/prompts`,
        body,
      ),
    onSuccess: async (detail) => {
      await invalidate();
      loadDetailIntoForm(detail);
      setError(null);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateActivityLibraryEntryRequest) =>
      api.post<AdminActivityLibraryDetailResponse>("/admin/activity-library", body),
    onSuccess: async (detail) => {
      await invalidate();
      setIsCreating(false);
      setSelectedId(detail.id);
      loadDetailIntoForm(detail);
      setError(null);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  function buildUpdateBody(integrityApprovalToken?: string | null): UpdateActivityLibraryEntryRequest {
    const instructionContent = form.default_instruction_content.trim()
      ? form.default_instruction_content.trim()
      : null;
    return {
      display_name: form.display_name.trim(),
      description: form.description.trim() ? form.description.trim() : null,
      default_instruction_content: instructionContent,
      integrity_approval_token: instructionContent ? integrityApprovalToken ?? undefined : undefined,
      default_model_id: form.default_model_id.trim() || undefined,
      fallback_model_id: form.fallback_model_id.trim() ? form.fallback_model_id.trim() : null,
      token_budget: parseTokenBudget(form.token_budget),
      token_budget_warning_threshold: Number.parseFloat(form.token_budget_warning_threshold),
      supports_automation: form.supports_automation,
      is_active: form.is_active,
    };
  }

  function buildCreateBody(
    integrityApprovalToken?: string | null,
  ): CreateActivityLibraryEntryRequest | null {
    const moduleType = moduleFilter.trim();
    if (!createThreadType.trim() || !form.display_name.trim() || !moduleType) {
      setError(
        locale === "he"
          ? "בחר מודול לפני יצירת סוג פעילות."
          : "Select a module before creating an activity type.",
      );
      return null;
    }
    const instructionContent = form.default_instruction_content.trim()
      ? form.default_instruction_content.trim()
      : null;
    return {
      thread_type: createThreadType.trim(),
      module_type: moduleType,
      display_name: form.display_name.trim(),
      description: form.description.trim() ? form.description.trim() : null,
      default_instruction_content: instructionContent,
      integrity_approval_token: instructionContent ? integrityApprovalToken ?? undefined : undefined,
      default_model_id: form.default_model_id.trim() || null,
      fallback_model_id: form.fallback_model_id.trim() ? form.fallback_model_id.trim() : null,
      token_budget: parseTokenBudget(form.token_budget),
      token_budget_warning_threshold: Number.parseFloat(form.token_budget_warning_threshold),
      supports_automation: form.supports_automation,
      is_active: form.is_active,
    };
  }

  async function handleQuickCreate(options?: { integrityApprovalToken?: string | null }) {
    try {
      const body = buildCreateBody(options?.integrityApprovalToken);
      if (!body) {
        return;
      }
      const detail = await createMutation.mutateAsync(body);
      const promptPayload = buildPromptsPayload(prompts);
      if (promptPayload.prompts.length > 0) {
        await promptsMutation.mutateAsync({ entryId: detail.id, body: promptPayload });
      }
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : "Create failed");
    }
  }

  if (!isAppAdmin(userRole)) {
    return null;
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-start">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{copy.subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/${locale}/admin/activity-library/create`}
            className="inline-flex h-9 items-center rounded-lg border border-zinc-300 px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
          >
            {copy.guidedSetup}
          </Link>
          <button
            type="button"
            onClick={startCreate}
            className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            {copy.quickCreate}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <label className="text-start text-sm">
          <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
            {copy.module}
          </span>
          <select
            value={moduleFilter}
            onChange={(event) => {
              setModuleFilter(event.target.value);
              setSelectedId(null);
              setIsCreating(false);
              setForm(EMPTY_FORM);
            }}
            className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
          >
            <option value="">{copy.allModules}</option>
            {MODULE_DEFINITIONS.map((module) => (
              <option key={module.value} value={module.value}>
                {module.label[locale]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(event) => setIncludeInactive(event.target.checked)}
          />
          {copy.includeInactive}
        </label>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
        <div className="rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
          {listQuery.isLoading ? (
            <p className="p-4 text-sm text-zinc-500">{copy.loading}</p>
          ) : entries.length === 0 ? (
            <p className="p-4 text-sm text-zinc-500">{copy.empty}</p>
          ) : (
            <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {entries.map((entry) => (
                <li key={entry.id}>
                  <button
                    type="button"
                    onClick={() => selectEntry(entry)}
                    className={`w-full px-4 py-3 text-start transition-colors ${
                      selectedId === entry.id && !isCreating
                        ? "bg-zinc-100 dark:bg-zinc-900"
                        : "hover:bg-zinc-50 dark:hover:bg-zinc-900/50"
                    }`}
                  >
                    <p className="font-medium text-zinc-900 dark:text-zinc-50">{entry.display_name}</p>
                    <p className="mt-0.5 font-mono text-xs text-zinc-500">{entry.thread_type}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {entry.is_active ? copy.active : copy.inactive} · {entry.prompt_count}{" "}
                      {copy.prompts}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          {isCreating ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-start text-sm font-semibold">{copy.quickCreate}</h3>
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="text-sm text-zinc-500 underline-offset-4 hover:underline"
                >
                  {copy.cancel}
                </button>
              </div>
              <ActivityEntryDetailTabs
                locale={locale}
                mode="create"
                moduleType={moduleFilter}
                threadType={createThreadType}
                onThreadTypeChange={setCreateThreadType}
                form={form}
                setForm={setForm}
                prompts={prompts}
                setPrompts={setPrompts}
                onSaveSettings={() => undefined}
                onSavePrompts={() => undefined}
                onCreate={(options) => void handleQuickCreate(options)}
                isSavingSettings={false}
                isSavingPrompts={false}
                isCreating={createMutation.isPending || promptsMutation.isPending}
                copy={copy}
              />
            </div>
          ) : selectedId && detailQuery.isLoading ? (
            <p className="text-sm text-zinc-500">{copy.loading}</p>
          ) : selectedId && detailQuery.data ? (
            <div className="space-y-4">
              <div className="text-start">
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                  {selectedSummary?.display_name ?? detailQuery.data.display_name}
                </h3>
                <p className="mt-1 font-mono text-xs text-zinc-500">{detailQuery.data.thread_type}</p>
              </div>
              <ActivityEntryDetailTabs
                locale={locale}
                mode="edit"
                moduleType={detailQuery.data.module_type}
                threadType={detailQuery.data.thread_type}
                entryId={selectedId}
                form={form}
                setForm={setForm}
                prompts={prompts}
                setPrompts={setPrompts}
                onSaveSettings={(options) =>
                  updateMutation.mutate({
                    entryId: selectedId,
                    body: buildUpdateBody(options?.integrityApprovalToken),
                  })
                }
                onSavePrompts={() =>
                  promptsMutation.mutate({
                    entryId: selectedId,
                    body: buildPromptsPayload(prompts),
                  })
                }
                isSavingSettings={updateMutation.isPending}
                isSavingPrompts={promptsMutation.isPending}
                copy={copy}
              />
            </div>
          ) : (
            <p className="text-sm text-zinc-500">{copy.selectHint}</p>
          )}

          {error ? (
            <p className="mt-4 text-start text-sm text-red-600 dark:text-red-400">{error}</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
