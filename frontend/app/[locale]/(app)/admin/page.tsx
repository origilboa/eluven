import { redirect } from "next/navigation";

import { AdminPanel } from "@/components/admin/admin-panel";
import { isAdminRole } from "@/lib/admin-access";
import { requireAuthSession } from "@/lib/auth-session";
import { isLocale, type Locale } from "@/i18n.config";

type AdminPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function AdminPage({ params }: AdminPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  if (!isAdminRole(session.user.role)) {
    redirect(`/${locale}/dashboard`);
  }

  return (
    <AdminPanel
      locale={locale}
      userRole={session.user.role}
      currentUserId={session.user.id}
    />
  );
}
