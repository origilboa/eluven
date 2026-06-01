"use client";

import { useState } from "react";

import { NewTaskModal } from "@/components/tasks/new-task-modal";
import {
  MODULE_TYPE_EXTERNAL_PAPER_REVIEW,
  MODULE_TYPE_STUDENT_PAPER_REVIEW,
  type ModuleType,
} from "@/lib/modules";
import type { Locale } from "@/i18n.config";

type DashboardToolbarProps = {
  locale: Locale;
};

export function DashboardToolbar({ locale }: DashboardToolbarProps) {
  const [open, setOpen] = useState(false);
  const [initialModuleType, setInitialModuleType] = useState<ModuleType | undefined>(
    undefined,
  );

  const copy =
    locale === "he"
      ? {
          title: "לוח בקרה",
          subtitle: "משימות מאורגנות לפי סוג מודול",
          newTask: "משימה חדשה",
          newEpr: "סקירת מאמר חיצונית",
          newSpr: "סקירת עבודות סטודנטים",
        }
      : {
          title: "Dashboard",
          subtitle: "Your tasks grouped by module type",
          newTask: "New Task",
          newEpr: "External Paper Review",
          newSpr: "Student Paper Review",
        };

  function openModal(moduleType?: ModuleType) {
    setInitialModuleType(moduleType);
    setOpen(true);
  }

  return (
    <>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="text-start">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
            {copy.title}
          </h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={() => openModal(MODULE_TYPE_EXTERNAL_PAPER_REVIEW)}
            className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-white dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-950"
          >
            {copy.newEpr}
          </button>
          <button
            type="button"
            onClick={() => openModal(MODULE_TYPE_STUDENT_PAPER_REVIEW)}
            className="inline-flex h-10 items-center justify-center rounded-lg border border-zinc-300 px-4 text-sm font-medium text-zinc-700 transition-colors hover:bg-white dark:border-zinc-700 dark:text-zinc-200 dark:hover:bg-zinc-950"
          >
            {copy.newSpr}
          </button>
          <button
            type="button"
            data-testid="new-task-button"
            onClick={() => openModal()}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
          >
            {copy.newTask}
          </button>
        </div>
      </div>

      <NewTaskModal
        locale={locale}
        open={open}
        onClose={() => setOpen(false)}
        initialValues={
          initialModuleType
            ? {
                module_type: initialModuleType,
                title:
                  initialModuleType === MODULE_TYPE_EXTERNAL_PAPER_REVIEW
                    ? locale === "he"
                      ? "סקירת מאמר לדוגמה"
                      : "Sample paper review"
                    : locale === "he"
                      ? "הגשת סטודנט לדוגמה"
                      : "Sample student submission",
              }
            : undefined
        }
      />
    </>
  );
}
