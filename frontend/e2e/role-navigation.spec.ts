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
