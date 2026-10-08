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

test("admin can run a population allergy query without selecting a patient", async ({ page }) => {
  await login(page, "e2e_admin");
  await page.getByRole("link", { name: "AI Asistan" }).click();

  const responsePromise = page.waitForResponse((response) => (
    response.url().includes("/api/assistant/messages/")
      && response.request().method() === "POST"
      && response.status() === 201
  ));
  await page.getByRole("button", { name: /Alerjisi olan hastaları listele/ }).click();
  await responsePromise;

  await expect(page.getByText(/doğrulanmış alerji kaydı bulunuyor/)).toBeVisible();
  await expect(page.getByText(/otomatik gönderilecek/)).toHaveCount(0);
});

test("admin can edit and view a structured patient allergy", async ({ page }) => {
  await login(page, "e2e_admin");
  await page.getByRole("link", { name: "Hastalar" }).click();
  await page.getByPlaceholder(/Ad, e-posta veya telefon ara/).fill("E2E Patient");

  const row = page.getByRole("row").filter({ hasText: "E2E Patient" });
  await expect(row).toBeVisible();
  await row.getByRole("button", { name: /Hastayı düzenle/ }).click();

  const dialog = page.getByRole("dialog", { name: /Hastayı düzenle/ });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Alerjen").fill("Synthetic E2E pollen");
  await dialog.getByLabel("Reaksiyon").fill("Synthetic E2E skin reaction");
  await dialog.getByLabel("Önem derecesi").click();
  await page.getByRole("option", { name: "Orta" }).click();

  const updatePromise = page.waitForResponse((response) => (
    response.url().includes("/api/patients/")
      && response.request().method() === "PATCH"
      && response.status() === 200
  ));
  await dialog.getByRole("button", { name: "Kaydet" }).click();
  await updatePromise;
  await expect(dialog).toHaveCount(0);

  await row.getByRole("button", { name: /Hasta detaylarını görüntüle/ }).click();
  const details = page.getByRole("dialog", { name: /Hasta detayları/ });
  await expect(details.getByText(/Synthetic E2E pollen/)).toBeVisible();
  await expect(details.getByText(/Synthetic E2E skin reaction/)).toBeVisible();
  await expect(details.getByText(/Orta/)).toBeVisible();
});

test("patient sees assistant but not user management", async ({ page }) => {
  await login(page, "e2e_patient");

  await expect(page.getByRole("link", { name: "AI Asistan" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Kullan/ })).toHaveCount(0);
});

test("doctor prompt is sent after selecting a searched patient", async ({ page }) => {
  await login(page, "e2e_doctor");
  const historyPromise = page.waitForResponse((response) => (
    response.url().includes("/api/assistant/messages/")
      && response.request().method() === "GET"
  ));
  await page.getByRole("link", { name: "AI Asistan" }).click();
  await historyPromise;
  await expect(page.getByRole("heading", { name: /Carevia AI Asistan/ })).toBeVisible();

  const clearChat = page.getByRole("button", { name: /Sohbeti temizle/ });
  if (await clearChat.isEnabled()) {
    const clearPromise = page.waitForResponse((response) => (
      response.url().includes("/api/assistant/messages/")
        && response.request().method() === "DELETE"
        && response.status() === 204
    ));
    await clearChat.click();
    await clearPromise;
  }

  await expect(page.getByRole("heading", { name: /Size nasıl yardımcı/ })).toBeVisible();
  await page.getByRole("button", { name: /Hastanın yaklaşan randevularını göster/ }).click();
  await expect(page.getByText(/otomatik gönderilecek/)).toBeVisible();

  const patientSearch = page.getByRole("combobox", { name: /Hasta bağlamı/ });
  await patientSearch.fill("E2E Patient");
  const responsePromise = page.waitForResponse((response) => (
    response.url().includes("/api/assistant/messages/")
      && response.request().method() === "POST"
      && response.status() === 201
  ));
  await page.getByRole("option", { name: "E2E Patient" }).click();
  await responsePromise;

  await expect(page.getByText(/Carevia randevu kayıtları/)).toBeVisible();
});
