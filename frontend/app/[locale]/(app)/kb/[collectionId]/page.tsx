import { notFound } from "next/navigation";

import { CollectionDetail } from "@/components/kb/collection-detail";
import { api } from "@/lib/api";
import { requireAuthSession } from "@/lib/auth-session";
import type { KBDocumentResponse, KBCollectionResponse } from "@/lib/types/api";
import { isLocale, type Locale } from "@/i18n.config";

type CollectionDetailPageProps = {
  params: Promise<{ locale: string; collectionId: string }>;
};

export default async function CollectionDetailPage({ params }: CollectionDetailPageProps) {
  const { locale: localeParam, collectionId } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  let collection: KBCollectionResponse | null = null;
  let documents: KBDocumentResponse[] = [];

  try {
    collection = await api.get<KBCollectionResponse>(`/kb/collections/${collectionId}`, {
      accessToken: session.accessToken,
    });
    documents = await api.get<KBDocumentResponse[]>(
      `/kb/collections/${collectionId}/documents`,
      { accessToken: session.accessToken },
    );
  } catch {
    notFound();
  }

  return (
    <CollectionDetail
      locale={locale}
      collection={collection}
      initialDocuments={documents}
    />
  );
}
