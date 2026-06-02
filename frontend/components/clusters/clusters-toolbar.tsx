"use client";

import { useState } from "react";

import { NewAssignmentModal } from "@/components/clusters/new-assignment-modal";
import type { Locale } from "@/i18n.config";

type ClustersToolbarProps = {
  locale: Locale;
};

export function ClustersToolbar({ locale }: ClustersToolbarProps) {
  const [open, setOpen] = useState(false);

  const copy =
    locale === "he"
      ? {
          title: "מטלות (Assignments)",
          subtitle: "נהל מטלות והגשות סטודנטים",
          newAssignment: "מטלה חדשה",
        }
      : {
          title: "Assignments",
          subtitle: "Manage SPR assignments and student submissions",
          newAssignment: "New Assignment",
        };

  return (
    <>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="text-start">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          {copy.newAssignment}
        </button>
      </div>
      <NewAssignmentModal locale={locale} open={open} onClose={() => setOpen(false)} />
    </>
  );
}
