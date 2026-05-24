import { expect, test } from "@playwright/test";

/**
 * Slidelang smoke tests.
 *
 * Coverage philosophy (see TDD §11):
 * - Backend correctness is fully covered by pytest (20 tests).
 * - These tests cover the integration: that the frontend can talk to the
 *   backend, generate a deck, render it, and present it. If these pass,
 *   the user-facing critical path works.
 *
 * What's deferred to v1:
 * - Component-level frontend tests
 * - Visual regression
 * - Cross-browser (Firefox / Webkit)
 * - Mobile viewports (manual smoke per TEST_PLAN.md)
 * - Edge cases (empty prompts, invalid JSON edits) — covered by the
 *   backend validation tests and by manual smoke per TEST_PLAN.md
 */

// One short, deterministic prompt — keeps Claude latency predictable and
// keeps the test bill modest. Don't change to something exotic; this is
// a smoke test, not a content evaluation.
const TEST_PROMPT = "3-slide intro to recursion for beginners";

test.describe("Slidelang smoke", () => {
  test("landing page renders the prompt UI", async ({ page }) => {
    await page.goto("/");

    // The title is the strongest signal that the page loaded correctly.
    await expect(page).toHaveTitle(/Slidelang/);

    // Core UI primitives that any user needs to see to use the product.
    await expect(page.getByRole("heading", { name: "Slidelang" })).toBeVisible();
    await expect(
      page.getByPlaceholder(/intro to vector databases/i),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /generate deck/i }),
    ).toBeVisible();

    // The example prompts being present catches a class of bug where
    // the page renders but example clicks are broken.
    await expect(page.getByText(/try one of these/i)).toBeVisible();
  });

  test("generating a deck redirects to the editor with content", async ({
    page,
  }) => {
    await page.goto("/");

    // Type and submit
    await page.getByPlaceholder(/intro to vector databases/i).fill(TEST_PROMPT);
    await page.getByRole("button", { name: /generate deck/i }).click();

    // The button label changes to a counting timer during generation —
    // that's our signal the request is in flight.
    await expect(
      page.getByRole("button", { name: /generating/i }),
    ).toBeVisible({ timeout: 5_000 });

    // Generation takes 10-30s (Claude latency + cold start). We give it 45s.
    await page.waitForURL(/\/deck\/[a-z0-9-]+/, { timeout: 45_000 });

    // The deck ID badge proves we're on a real deck page.
    await expect(page.getByText(/deck: [a-z0-9-]+/i)).toBeVisible();

    // The ⚡ timer badge proves the generation timer worked end-to-end.
    // (This is our app-specific marker; absence means the timing feature
    // regressed even if the deck itself generated.)
    await expect(page.getByText(/⚡ \d+\.\d+s/)).toBeVisible({
      timeout: 5_000,
    });

    // Monaco loads asynchronously. Wait for the editor textarea to appear.
    // Monaco renders into a div with role="code" once it's ready.
    await expect(page.locator(".monaco-editor")).toBeVisible({
      timeout: 15_000,
    });

    // The preview iframe should be present. We don't load its content here —
    // that's the next test.
    await expect(page.locator('iframe[title="deck preview"]')).toBeVisible();
  });

  test("present mode renders slides from a generated deck", async ({
    page,
  }) => {
    // Generate a deck inline so this test is independent.
    await page.goto("/");
    await page.getByPlaceholder(/intro to vector databases/i).fill(TEST_PROMPT);
    await page.getByRole("button", { name: /generate deck/i }).click();
    await page.waitForURL(/\/deck\/[a-z0-9-]+/, { timeout: 45_000 });

    // Click Present
    const presentLink = page.getByRole("link", { name: /present/i });
    await expect(presentLink).toBeVisible();
    await presentLink.click();

    // We're now on /deck/<id>/present. The page is a full-screen iframe
    // sourcing /api/compile/<id>, so we have to descend into the iframe
    // to verify content.
    await page.waitForURL(/\/deck\/[a-z0-9-]+\/present/);

    const iframe = page.frameLocator('iframe[title="presentation"]');

    // reveal.js mounts a .reveal container around the slides. If this
    // appears, reveal.js initialized successfully against our compiled HTML.
    await expect(iframe.locator(".reveal")).toBeVisible({ timeout: 15_000 });

    // At least one <section> (slide) is present and visible.
    await expect(iframe.locator(".reveal .slides section").first()).toBeVisible();
  });
});
