import { isLocale, type Locale } from "@/i18n.config";

type KbPlaceholderPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function KbPlaceholderPage({ params }: KbPlaceholderPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";

  return (
    <div className="text-start">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
        {locale === "he" ? "מאגר ידע" : "Knowledge Base"}
      </h1>
      <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
        {locale === "he" ? "ממשק מאגר הידע יגיע בקרוב." : "KB UI coming soon."}
      </p>
    </div>
  );
}
