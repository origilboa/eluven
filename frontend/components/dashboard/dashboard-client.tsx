"use client";

import { useState } from "react";

import { DashboardEmptyState } from "@/components/dashboard/dashboard-empty-state";
import { NewTaskModal } from "@/components/tasks/new-task-modal";
import {
  MODULE_TYPE_EXTERNAL_PAPER_REVIEW,
  MODULE_TYPE_STUDENT_PAPER_REVIEW,
} from "@/lib/modules";
import type { Locale } from "@/i18n.config";

type DashboardEmptyWrapperProps = {
  locale: Locale;
};

export function DashboardEmptyWrapper({ locale }: DashboardEmptyWrapperProps) {
  const [open, setOpen] = useState(false);
  const [moduleType, setModuleType] = useState<
    typeof MODULE_TYPE_EXTERNAL_PAPER_REVIEW | typeof MODULE_TYPE_STUDENT_PAPER_REVIEW
  >(MODULE_TYPE_EXTERNAL_PAPER_REVIEW);

  function openSample(type: typeof moduleType) {
    setModuleType(type);
    setOpen(true);
  }

  return (
    <>
      <DashboardEmptyState
        locale={locale}
        onSampleEpr={() => openSample(MODULE_TYPE_EXTERNAL_PAPER_REVIEW)}
        onSampleSpr={() => openSample(MODULE_TYPE_STUDENT_PAPER_REVIEW)}
      />
      <NewTaskModal
        locale={locale}
        open={open}
        onClose={() => setOpen(false)}
        initialValues={{
          module_type: moduleType,
          title:
            moduleType === MODULE_TYPE_EXTERNAL_PAPER_REVIEW
              ? locale === "he"
                ? "סקירת מאמר לדוגמה"
                : "Sample paper review"
              : locale === "he"
                ? "הגשת סטודנט לדוגמה"
                : "Sample student submission",
        }}
      />
    </>
  );
}
