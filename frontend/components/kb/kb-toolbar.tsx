"use client";

import { useState } from "react";

import { NewCollectionModal } from "@/components/kb/new-collection-modal";
import type { Locale } from "@/i18n.config";

type KbToolbarProps = {
  locale: Locale;
};

export function KbToolbar({ locale }: KbToolbarProps) {
  const [open, setOpen] = useState(false);

  const copy =
    locale === "he"
      ? {
          title: "מאגר ידע",
          subtitle: "אוספי מסמכים לשימוש חוזר במשימות ובקבוצות",
          newCollection: "אוסף חדש",
        }
      : {
          title: "Knowledge Base",
          subtitle: "Reusable document collections for tasks and clusters",
          newCollection: "New Collection",
        };

  return (
    <>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="text-start">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
            {copy.title}
          </h1>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
        </div>

        <button
          type="button"
          data-testid="new-collection-button"
          onClick={() => setOpen(true)}
          className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
        >
          {copy.newCollection}
        </button>
      </div>

      <NewCollectionModal locale={locale} open={open} onClose={() => setOpen(false)} />
    </>
  );
}
