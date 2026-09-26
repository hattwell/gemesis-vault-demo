import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

export default defineConfig({
  testDir: "./tests",
  testMatch: "demo.spec.ts",
  timeout: 25_000,
  use: { baseURL: "http://127.0.0.1:18765", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { browserName: "chromium", viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { browserName: "chromium", viewport: { width: 390, height: 844 } } },
  ],
  webServer: {
    command: `${process.env.PYTHON_BIN || "python3"} -m demo.launch`,
    cwd: resolve(process.cwd(), ".."),
    env: { PORT: "18765" },
    url: "http://127.0.0.1:18765/api/catalog",
    timeout: 25_000,
    reuseExistingServer: false,
  },
});
