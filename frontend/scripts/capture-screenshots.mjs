import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const outputDirectory = path.resolve(scriptDirectory, "../../docs/images");
const baseUrl = process.env.CAREVIA_SCREENSHOT_URL ?? "http://127.0.0.1:5173";
const password = process.env.CAREVIA_E2E_PASSWORD ?? "carevia-e2e-password";

await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });

try {
  await page.goto(`${baseUrl}/login`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /Giri/ }).waitFor();
  await page.screenshot({ path: path.join(outputDirectory, "carevia-login.png"), fullPage: true });

  await page.getByLabel(/Kullan/).fill("e2e_admin");
  await page.getByLabel(/ifre/).fill(password);
  await page.getByRole("button", { name: /Giri/ }).click();
  await page.waitForURL(/\/dashboard$/);
  await page.getByText("fix: persist release history in production").waitFor();
  await page.screenshot({ path: path.join(outputDirectory, "carevia-dashboard.png"), fullPage: true });

  await page.getByRole("link", { name: "Hastalar" }).click();
  await page.getByRole("heading", { name: "Hastalar" }).waitFor();
  await page.getByPlaceholder(/Ad, e-posta veya telefon ara/).fill("E2E Patient");
  await page.getByRole("row").filter({ hasText: "E2E Patient" }).waitFor();
  await page.screenshot({ path: path.join(outputDirectory, "carevia-patients.png"), fullPage: true });

  await page.getByRole("link", { name: "AI Asistan" }).click();
  await page.getByRole("heading", { name: /Carevia AI Asistan/ }).waitFor();
  const clearChat = page.getByRole("button", { name: /Sohbeti temizle/ });
  if (await clearChat.isEnabled()) {
    const clearResponse = page.waitForResponse((response) => (
      response.url().includes("/api/assistant/messages/")
        && response.request().method() === "DELETE"
        && response.status() === 204
    ));
    await clearChat.click();
    await clearResponse;
    await page.getByText("Size nasıl yardımcı olabilirim?").waitFor();
  }
  const messageInput = page.getByPlaceholder(/Carevia'ya bir soru sorun/);
  await messageInput.fill("Alerjisi olan hastaları listele");
  const assistantResponse = page.waitForResponse((response) => (
    response.url().includes("/api/assistant/messages/")
      && response.request().method() === "POST"
      && response.status() === 201
  ));
  await page.getByRole("button", { name: "Gönder" }).click();
  await page.getByText("Carevia düşünüyor...").waitFor();
  await assistantResponse;
  await page.getByText("Carevia düşünüyor...").waitFor({ state: "hidden" });
  await page.getByText(/doğrulanmış alerji kaydı bulunuyor/).last().waitFor();
  await page.screenshot({ path: path.join(outputDirectory, "carevia-assistant.png"), fullPage: true });
}
finally {
  await browser.close();
}

console.log(`Screenshots written to ${outputDirectory}`);
