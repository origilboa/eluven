import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";

import { authOptions } from "@/lib/auth";
import type { Locale } from "@/i18n.config";

export async function getAuthSession() {
  return getServerSession(authOptions);
}

export async function requireAuthSession(locale: Locale) {
  const session = await getAuthSession();
  if (!session?.accessToken) {
    redirect(`/${locale}/login`);
  }
  return session;
}
