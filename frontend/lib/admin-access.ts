export function isAdminRole(role: string): boolean {
  return role === "app_admin" || role === "org_admin";
}

export function isAppAdmin(role: string): boolean {
  return role === "app_admin";
}

export function localizedInviteUrl(baseUrl: string, locale: "en" | "he"): string {
  return baseUrl.replace("/en/accept-invite", `/${locale}/accept-invite`);
}
