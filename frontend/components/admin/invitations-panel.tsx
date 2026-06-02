"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api";
import { isAppAdmin, localizedInviteUrl } from "@/lib/admin-access";
import type {
  AdminOrgResponse,
  CreateInvitationRequest,
  CreateInvitationResponse,
  InvitationResponse,
} from "@/lib/types/api";
import type { Locale } from "@/i18n.config";

type InvitationsPanelProps = {
  locale: Locale;
  userRole: string;
};

export function InvitationsPanel({ locale, userRole }: InvitationsPanelProps) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("user");
  const [orgId, setOrgId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lastInviteUrl, setLastInviteUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const copy =
    locale === "he"
      ? {
          title: "הזמנות",
          invite: "הזמן משתמש",
          inviting: "שולח…",
          email: "אימייל",
          name: "שם",
          role: "תפקיד",
          org: "ארגון",
          selectOrg: "בחר ארגון",
          copyLink: "העתק קישור",
          copied: "הועתק",
          revoke: "בטל",
          empty: "אין הזמנות.",
          lastLink: "קישור הזמנה (חד-פעמי):",
          roles: { user: "משתמש", org_admin: "מנהל ארגון", app_admin: "מנהל מערכת" },
          statuses: {
            pending: "ממתין",
            accepted: "התקבל",
            expired: "פג תוקף",
            revoked: "בוטל",
          },
        }
      : {
          title: "Invitations",
          invite: "Invite user",
          inviting: "Inviting…",
          email: "Email",
          name: "Name",
          role: "Role",
          org: "Organization",
          selectOrg: "Select org",
          copyLink: "Copy link",
          copied: "Copied",
          revoke: "Revoke",
          empty: "No invitations yet.",
          lastLink: "Invite link (one-time):",
          roles: { user: "User", org_admin: "Org admin", app_admin: "App admin" },
          statuses: {
            pending: "Pending",
            accepted: "Accepted",
            expired: "Expired",
            revoked: "Revoked",
          },
        };

  const { data: orgs = [] } = useQuery({
    queryKey: ["admin-orgs"],
    queryFn: () => api.get<AdminOrgResponse[]>("/admin/orgs"),
    enabled: isAppAdmin(userRole),
  });

  const { data: invitations = [], isLoading } = useQuery({
    queryKey: ["admin-invitations"],
    queryFn: () => api.get<InvitationResponse[]>("/admin/invitations"),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateInvitationRequest) =>
      api.post<CreateInvitationResponse>("/admin/invitations", body),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["admin-invitations"] });
      setLastInviteUrl(localizedInviteUrl(data.invite_url, locale));
      setEmail("");
      setName("");
      setError(null);
      setCopied(false);
    },
    onError: (mutationError: Error) => setError(mutationError.message),
  });

  const revokeMutation = useMutation({
    mutationFn: (invitationId: string) =>
      api.delete<void>(`/admin/invitations/${invitationId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-invitations"] }),
  });

  const roleOptions = isAppAdmin(userRole)
    ? (["user", "org_admin", "app_admin"] as const)
    : (["user", "org_admin"] as const);

  async function handleCopy(url: string) {
    await navigator.clipboard.writeText(url);
    setCopied(true);
  }

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-start text-sm font-semibold text-zinc-900 dark:text-zinc-50">
          {copy.title}
        </h2>
        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate({
              email,
              name,
              role,
              org_id: isAppAdmin(userRole) ? orgId : null,
            });
          }}
        >
          <label className="text-start text-xs text-zinc-500">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
              {copy.email}
            </span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="block w-full rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="text-start text-xs text-zinc-500">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
              {copy.name}
            </span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              className="block w-full rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            />
          </label>
          <label className="text-start text-xs text-zinc-500">
            <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
              {copy.role}
            </span>
            <select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className="block w-full rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            >
              {roleOptions.map((option) => (
                <option key={option} value={option}>
                  {copy.roles[option]}
                </option>
              ))}
            </select>
          </label>
          {isAppAdmin(userRole) ? (
            <label className="text-start text-xs text-zinc-500">
              <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">
                {copy.org}
              </span>
              <select
                value={orgId}
                onChange={(event) => setOrgId(event.target.value)}
                required
                className="block w-full rounded-lg border border-zinc-200 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
              >
                <option value="">{copy.selectOrg}</option>
                {orgs.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              {createMutation.isPending ? copy.inviting : copy.invite}
            </button>
          </div>
        </form>
        {error ? (
          <p className="mt-2 text-start text-xs text-red-600 dark:text-red-400">{error}</p>
        ) : null}
        {lastInviteUrl ? (
          <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-start dark:border-emerald-900 dark:bg-emerald-950">
            <p className="text-xs font-medium text-emerald-800 dark:text-emerald-200">
              {copy.lastLink}
            </p>
            <p className="mt-1 break-all text-xs text-emerald-700 dark:text-emerald-300">
              {lastInviteUrl}
            </p>
            <button
              type="button"
              onClick={() => void handleCopy(lastInviteUrl)}
              className="mt-2 text-xs font-medium text-emerald-800 underline-offset-4 hover:underline dark:text-emerald-200"
            >
              {copied ? copy.copied : copy.copyLink}
            </button>
          </div>
        ) : null}
      </div>

      {isLoading ? null : invitations.length === 0 ? (
        <p className="text-start text-sm text-zinc-500">{copy.empty}</p>
      ) : (
        <ul className="space-y-3">
          {invitations.map((invitation) => {
            const statusLabel =
              copy.statuses[invitation.status as keyof typeof copy.statuses] ??
              invitation.status;
            const roleLabel =
              copy.roles[invitation.role as keyof typeof copy.roles] ?? invitation.role;
            return (
              <li
                key={invitation.id}
                className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="text-start">
                    <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                      {invitation.name}
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">{invitation.email}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {roleLabel} · {invitation.org_name} · {statusLabel}
                    </p>
                  </div>
                  {invitation.status === "pending" ? (
                    <button
                      type="button"
                      onClick={() => revokeMutation.mutate(invitation.id)}
                      className="text-xs font-medium text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400"
                    >
                      {copy.revoke}
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
