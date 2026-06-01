import { Shell } from "@/components/layout/shell";
import { requireAuthSession } from "@/lib/auth-session";
import { isLocale, type Locale } from "@/i18n.config";

type AppLayoutProps = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export default async function AppLayout({ children, params }: AppLayoutProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  return (
    <Shell locale={locale} user={session.user}>
      {children}
    </Shell>
  );
}
