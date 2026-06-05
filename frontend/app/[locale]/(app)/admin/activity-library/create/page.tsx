import { redirect } from "next/navigation";

import { ActivityTypeWizard } from "@/components/activity-studio/activity-type-wizard";
import { isAppAdmin } from "@/lib/admin-access";
import { requireAuthSession } from "@/lib/auth-session";
import { isLocale, type Locale } from "@/i18n.config";

type CreateActivityPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function CreateActivityPage({ params }: CreateActivityPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  if (!isAppAdmin(session.user.role)) {
    redirect(`/${locale}/dashboard`);
  }

  return <ActivityTypeWizard locale={locale} />;
}
