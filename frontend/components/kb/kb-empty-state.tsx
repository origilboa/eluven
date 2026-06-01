import type { Locale } from "@/i18n.config";

type KbEmptyStateProps = {
  locale: Locale;
};

export function KbEmptyState({ locale }: KbEmptyStateProps) {
  const copy =
    locale === "he"
      ? {
          title: "אין עדיין אוספים",
          description:
            "צור אוסף מאגר ידע כדי להעלות מסמכים ולצרף אותם למשימות או לקבוצות.",
        }
      : {
          title: "No collections yet",
          description:
            "Create a knowledge base collection to upload documents and attach them to tasks or clusters.",
        };

  return (
    <div className="rounded-xl border border-dashed border-zinc-300 bg-white px-6 py-12 text-center dark:border-zinc-700 dark:bg-zinc-950">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-zinc-600 dark:text-zinc-400">
        {copy.description}
      </p>
    </div>
  );
}
