import type { Locale } from "@/i18n.config";
import type { TaskResponse } from "@/lib/types/api";

export const MODULE_TYPE_EXTERNAL_PAPER_REVIEW = "external_paper_review";
export const MODULE_TYPE_STUDENT_PAPER_REVIEW = "student_paper_review";

export type ModuleType =
  | typeof MODULE_TYPE_EXTERNAL_PAPER_REVIEW
  | typeof MODULE_TYPE_STUDENT_PAPER_REVIEW;

export type ModuleDefinition = {
  value: ModuleType;
  label: Record<Locale, string>;
  description: Record<Locale, string>;
};

export const MODULE_DEFINITIONS: ModuleDefinition[] = [
  {
    value: MODULE_TYPE_EXTERNAL_PAPER_REVIEW,
    label: {
      en: "External Paper Review",
      he: "סקירת מאמר חיצונית",
    },
    description: {
      en: "Review manuscripts for publishers and journals.",
      he: "סקירת כתבי יד עבור מוציאים לאור וכתבי עת.",
    },
  },
  {
    value: MODULE_TYPE_STUDENT_PAPER_REVIEW,
    label: {
      en: "Student Paper Review",
      he: "סקירת עבודות סטודנטים",
    },
    description: {
      en: "Evaluate student submissions against rubrics and briefs.",
      he: "הערכת הגשות סטודנטים מול רubric ותדריך המטלה.",
    },
  },
];

export function getModuleLabel(moduleType: string, locale: Locale): string {
  const definition = MODULE_DEFINITIONS.find((item) => item.value === moduleType);
  return definition?.label[locale] ?? moduleType;
}

export function groupTasksByModule(tasks: TaskResponse[]): Map<string, TaskResponse[]> {
  const grouped = new Map<string, TaskResponse[]>();

  for (const task of tasks) {
    const existing = grouped.get(task.module_type) ?? [];
    existing.push(task);
    grouped.set(task.module_type, existing);
  }

  for (const [key, value] of grouped) {
    grouped.set(
      key,
      [...value].sort(
        (left, right) =>
          new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
      ),
    );
  }

  return grouped;
}

export function formatOrgLabel(orgId: string, locale: Locale): string {
  const shortId = orgId.slice(0, 8);
  return locale === "he" ? `ארגון · ${shortId}` : `Org · ${shortId}`;
}
