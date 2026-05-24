import { defineConfig, devices } from "@playwright/test";

/**
 * Slidelang E2E config.
 *
 * Default: tests run against http://localhost:3000 (requires `npm run dev` running).
 * CI: sets BASE_URL to https://slidelang.vercel.app so we test the deployed app.
 *
 * Pattern: one Chromium project (smoke). Firefox/Webkit deferred to v1 — they're
 * 3x the runtime for marginal coverage at v0 scale.
 */
const BASE_URL = process.env.BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000, // Generation can take 20-30s on cold start
  expect: {
    timeout: 5_000,
  },
  fullyParallel: false, // Generation hits Claude; serialize to be polite to rate limits
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Same reason as fullyParallel: false

  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
