"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";
import { isAppAdmin } from "@/lib/admin-access";
import type { AdminOrgResponse, AdminUserResponse, UpdateAdminUserRequest } from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type UsersPanelProps = {
  locale: Locale;
  userRole: string;
  currentUserId: string;
};

export function UsersPanel({ locale, userRole, currentUserId }: UsersPanelProps) {
  const queryClient = useQueryClient();
  const [orgFilter, setOrgFilter] = useState<string>("");

  const copy =
    locale === "he"
      ? {
          title: "משתמשים",
          name: "שם",
          email: "אימייל",
          role: "תפקיד",
          org: "ארגון",
          status: "סטטוס",
          active: "פעיל",
          inactive: "לא פעיל",
          deactivate: "השבת",
          activate: "הפעל",
          filterOrg: "סנן לפי ארגון",
          allOrgs: "כל הארגונים",
          empty: "אין משתמשים.",
          loading: "טוען משתמשים…",
          loadError: "לא ניתן לטעון משתמשים.",
          retry: "נסה שוב",
          roles: { app_admin: "מנהל מערכת", org_admin: "מנהל ארגון", user: "משתמש" },
        }
      : {
          title: "Users",
          name: "Name",
          email: "Email",
          role: "Role",
          org: "Organization",
          status: "Status",
          active: "Active",
          inactive: "Inactive",
          deactivate: "Deactivate",
          activate: "Activate",
          filterOrg: "Filter by org",
          allOrgs: "All orgs",
          empty: "No users yet.",
          loading: "Loading users…",
          loadError: "Could not load users.",
          retry: "Try again",
          roles: { app_admin: "App admin", org_admin: "Org admin", user: "User" },
        };

  const { data: orgs = [] } = useQuery({
    queryKey: ["admin-orgs"],
    queryFn: () => api.get<AdminOrgResponse[]>("/admin/orgs"),
    enabled: isAppAdmin(userRole),
  });

  const usersQueryKey = ["admin-users", orgFilter || null] as const;
  const {
    data: users = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: usersQueryKey,
    queryFn: () => {
      const suffix = orgFilter ? `?org_id=${encodeURIComponent(orgFilter)}` : "";
      return api.get<AdminUserResponse[]>(`/admin/users${suffix}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, body }: { userId: string; body: UpdateAdminUserRequest }) =>
      api.patch<AdminUserResponse>(`/admin/users/${userId}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.title}
        </h2>
        {isAppAdmin(userRole) ? (
          <label className="text-start text-xs text-zinc-500">
            <span className="me-2 font-medium text-zinc-700 dark:text-zinc-300">
              {copy.filterOrg}
            </span>
            <select
              value={orgFilter}
              onChange={(event) => setOrgFilter(event.target.value)}
              className="rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              <option value="">{copy.allOrgs}</option>
              {orgs.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {isLoading ? (
        <p className="text-start text-sm text-zinc-500">{copy.loading}</p>
      ) : isError ? (
        <div className="space-y-2 text-start">
          <p className="text-sm text-red-600 dark:text-red-400">
            {error instanceof Error ? error.message : copy.loadError}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="text-sm font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
          >
            {copy.retry}
          </button>
        </div>
      ) : users.length === 0 ? (
        <p className="text-start text-sm text-zinc-500">{copy.empty}</p>
      ) : (
        <ul className="space-y-3">
          {users.map((user) => {
            const isSelf = user.id === currentUserId;
            const roleLabel =
              copy.roles[user.role as keyof typeof copy.roles] ?? user.role;
            return (
              <li
                key={user.id}
                className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="text-start">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                      {user.name}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">{user.email}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {roleLabel}
                      {isAppAdmin(userRole) ? ` · ${user.org_name}` : ""}
                    </p>
                  </div>
                  {!isSelf ? (
                    <button
                      type="button"
                      disabled={updateMutation.isPending}
                      onClick={() =>
                        updateMutation.mutate({
                          userId: user.id,
                          body: { is_active: !user.is_active },
                        })
                      }
                      className="text-xs font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
                    >
                      {user.is_active ? copy.deactivate : copy.activate}
                    </button>
                  ) : null}
                </div>
                <p className="mt-2 text-start text-xs text-zinc-500">
                  {copy.status}: {user.is_active ? copy.active : copy.inactive}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
