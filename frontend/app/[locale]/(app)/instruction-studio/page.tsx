import { InstructionStudioPanel } from "@/components/instruction-studio/instruction-studio-panel";
import { requireAuthSession } from "@/lib/auth-session";
import { isLocale, type Locale } from "@/i18n.config";

type InstructionStudioPageProps = {
  params: Promise<{ locale: string }>;
};

export default async function InstructionStudioPage({ params }: InstructionStudioPageProps) {
  const { locale: localeParam } = await params;
  const locale: Locale = isLocale(localeParam) ? localeParam : "en";
  const session = await requireAuthSession(locale);

  return (
    <InstructionStudioPanel locale={locale} userRole={session.user.role} />
  );
}
