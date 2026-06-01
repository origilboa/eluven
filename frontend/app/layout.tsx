import type { Metadata } from "next";
import { Heebo, Inter } from "next/font/google";
import { headers } from "next/headers";

import { AppProviders } from "@/components/providers/app-providers";
import { defaultLocale, isLocale, isRTL, type Locale } from "@/i18n.config";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const heebo = Heebo({
  subsets: ["hebrew", "latin"],
  variable: "--font-heebo",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Eluven",
  description: "AI-powered academic research workspace",
};

async function getLocale(): Promise<Locale> {
  const headersList = await headers();
  const localeHeader = headersList.get("x-locale");
  if (localeHeader && isLocale(localeHeader)) {
    return localeHeader;
  }
  return defaultLocale;
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const rtl = isRTL(locale);

  return (
    <html
      lang={locale}
      dir={rtl ? "rtl" : "ltr"}
      className={`${inter.variable} ${heebo.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
