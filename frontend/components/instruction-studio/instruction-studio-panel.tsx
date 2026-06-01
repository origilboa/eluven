"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "@/lib/api";
import type {
  ActivateInstructionVersionRequest,
  CreateInstructionVersionRequest,
  InstructionLevel,
  InstructionSetResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type InstructionStudioPanelProps = {
  locale: Locale;
  userRole: string;
};

type TabConfig = {
  level: InstructionLevel;
  label: string;
  visible: boolean;
  canEdit: boolean;
};

function formatTimestamp(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale === "he" ? "he-IL" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function InstructionStudioPanel({ locale, userRole }: InstructionStudioPanelProps) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<InstructionLevel>("user");
  const [editing, setEditing] = useState(false);
  const [draftContent, setDraftContent] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "Instruction Studio",
          subtitle: "ניהול הוראות לפי רמות ההיררכיה",
          platform: "פלטפורמה",
          org: "ארגון",
          user: "משתמש",
          activeVersion: "גרסה פעילה",
          noActive: "אין גרסה פעילה עדיין.",
          edit: "ערוך",
          cancel: "ביטול",
          save: "שמור גרסה",
          saving: "שומר…",
          changeNote: "הערת שינוי (אופציונלי)",
          content: "תוכן ההוראות",
          history: "היסטוריית גרסאות",
          noVersions: "אין גרסאות עדיין.",
          setActive: "הגדר כפעיל",
          activating: "מגדיר…",
          activeBadge: "פעיל",
          version: "גרסה",
          readOnly: "תצוגה בלבד — אין לך הרשאת עריכה ברמה זו.",
        }
      : {
          title: "Instruction Studio",
          subtitle: "Manage instructions across hierarchy levels",
          platform: "Platform",
          org: "Organization",
          user: "User",
          activeVersion: "Active version",
          noActive: "No active version yet.",
          edit: "Edit",
          cancel: "Cancel",
          save: "Save version",
          saving: "Saving…",
          changeNote: "Change note (optional)",
          content: "Instruction content",
          history: "Version history",
          noVersions: "No versions yet.",
          setActive: "Set as Active",
          activating: "Activating…",
          activeBadge: "Active",
          version: "Version",
          readOnly: "Read-only — you do not have edit access at this level.",
        };

  const tabs = useMemo<TabConfig[]>(
    () => [
      {
        level: "platform",
        label: copy.platform,
        visible: true,
        canEdit: userRole === "app_admin",
      },
      {
        level: "org",
        label: copy.org,
        visible: userRole === "org_admin" || userRole === "app_admin",
        canEdit: userRole === "org_admin" || userRole === "app_admin",
      },
      {
        level: "user",
        label: copy.user,
        visible: true,
        canEdit: true,
      },
    ],
    [copy.org, copy.platform, copy.user, userRole],
  );

  const visibleTabs = tabs.filter((tab) => tab.visible);
  const currentTab = visibleTabs.find((tab) => tab.level === activeTab) ?? visibleTabs[0];
  const currentLevel = currentTab?.level ?? "user";
  const canEdit = currentTab?.canEdit ?? false;

  const { data, isLoading } = useQuery({
    queryKey: ["instructions", currentLevel],
    queryFn: () => api.get<InstructionSetResponse>(`/instructions/${currentLevel}`),
    enabled: Boolean(currentLevel),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateInstructionVersionRequest) =>
      api.post<InstructionSetResponse>(`/instructions/${currentLevel}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instructions", currentLevel] });
      setEditing(false);
      setDraftContent("");
      setChangeNote("");
      setError(null);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const activateMutation = useMutation({
    mutationFn: (payload: ActivateInstructionVersionRequest) =>
      api.post<InstructionSetResponse>(`/instructions/${currentLevel}/activate`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["instructions", currentLevel] });
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  function startEditing() {
    setDraftContent(data?.active_version?.content ?? "");
    setChangeNote("");
    setEditing(true);
    setError(null);
  }

  function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draftContent.trim()) {
      return;
    }
    createMutation.mutate({
      content: draftContent.trim(),
      change_note: changeNote.trim() ? changeNote.trim() : null,
    });
  }

  const activeContent = data?.active_version?.content ?? null;

  return (
    <div className="space-y-6">
      <div className="text-start">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
        {visibleTabs.map((tab) => (
          <button
            key={tab.level}
            type="button"
            onClick={() => {
              setActiveTab(tab.level);
              setEditing(false);
              setError(null);
            }}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              currentLevel === tab.level
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">
          {locale === "he" ? "טוען…" : "Loading…"}
        </p>
      ) : (
        <div className="space-y-8">
          <section className="space-y-4 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                {copy.activeVersion}
              </h2>
              {canEdit && !editing ? (
                <button
                  type="button"
                  onClick={startEditing}
                  className="inline-flex h-9 items-center justify-center rounded-lg border border-zinc-300 px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
                >
                  {copy.edit}
                </button>
              ) : null}
            </div>

            {!canEdit ? (
              <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.readOnly}</p>
            ) : null}

            {editing ? (
              <form className="space-y-4" onSubmit={handleSave}>
                <div className="space-y-2 text-start">
                  <label htmlFor="instruction-content" className="block text-sm font-medium">
                    {copy.content}
                  </label>
                  <textarea
                    id="instruction-content"
                    required
                    rows={12}
                    value={draftContent}
                    onChange={(event) => setDraftContent(event.target.value)}
                    className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 font-mono text-sm text-zinc-900 outline-none focus:border-zinc-500 focus:ring-2 focus:ring-zinc-900/10 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                  />
                </div>
                <div className="space-y-2 text-start">
                  <label htmlFor="instruction-change-note" className="block text-sm font-medium">
                    {copy.changeNote}
                  </label>
                  <input
                    id="instruction-change-note"
                    value={changeNote}
                    onChange={(event) => setChangeNote(event.target.value)}
                    className="block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                  />
                </div>
                {error ? (
                  <p className="text-start text-sm text-red-600 dark:text-red-400">{error}</p>
                ) : null}
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setEditing(false)}
                    className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium"
                  >
                    {copy.cancel}
                  </button>
                  <button
                    type="submit"
                    disabled={createMutation.isPending}
                    className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                  >
                    {createMutation.isPending ? copy.saving : copy.save}
                  </button>
                </div>
              </form>
            ) : (
              <div className="rounded-lg bg-zinc-50 p-4 text-start dark:bg-zinc-900">
                {activeContent ? (
                  <pre className="whitespace-pre-wrap font-mono text-sm text-zinc-800 dark:text-zinc-200">
                    {activeContent}
                  </pre>
                ) : (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">{copy.noActive}</p>
                )}
              </div>
            )}
          </section>

          <section className="space-y-4">
            <h2 className="text-start text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {copy.history}
            </h2>

            {!data?.versions.length ? (
              <p className="text-start text-sm text-zinc-500 dark:text-zinc-400">{copy.noVersions}</p>
            ) : (
              <ul className="space-y-3">
                {data.versions.map((version) => (
                  <li
                    key={version.id}
                    className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="text-start">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                            {copy.version} {version.version_number}
                          </p>
                          {version.is_active ? (
                            <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300">
                              {copy.activeBadge}
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                          {formatTimestamp(version.created_at, locale)}
                        </p>
                        {version.change_note ? (
                          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
                            {version.change_note}
                          </p>
                        ) : null}
                      </div>

                      {canEdit && !version.is_active ? (
                        <button
                          type="button"
                          disabled={activateMutation.isPending}
                          onClick={() => activateMutation.mutate({ version_id: version.id })}
                          className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg border border-zinc-300 px-3 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-900"
                        >
                          {activateMutation.isPending ? copy.activating : copy.setActive}
                        </button>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
