# Slidelang frontend

Next.js 14 (App Router), TypeScript, Tailwind CSS.

## Develop

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

The backend must be reachable at the URL in `.env.local` (`NEXT_PUBLIC_API_URL`).

## E2E smoke tests

Three Playwright smoke tests cover the critical user flow:

1. Landing page renders correctly
2. Generation flow: prompt → redirect to editor → Monaco loads → timer badge appears
3. Present mode: rendered slides visible in the reveal.js iframe

```bash
# Against local dev server (must be running on :3000)
npm run dev   # in another terminal
npm run test:e2e

# Against the live deployment
BASE_URL=https://slidelang.vercel.app npm run test:e2e

# Interactive UI mode (great for debugging)
npm run test:e2e:ui
```

CI runs these on every push to `main` against the live Vercel URL — see `.github/workflows/e2e.yml`.

## Test coverage policy

- **Smoke tests only** in v0 — three Playwright tests covering the critical user flow.
- **Comprehensive E2E coverage deferred to v1** — explicit roadmap item, not an oversight. The backend has full pytest coverage of the engineering (schema, compiler, validation, repair loop); the frontend is mostly orchestration over those.

## Build

```bash
npm run build
```

Vercel runs this automatically on push to `main`.
