/** Shared locale configuration (07-rtl-i18n.mdc). */

export const locales = ["en", "he"] as const;

export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export function isLocale(value: string): value is Locale {
  return locales.includes(value as Locale);
}

export function isRTL(locale: Locale): boolean {
  return locale === "he";
}
