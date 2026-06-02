"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";
import { isAppAdmin } from "@/lib/admin-access";
import type {
  AdminOrgResponse,
  CreateOrgRequest,
  UpdateOrgRequest,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type OrgsPanelProps = {
  locale: Locale;
  userRole: string;
};

export function OrgsPanel({ locale, userRole }: OrgsPanelProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);

  const copy =
    locale === "he"
      ? {
          title: "ארגונים",
          name: "שם",
          slug: "מזהה (slug)",
          create: "צור ארגון",
          creating: "יוצר…",
          active: "פעיל",
          inactive: "לא פעיל",
          users: "משתמשים",
          platform: "פלטפורמה",
          save: "שמור",
          empty: "אין ארגונים.",
        }
      : {
          title: "Organizations",
          name: "Name",
          slug: "Slug",
          create: "Create org",
          creating: "Creating…",
          active: "Active",
          inactive: "Inactive",
          users: "users",
          platform: "Platform",
          save: "Save",
          empty: "No organizations yet.",
        };

  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ["admin-orgs"],
    queryFn: () => api.get<AdminOrgResponse[]>("/admin/orgs"),
    enabled: isAppAdmin(userRole),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateOrgRequest) => api.post<AdminOrgResponse>("/admin/orgs", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-orgs"] });
      setName("");
      setSlug("");
      setError(null);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ orgId, body }: { orgId: string; body: UpdateOrgRequest }) =>
      api.patch<AdminOrgResponse>(`/admin/orgs/${orgId}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-orgs"] }),
  });

  if (!isAppAdmin(userRole)) {
    return null;
  }

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.title}
        </h2>
        <form
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate({
              name,
              slug: slug.trim() || null,
            });
          }}
        >
          <label className="text-start text-xs text-zinc-500">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
              {copy.name}
            </span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              className="rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="text-start text-xs text-zinc-500">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
              {copy.slug}
            </span>
            <input
              value={slug}
              onChange={(event) => setSlug(event.target.value)}
              className="rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            {createMutation.isPending ? copy.creating : copy.create}
          </button>
        </form>
        {error ? (
          <p className="mt-2 text-start text-xs text-red-600 dark:text-red-400">{error}</p>
        ) : null}
      </div>

      {isLoading ? null : orgs.length === 0 ? (
        <p className="text-start text-sm text-zinc-500">{copy.empty}</p>
      ) : (
        <ul className="space-y-3">
          {orgs.map((org) => (
            <OrgRow
              key={org.id}
              org={org}
              copy={copy}
              onToggleActive={() =>
                updateMutation.mutate({
                  orgId: org.id,
                  body: { is_active: !org.is_active },
                })
              }
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function OrgRow({
  org,
  copy,
  onToggleActive,
}: {
  org: AdminOrgResponse;
  copy: Record<string, string>;
  onToggleActive: () => void;
}) {
  const statusLabel = org.is_active ? copy.active : copy.inactive;
  return (
    <li className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="text-start">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{org.name}</p>
            {org.is_platform_org ? (
              <span className="rounded bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-950 dark:text-violet-300">
                {copy.platform}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-zinc-500">
            {org.slug} · {org.user_count} {copy.users}
          </p>
        </div>
        <button
          type="button"
          onClick={onToggleActive}
          className="text-xs font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
        >
          {org.is_active ? copy.inactive : copy.active}
        </button>
      </div>
      <p className="mt-2 text-start text-xs text-zinc-500">{statusLabel}</p>
    </li>
  );
}
