import { expect, test, type Page } from "@playwright/test";

const password = process.env.CAREVIA_E2E_PASSWORD ?? "carevia-e2e-password";

async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/Kullan/).fill("e2e_admin");
  await page.getByLabel(/ifre/).fill(password);
  await page.getByRole("button", { name: /Giri/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

test("empty management forms show required field feedback", async ({ page }) => {
  await loginAsAdmin(page);

  await page.getByRole("link", { name: "Hastalar" }).click();
  await page.getByRole("button", { name: "Hasta ekle" }).click();
  const patientDialog = page.getByRole("dialog", { name: "Hasta ekle" });

  await expect(patientDialog.getByText("* ile işaretli alanlar zorunludur.")).toBeVisible();
  await patientDialog.getByRole("button", { name: "Kaydet" }).click();
  await expect(patientDialog.getByText("Bu alan zorunludur.")).toHaveCount(3);
  await expect(patientDialog).toBeVisible();
  await patientDialog.getByRole("button", { name: "İptal" }).click();

  await page.getByRole("link", { name: "Sağlık Çalışanları" }).click();
  await page.getByRole("button", { name: "Sağlık çalışanı ekle" }).click();
  const clinicianDialog = page.getByRole("dialog", { name: "Sağlık çalışanı ekle" });

  await expect(clinicianDialog.getByText("* ile işaretli alanlar zorunludur.")).toBeVisible();
  await clinicianDialog.getByRole("button", { name: "Kaydet" }).click();
  await expect(clinicianDialog.getByText("Bu alan zorunludur.")).toHaveCount(4);
  await expect(clinicianDialog.getByText("Şifre en az 8 karakter olmalıdır.")).toBeVisible();
  await expect(clinicianDialog).toBeVisible();
  await clinicianDialog.getByRole("button", { name: "İptal" }).click();

  await page.getByRole("link", { name: "Kullanıcılar" }).click();
  await page.getByRole("button", { name: "Kullanıcı ekle" }).click();
  const userDialog = page.getByRole("dialog", { name: "Kullanıcı ekle" });

  await expect(userDialog.getByText("* ile işaretli alanlar zorunludur.")).toBeVisible();
  await userDialog.getByRole("button", { name: "Kaydet" }).click();
  await expect(userDialog.getByText("Bu alan zorunludur.")).toHaveCount(4);
  await expect(userDialog.getByText("Şifre en az 8 karakter olmalıdır.")).toBeVisible();
  await expect(userDialog).toBeVisible();
});
