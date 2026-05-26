# Slidelang E2E — Setup Instructions

Follow these steps in order. Total time: ~30 minutes (mostly waiting for `npm install`).

## Files in this delivery

1. `playwright.config.ts` → goes to `frontend/playwright.config.ts`
2. `smoke.spec.ts` → goes to `frontend/e2e/smoke.spec.ts`
3. `e2e.yml` → goes to `.github/workflows/e2e.yml`
4. `frontend_README.md` → goes to `frontend/README.md` (new file)

---

## Step 1 — Install Playwright in the frontend

```bash
cd /Users/swathikchpro/git/slidelang/frontend
npm install --save-dev @playwright/test
npx playwright install --with-deps chromium
```

The `npm install` adds Playwright as a dev dependency.
The `playwright install` downloads the browser binary (~150 MB, one-time).

## Step 2 — Add npm scripts

Open `frontend/package.json`. Find the `"scripts"` block:

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint"
}
```

Replace with:

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint",
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui",
  "test:e2e:headed": "playwright test --headed"
}
```

Save.

## Step 3 — Drop in the test files

Create the directory and copy the files:

```bash
cd /Users/swathikchpro/git/slidelang/frontend
mkdir -p e2e

# Copy the four delivered files into their final locations:
# Adjust ~/Downloads/ if you saved them elsewhere
cp ~/Downloads/playwright.config.ts .
cp ~/Downloads/smoke.spec.ts e2e/
cp ~/Downloads/frontend_README.md README.md

cd /Users/swathikchpro/git/slidelang
cp ~/Downloads/e2e.yml .github/workflows/
```

## Step 4 — Add Playwright artifacts to .gitignore

Open `/Users/swathikchpro/git/slidelang/.gitignore` and add these lines if not already there:

```
# Playwright
/frontend/test-results/
/frontend/playwright-report/
/frontend/playwright/.cache/
```

## Step 5 — Run the tests locally (the moment of truth)

Two terminals.

**Terminal 1 — Start the local frontend:**
```bash
cd /Users/swathikchpro/git/slidelang/frontend
npm run dev
```

Note: your `.env.local` must point at a running backend. Either:
- Start the local backend too (`cd ../backend && source .venv/bin/activate && uvicorn app.main:app --port 8000`), OR
- Temporarily point at production: `echo 'NEXT_PUBLIC_API_URL=https://slidelang-production.up.railway.app' > .env.local` then `npm run dev`

**Terminal 2 — Run Playwright:**
```bash
cd /Users/swathikchpro/git/slidelang/frontend
npm run test:e2e
```

You should see:
- "Running 3 tests using 1 worker"
- Each test passes (✓)
- Total time ~60-90 seconds

If any test fails, run with the UI for debugging:
```bash
npm run test:e2e:ui
```

That opens a browser where you can see exactly what Playwright sees.

## Step 6 — Run against live deployment

```bash
BASE_URL=https://slidelang.vercel.app npm run test:e2e
```

This is what CI does. Make sure it passes.

## Step 7 — Commit and push

```bash
cd /Users/swathikchpro/git/slidelang
git add frontend/playwright.config.ts \
        frontend/e2e/smoke.spec.ts \
        frontend/README.md \
        frontend/package.json \
        frontend/package-lock.json \
        .github/workflows/e2e.yml \
        .gitignore

git commit -m "Add Playwright smoke tests + CI workflow

Three smoke tests covering the critical user flow:
- Landing page renders prompt UI
- Generation redirects to editor with content + timer badge
- Present mode renders slides via reveal.js iframe

CI runs against live Vercel deployment on every push.
Comprehensive frontend coverage deferred to v1 (documented in TDD)."

git push
```

GitHub Actions will trigger the workflow. Visit your repo's Actions tab to watch it run.

---

## Common stumbles

### "Browser binary not found"
You skipped `npx playwright install --with-deps chromium`. Run it.

### "ECONNREFUSED localhost:3000"
The dev server isn't running. Start it in another terminal first.

### "Timeout waiting for URL /deck/..."
The backend isn't responding. Check that `.env.local` points to a reachable URL and that the backend is healthy (`curl <api>/api/health`).

### "Cannot find element .monaco-editor"
Monaco loads slowly. If this fails intermittently, the test's 15s timeout might not be enough on a slow network — bump it to 20-25s in `smoke.spec.ts`.

### CI fails but local passes
Most likely the live URL isn't responsive when the workflow runs (Vercel deploy still propagating). The workflow has a 30s sleep, but on slow days bump it to 60s.

---

## What you can claim now

After step 7 commits and the CI run goes green:

- ✅ Playwright E2E tests in your repo
- ✅ CI gate on every push
- ✅ Tests run against the live deployment, not localhost
- ✅ Coverage policy explicitly documented in TDD and frontend README
- ✅ Comprehensive coverage deferred to v1 with rationale

Talking points for interviews:
"I have backend unit tests covering the schema, compiler, and validation pipeline — that's where regressions would break correctness. The frontend has Playwright smoke tests covering the critical user flow, gated in CI on every push. Comprehensive frontend coverage is in my v1 backlog because the v0 frontend is mostly orchestration over the heavily-tested backend."
