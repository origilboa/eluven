import { isLocale, type Locale } from "@/i18n.config";

type InstructionStudioPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function InstructionStudioPage({ params }: InstructionStudioPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";

  return (
    <div className="text-start">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
        Instruction Studio
      </h1>
      <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
        {locale === "he"
          ? "עריכת הוראות תגיע בשלב מאוחר יותר."
          : "Instruction authoring coming in a later build step."}
      </p>
    </div>
  );
}
