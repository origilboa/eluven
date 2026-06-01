import type { UserResponse } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

import { Sidebar } from "./sidebar";

type ShellProps = {
  locale: Locale;
  user: UserResponse;
  children: React.ReactNode;
};

export function Shell({ locale, user, children }: ShellProps) {
  return (
    <div className="flex min-h-full flex-1 bg-zinc-50 dark:bg-black">
      <Sidebar locale={locale} user={user} />
      <main className="min-w-0 flex-1 overflow-x-hidden">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
    </div>
  );
}
