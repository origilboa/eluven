"use client";

import { useState } from "react";

import { NewSubmissionModal } from "@/components/clusters/new-submission-modal";
import type { Locale } from "@/i18n.config";

type ClusterDetailToolbarProps = {
  locale: Locale;
  clusterId: string;
};

export function ClusterDetailToolbar({ locale, clusterId }: ClusterDetailToolbarProps) {
  const [open, setOpen] = useState(false);
  const label = locale === "he" ? "הגשה חדשה" : "New Submission";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
      >
        {label}
      </button>
      <NewSubmissionModal
        locale={locale}
        clusterId={clusterId}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
