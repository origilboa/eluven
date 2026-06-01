"use client";

import { useState } from "react";

import type { TaskMemoryEntryResponse, TaskMemoryResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type TaskMemoryPanelProps = {
  locale: Locale;
  memory: TaskMemoryResponse;
};

type MemorySection = {
  key: keyof TaskMemoryResponse;
  label: Record<Locale, string>;
};

const SECTIONS: MemorySection[] = [
  { key: "findings", label: { en: "Findings", he: "ממצאים" } },
  { key: "assumptions", label: { en: "Assumptions", he: "הנחות" } },
  { key: "gaps", label: { en: "Gaps", he: "פערים" } },
  { key: "references", label: { en: "References", he: "מקורות" } },
];

function MemoryEntryCard({
  entry,
  locale,
}: {
  entry: TaskMemoryEntryResponse;
  locale: Locale;
}) {
  return (
    <article className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-start dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm leading-6 text-zinc-800 dark:text-zinc-200">{entry.content}</p>
      {entry.confidence !== null ? (
        <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">
          {locale === "he"
            ? `ביטחון: ${Math.round(entry.confidence * 100)}%`
            : `Confidence: ${Math.round(entry.confidence * 100)}%`}
        </p>
      ) : null}
    </article>
  );
}

export function TaskMemoryPanel({ locale, memory }: TaskMemoryPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  const totalEntries =
    memory.findings.length +
    memory.assumptions.length +
    memory.gaps.length +
    memory.references.length;

  const copy =
    locale === "he"
      ? {
          title: "זיכרון משימה",
          collapse: "כווץ פאנל",
          expand: "הרחב פאנל",
          empty: "אין רשומות זיכרון עדיין.",
        }
      : {
          title: "Task memory",
          collapse: "Collapse panel",
          expand: "Expand panel",
          empty: "No memory entries yet.",
        };

  return (
    <aside className="rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <div className="text-start">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{totalEntries}</p>
        </div>
        <button
          type="button"
          aria-label={collapsed ? copy.expand : copy.collapse}
          onClick={() => setCollapsed((value) => !value)}
          className="inline-flex size-8 items-center justify-center rounded-md border border-zinc-200 text-zinc-600 hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
        >
          {collapsed ? "+" : "−"}
        </button>
      </div>

      {!collapsed ? (
        <div className="max-h-[70vh] space-y-5 overflow-y-auto p-4">
          {totalEntries === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">{copy.empty}</p>
          ) : (
            SECTIONS.map((section) => {
              const entries = memory[section.key];
              if (!entries.length) {
                return null;
              }
              return (
                <section key={section.key} className="space-y-2">
                  <h3 className="text-start text-xs font-semibold uppercase tracking-wide text-zinc-500">
                    {section.label[locale]}
                  </h3>
                  <div className="space-y-2">
                    {entries.map((entry) => (
                      <MemoryEntryCard key={entry.id} entry={entry} locale={locale} />
                    ))}
                  </div>
                </section>
              );
            })
          )}
        </div>
      ) : null}
    </aside>
  );
}
