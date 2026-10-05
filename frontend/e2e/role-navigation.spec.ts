import { expect, test, type Page } from "@playwright/test";

const password = process.env.CAREVIA_E2E_PASSWORD ?? "carevia-e2e-password";

async function login(page: Page, username: string) {
  await page.goto("/login");
  await page.getByLabel(/Kullan/).fill(username);
  await page.getByLabel(/ifre/).fill(password);
  await page.getByRole("button", { name: /Giri/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: /Genel Bak/ })).toBeVisible();
}

test("admin sees management and assistant navigation", async ({ page }) => {
  await login(page, "e2e_admin");

  await expect(page.getByRole("link", { name: /Kullan/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "AI Asistan" })).toBeVisible();
});

test("patient sees assistant but not user management", async ({ page }) => {
  await login(page, "e2e_patient");

  await expect(page.getByRole("link", { name: "AI Asistan" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Kullan/ })).toHaveCount(0);
});
