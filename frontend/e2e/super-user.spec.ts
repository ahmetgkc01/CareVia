import { expect, test } from "@playwright/test";

const password = process.env.CAREVIA_E2E_PASSWORD ?? "carevia-e2e-password";

async function login(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login");
  await page.getByLabel(/Kullan/).fill(username);
  await page.getByLabel(/ifre/).fill(password);
  await page.getByRole("button", { name: /Giri/ }).click();
}

test("Super User is identified and can assign the Admin role", async ({ page }) => {
  await login(page, "e2e_admin");

  await expect(page.getByText("Super User", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: /Kullan/ }).click();
  await page.getByRole("button", { name: "Kullanıcı ekle" }).click();

  const dialog = page.getByRole("dialog", { name: "Kullanıcı ekle" });
  await dialog.getByLabel("Rol").click();
  await expect(page.getByRole("option", { name: "Admin", exact: true })).toBeVisible();
});

test("regular users see their role in the header", async ({ page }) => {
  await login(page, "e2e_doctor");

  const roleBadge = page.getByText("Doktor", { exact: true });
  await expect(roleBadge).toBeVisible();
  await expect(roleBadge).toHaveCSS("font-size", "16px");
});
