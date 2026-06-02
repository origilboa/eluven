import { expect, test } from "@playwright/test";

test("login page loads", async ({ page }) => {
  await page.goto("/en/login");
  await expect(page.getByRole("heading")).toBeVisible();
  await expect(page.getByLabel(/email/i)).toBeVisible();
});
