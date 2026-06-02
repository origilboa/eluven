import type { NextConfig } from "next";

import { defaultLocale, locales } from "./i18n.config";

/**
 * App Router uses middleware + [locale] routes for i18n (Next.js 16).
 * Locale list mirrors the Pages Router i18n block from 07-rtl-i18n.mdc:
 *   locales: ["en", "he"], defaultLocale: "en", localeDetection: true
 */
const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_DEFAULT_LOCALE: defaultLocale,
    NEXT_PUBLIC_LOCALES: locales.join(","),
  },
};

export default nextConfig;
