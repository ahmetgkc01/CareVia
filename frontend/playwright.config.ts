import { defineConfig, devices } from "@playwright/test";

const backendCommand = process.platform === "win32"
  ? "..\\.venv\\Scripts\\python.exe ..\\backend\\manage.py runserver 127.0.0.1:8000 --noreload"
  : "python ../backend/manage.py runserver 127.0.0.1:8000 --noreload";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: backendCommand,
      url: "http://127.0.0.1:8000/api/health/",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
