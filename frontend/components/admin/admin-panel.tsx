"use client";

import { useMemo, useState } from "react";

import { InvitationsPanel } from "@/components/admin/invitations-panel";
import { OrgsPanel } from "@/components/admin/orgs-panel";
import { UsersPanel } from "@/components/admin/users-panel";
import { isAppAdmin } from "@/lib/admin-access";
import type { Locale } from "@/i18n.config";

type AdminTab = "organizations" | "users" | "invitations";

type AdminPanelProps = {
  locale: Locale;
  userRole: string;
  currentUserId: string;
};

export function AdminPanel({ locale, userRole, currentUserId }: AdminPanelProps) {
  const [activeTab, setActiveTab] = useState<AdminTab>(
    isAppAdmin(userRole) ? "organizations" : "users",
  );

  const copy =
    locale === "he"
      ? {
          title: "ניהול",
          subtitle: "ארגונים, משתמשים והזמנות",
          organizations: "ארגונים",
          users: "משתמשים",
          invitations: "הזמנות",
        }
      : {
          title: "Admin",
          subtitle: "Manage organizations, users, and invitations",
          organizations: "Organizations",
          users: "Users",
          invitations: "Invitations",
        };

  const tabs = useMemo(() => {
    const items: { id: AdminTab; label: string; visible: boolean }[] = [
      { id: "organizations", label: copy.organizations, visible: isAppAdmin(userRole) },
      { id: "users", label: copy.users, visible: true },
      { id: "invitations", label: copy.invitations, visible: true },
    ];
    return items.filter((item) => item.visible);
  }, [copy.invitations, copy.organizations, copy.users, userRole]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="text-start">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{copy.title}</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{copy.subtitle}</p>
      </header>

      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2 dark:border-zinc-800">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "organizations" ? (
        <OrgsPanel locale={locale} userRole={userRole} />
      ) : null}
      {activeTab === "users" ? <UsersPanel locale={locale} userRole={userRole} currentUserId={currentUserId} /> : null}
      {activeTab === "invitations" ? (
        <InvitationsPanel locale={locale} userRole={userRole} />
      ) : null}
    </div>
  );
}
