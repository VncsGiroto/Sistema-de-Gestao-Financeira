import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1, // serial: evita estourar o rate-limit de login (10/min/IP) entre specs
  use: { baseURL: process.env.E2E_BASE_URL || "http://localhost:8080" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
