import { CollectionCard } from "@/components/kb/collection-card";
import { KbEmptyState } from "@/components/kb/kb-empty-state";
import { KbToolbar } from "@/components/kb/kb-toolbar";
import { api } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import type { KBCollectionResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type KbPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function KbPage({ params }: KbPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let collections: KBCollectionResponse[] = [];
  try {
    collections = await api.get<KBCollectionResponse[]>("/kb/collections", {
      accessToken: session.accessToken,
    });
  } catch {
    collections = [];
  }

  return (
    <div className="space-y-8">
      <KbToolbar locale={locale} />

      {collections.length === 0 ? (
        <KbEmptyState locale={locale} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {collections.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} locale={locale} />
          ))}
        </div>
      )}
    </div>
  );
}
