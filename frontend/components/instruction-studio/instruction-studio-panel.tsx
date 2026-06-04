"use client";

import { useMemo, useState } from "react";

import { InstructionSetEditor } from "@/components/instructions/instruction-set-editor";
import type { InstructionLevel } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type InstructionStudioPanelProps = {
  locale: Locale;
  userRole: string;
};

type TabConfig = {
  level: InstructionLevel;
  label: string;
  subtitle: string;
  visible: boolean;
  canEdit: boolean;
};

export function InstructionStudioPanel({ locale, userRole }: InstructionStudioPanelProps) {
  const [activeTab, setActiveTab] = useState<InstructionLevel>("user");

  const copy =
    locale === "he"
      ? {
          title: "Instruction Studio",
          subtitle: "ניהול הוראות לפי רמות ההיררכיה",
          platform: "פלטפורמה",
          org: "ארגון",
          user: "משתמש",
          platformSubtitle: "הוראות ברירת מחדל לכל הארגונים בפלטפורמה.",
          orgSubtitle: "הוראות ברירת מחדל לכל המשתמשים בארגון.",
          userSubtitle: "הוראות אישיות — חלות על כל המשימות שלך.",
          readOnly: "תצוגה בלבד — אין לך הרשאת עריכה ברמה זו.",
        }
      : {
          title: "Instruction Studio",
          subtitle: "Manage instructions across hierarchy levels",
          platform: "Platform",
          org: "Organization",
          user: "User",
          platformSubtitle: "Default instructions for all organizations on the platform.",
          orgSubtitle: "Default instructions for all users in your organization.",
          userSubtitle: "Personal instructions applied across your tasks.",
          readOnly: "Read-only — you do not have edit access at this level.",
        };

  const tabs = useMemo<TabConfig[]>(
    () => [
      {
        level: "platform",
        label: copy.platform,
        subtitle: copy.platformSubtitle,
        visible: true,
        canEdit: userRole === "app_admin",
      },
      {
        level: "org",
        label: copy.org,
        subtitle: copy.orgSubtitle,
        visible: userRole === "org_admin" || userRole === "app_admin",
        canEdit: userRole === "org_admin" || userRole === "app_admin",
      },
      {
        level: "user",
        label: copy.user,
        subtitle: copy.userSubtitle,
        visible: true,
        canEdit: true,
      },
    ],
    [
      copy.org,
      copy.orgSubtitle,
      copy.platform,
      copy.platformSubtitle,
      copy.user,
      copy.userSubtitle,
      userRole,
    ],
  );

  const visibleTabs = tabs.filter((tab) => tab.visible);
  const currentTab = visibleTabs.find((tab) => tab.level === activeTab) ?? visibleTabs[0];
  const currentLevel = currentTab?.level ?? "user";

  return (
    <div className="space-y-6">
      <div className="text-start">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{copy.subtitle}</p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
        {visibleTabs.map((tab) => (
          <button
            key={tab.level}
            type="button"
            onClick={() => setActiveTab(tab.level)}
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              currentLevel === tab.level
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {currentTab ? (
        <InstructionSetEditor
          key={currentLevel}
          locale={locale}
          canEdit={currentTab.canEdit}
          queryKey={["instructions", currentLevel]}
          fetchPath={`/instructions/${currentLevel}`}
          createPath={`/instructions/${currentLevel}`}
          activatePath={`/instructions/${currentLevel}/activate`}
          title={currentTab.label}
          subtitle={currentTab.subtitle}
          readOnlyMessage={copy.readOnly}
        />
      ) : null}
    </div>
  );
}
