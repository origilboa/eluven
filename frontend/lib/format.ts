import type { Locale } from "@/i18n.config";

export function formatRelativeUpdatedAt(isoDate: string, locale: Locale): string {
  const date = new Date(isoDate);
  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60_000);

  if (diffMinutes < 1) {
    return locale === "he" ? "עודכן עכשיו" : "Updated just now";
  }

  if (diffMinutes < 60) {
    return locale === "he"
      ? `עודכן לפני ${diffMinutes} דקות`
      : `Updated ${diffMinutes}m ago`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return locale === "he" ? `עודכן לפני ${diffHours} שעות` : `Updated ${diffHours}h ago`;
  }

  return new Intl.DateTimeFormat(locale === "he" ? "he-IL" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function getStatusLabel(status: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    draft: { en: "Draft", he: "טיוטה" },
    active: { en: "Active", he: "פעיל" },
    complete: { en: "Complete", he: "הושלם" },
    archived: { en: "Archived", he: "בארכיון" },
  };

  return labels[status]?.[locale] ?? status;
}
