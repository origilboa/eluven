"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { useMemo, useState } from "react";

import { formatOrgLabel } from "@/lib/modules";
import type { UserResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type NavItem = {
  href: string;
  label: string;
  testId: string;
};

type SidebarProps = {
  locale: Locale;
  user: UserResponse;
};

function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ locale, user }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const copy =
    locale === "he"
      ? {
          dashboard: "לוח בקרה",
          assignments: "מטלות",
          kb: "מאגר ידע",
          instructionStudio: "סטודיו הוראות",
          collapse: "כווץ תפריט",
          expand: "הרחב תפריט",
          logout: "התנתקות",
        }
      : {
          dashboard: "Dashboard",
          assignments: "Assignments",
          kb: "KB",
          instructionStudio: "Instruction Studio",
          collapse: "Collapse sidebar",
          expand: "Expand sidebar",
          logout: "Log out",
        };

  const navItems: NavItem[] = useMemo(
    () => [
      {
        href: `/${locale}/dashboard`,
        label: copy.dashboard,
        testId: "nav-dashboard",
      },
      {
        href: `/${locale}/clusters`,
        label: copy.assignments,
        testId: "nav-clusters",
      },
      {
        href: `/${locale}/kb`,
        label: copy.kb,
        testId: "nav-kb",
      },
      {
        href: `/${locale}/instruction-studio`,
        label: copy.instructionStudio,
        testId: "nav-instruction-studio",
      },
    ],
    [copy.assignments, copy.dashboard, copy.instructionStudio, copy.kb, locale],
  );

  return (
    <aside
      data-testid="sidebar"
      className={`flex shrink-0 flex-col border-e border-zinc-200 bg-white transition-[width] duration-200 dark:border-zinc-800 dark:bg-zinc-950 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-3 py-4 dark:border-zinc-800">
        {!collapsed ? (
          <Link
            href={`/${locale}/dashboard`}
            className="text-start text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-50"
          >
            Eluven
          </Link>
        ) : (
          <span className="mx-auto text-sm font-semibold text-zinc-900 dark:text-zinc-50">
            E
          </span>
        )}
        <button
          type="button"
          aria-label={collapsed ? copy.expand : copy.collapse}
          onClick={() => setCollapsed((value) => !value)}
          className="inline-flex size-8 items-center justify-center rounded-md border border-zinc-200 text-zinc-600 transition-colors hover:bg-zinc-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
        >
          <span aria-hidden="true">{collapsed ? "»" : "«"}</span>
        </button>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-2" aria-label="Main navigation">
        {navItems.map((item) => {
          const active = isActivePath(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              data-testid={item.testId}
              title={collapsed ? item.label : undefined}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-900"
              } ${collapsed ? "text-center" : "text-start"}`}
            >
              {collapsed ? item.label.slice(0, 1) : item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-200 p-3 dark:border-zinc-800">
        {!collapsed ? (
          <div className="space-y-3 text-start">
            <div>
              <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-50">
                {user.name}
              </p>
              <p className="truncate text-xs text-zinc-500 dark:text-zinc-400">
                {formatOrgLabel(user.org_id, locale)}
              </p>
            </div>
            <button
              type="button"
              data-testid="logout-button"
              onClick={() => void signOut({ callbackUrl: `/${locale}/login` })}
              className="text-sm font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
            >
              {copy.logout}
            </button>
          </div>
        ) : (
          <p
            className="mx-auto flex size-8 items-center justify-center rounded-full bg-zinc-100 text-xs font-semibold text-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
            title={user.name}
          >
            {user.name.slice(0, 1).toUpperCase()}
          </p>
        )}
      </div>
    </aside>
  );
}
