"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { isAppAdmin } from "@/lib/admin-access";
import { MODULE_DEFINITIONS, MODULE_TYPE_EXTERNAL_PAPER_REVIEW } from "@/lib/modules";
import type {
  AdminActivityLibraryDetailResponse,
  AdminActivityLibraryEntryResponse,
  CreateActivityLibraryEntryRequest,
  ReplaceOpeningQuestionsRequest,
  UpdateActivityLibraryEntryRequest,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type ActivityLibraryPanelProps = {
  locale: Locale;
  userRole: string;
};

type OpeningQuestionDraft = {
  question_text: string;
  is_required: boolean;
};

type EntryFormState = {
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

function questionsFromDetail(detail: AdminActivityLibraryDetailResponse): OpeningQuestionDraft[] {
  return detail.opening_questions.map((question) => ({
    question_text: question.question_text,
    is_required: question.is_required,
  }));
}

function parseTokenBudget(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function ActivityLibraryPanel({ locale, userRole }: ActivityLibraryPanelProps) {
  const queryClient = useQueryClient();
  const [moduleFilter, setModuleFilter] = useState<string>(MODULE_TYPE_EXTERNAL_PAPER_REVIEW);
  const [includeInactive, setIncludeInactive] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createThreadType, setCreateThreadType] = useState("");
  const [form, setForm] = useState<EntryFormState>(EMPTY_FORM);
  const [questions, setQuestions] = useState<OpeningQuestionDraft[]>([]);
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "ספריית פעילויות",
          subtitle: "ניהול סוגי שרשור, הוראות ברירת מחדל ושאלות פתיחה",
          module: "מודול",
          allModules: "כל המודולים",
          includeInactive: "הצג לא פעילים",
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
          openingQuestions: "שאלות פתיחה",
          addQuestion: "הוסף שאלה",
          question: "שאלה",
          required: "חובה",
          saveEntry: "שמור הגדרות",
          saveQuestions: "שמור שאלות",
          saving: "שומר…",
          create: "צור סוג",
          creating: "יוצר…",
          cancel: "ביטול",
          active: "פעיל",
          inactive: "לא פעיל",
          questions: "שאלות",
          empty: "אין סוגי פעילות.",
          loading: "טוען…",
        }
      : {
          title: "Activity library",
          subtitle: "Manage thread types, default instructions, and opening Q&A",
          module: "Module",
          allModules: "All modules",
          includeInactive: "Show inactive",
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
          openingQuestions: "Opening questions",
          addQuestion: "Add question",
          question: "Question",
          required: "Required",
          saveEntry: "Save settings",
          saveQuestions: "Save questions",
          saving: "Saving…",
          create: "Create type",
          creating: "Creating…",
          cancel: "Cancel",
          active: "Active",
          inactive: "Inactive",
          questions: "questions",
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
    setQuestions([]);
    setError(null);
  }

  function startCreate() {
    setIsCreating(true);
    setSelectedId(null);
    setCreateThreadType("");
    setForm(EMPTY_FORM);
    setQuestions([]);
    setError(null);
  }

  function loadDetailIntoForm(detail: AdminActivityLibraryDetailResponse) {
    setForm(formFromDetail(detail));
    setQuestions(questionsFromDetail(detail));
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

  const questionsMutation = useMutation({
    mutationFn: ({
      entryId,
      body,
    }: {
      entryId: string;
      body: ReplaceOpeningQuestionsRequest;
    }) =>
      api.put<AdminActivityLibraryDetailResponse>(
        `/admin/activity-library/${entryId}/opening-questions`,
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

  function buildUpdateBody(): UpdateActivityLibraryEntryRequest {
    return {
      display_name: form.display_name.trim(),
      description: form.description.trim() ? form.description.trim() : null,
      default_instruction_content: form.default_instruction_content.trim()
        ? form.default_instruction_content.trim()
        : null,
      default_model_id: form.default_model_id.trim() || undefined,
      fallback_model_id: form.fallback_model_id.trim() ? form.fallback_model_id.trim() : null,
      token_budget: parseTokenBudget(form.token_budget),
      token_budget_warning_threshold: Number.parseFloat(form.token_budget_warning_threshold),
      supports_automation: form.supports_automation,
      is_active: form.is_active,
    };
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
        <button
          type="button"
          onClick={startCreate}
          className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          {copy.newType}
        </button>
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
                      {entry.is_active ? copy.active : copy.inactive} · {entry.opening_question_count}{" "}
                      {copy.questions}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
          {isCreating ? (
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                const moduleType = moduleFilter.trim();
                if (!createThreadType.trim() || !form.display_name.trim() || !moduleType) {
                  setError(
                    locale === "he"
                      ? "בחר מודול לפני יצירת סוג פעילות."
                      : "Select a module before creating an activity type.",
                  );
                  return;
                }
                createMutation.mutate({
                  thread_type: createThreadType.trim(),
                  module_type: moduleType,
                  display_name: form.display_name.trim(),
                  description: form.description.trim() ? form.description.trim() : null,
                  default_instruction_content: form.default_instruction_content.trim()
                    ? form.default_instruction_content.trim()
                    : null,
                  default_model_id: form.default_model_id.trim() || null,
                  fallback_model_id: form.fallback_model_id.trim()
                    ? form.fallback_model_id.trim()
                    : null,
                  token_budget: parseTokenBudget(form.token_budget),
                  token_budget_warning_threshold: Number.parseFloat(
                    form.token_budget_warning_threshold,
                  ),
                  supports_automation: form.supports_automation,
                  is_active: form.is_active,
                });
              }}
            >
              <h3 className="text-start text-sm font-semibold">{copy.newType}</h3>
              <label className="block text-start text-sm">
                <span className="font-medium">{copy.threadType}</span>
                <input
                  required
                  value={createThreadType}
                  onChange={(event) => setCreateThreadType(event.target.value)}
                  pattern="[a-z][a-z0-9_]*"
                  className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 font-mono text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>
              <EntryFields form={form} setForm={setForm} copy={copy} />
              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {createMutation.isPending ? copy.creating : copy.create}
                </button>
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="inline-flex h-9 items-center rounded-lg border px-3 text-sm"
                >
                  {copy.cancel}
                </button>
              </div>
            </form>
          ) : selectedId && detailQuery.isLoading ? (
            <p className="text-sm text-zinc-500">{copy.loading}</p>
          ) : selectedId && detailQuery.data ? (
            <div className="space-y-6">
              <div className="text-start">
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                  {selectedSummary?.display_name ?? detailQuery.data.display_name}
                </h3>
                <p className="mt-1 font-mono text-xs text-zinc-500">{detailQuery.data.thread_type}</p>
              </div>

              <form
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  updateMutation.mutate({ entryId: selectedId, body: buildUpdateBody() });
                }}
              >
                <EntryFields form={form} setForm={setForm} copy={copy} />
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="inline-flex h-9 items-center rounded-lg bg-zinc-900 px-3 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {updateMutation.isPending ? copy.saving : copy.saveEntry}
                </button>
              </form>

              <section className="space-y-3 border-t border-zinc-200 pt-4 dark:border-zinc-800">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-start text-sm font-semibold">{copy.openingQuestions}</h4>
                  <button
                    type="button"
                    onClick={() =>
                      setQuestions((current) => [
                        ...current,
                        { question_text: "", is_required: true },
                      ])
                    }
                    className="text-sm font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
                  >
                    {copy.addQuestion}
                  </button>
                </div>
                {questions.map((question, index) => (
                  <div
                    key={`q-${index}`}
                    className="space-y-2 rounded-lg border border-zinc-200 p-3 dark:border-zinc-800"
                  >
                    <label className="block text-start text-sm">
                      <span className="font-medium">{copy.question}</span>
                      <textarea
                        required
                        rows={2}
                        value={question.question_text}
                        onChange={(event) =>
                          setQuestions((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, question_text: event.target.value }
                                : item,
                            ),
                          )
                        }
                        className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                      />
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={question.is_required}
                        onChange={(event) =>
                          setQuestions((current) =>
                            current.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, is_required: event.target.checked }
                                : item,
                            ),
                          )
                        }
                      />
                      {copy.required}
                    </label>
                  </div>
                ))}
                <button
                  type="button"
                  disabled={questionsMutation.isPending}
                  onClick={() =>
                    questionsMutation.mutate({
                      entryId: selectedId,
                      body: {
                        questions: questions
                          .filter((question) => question.question_text.trim())
                          .map((question, index) => ({
                            question_text: question.question_text.trim(),
                            is_required: question.is_required,
                            sequence_index: index,
                          })),
                      },
                    })
                  }
                  className="inline-flex h-9 items-center rounded-lg border px-3 text-sm font-medium"
                >
                  {questionsMutation.isPending ? copy.saving : copy.saveQuestions}
                </button>
              </section>
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

type EntryFieldsProps = {
  form: EntryFormState;
  setForm: React.Dispatch<React.SetStateAction<EntryFormState>>;
  copy: Record<string, string>;
};

function EntryFields({ form, setForm, copy }: EntryFieldsProps) {
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
      <label className="block text-start text-sm">
        <span className="font-medium">{copy.defaultInstructions}</span>
        <textarea
          rows={8}
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
            onChange={(event) =>
              setForm((current) => ({ ...current, is_active: event.target.checked }))
            }
          />
          {copy.isActive}
        </label>
      </div>
    </>
  );
}
