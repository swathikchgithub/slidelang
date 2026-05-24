# Slidelang — Technical Design Document
Version: 0.2 · Companion: CLAUDE.md

## System overview

Two services connected by a JSON DSL and a small HTTP surface.

```
Next.js (Vercel)  ──POST /api/generate────────▶  FastAPI (Railway)  ──▶  Anthropic API
                  ──GET  /api/compile/{id}────▶
                  ──PATCH /api/decks/{id}────▶
```

The pipeline:

```
prompt → Claude → raw dict → validate ──ok──▶ compile → HTML
                                  └─errors──▶ Claude repair (max 2) → revalidate
```

## Load-bearing decision

Three options considered for the deck spec:

1. Claude emits HTML — impossible to validate, no determinism
2. Claude emits reveal.js markdown — layout still unconstrained
3. Claude emits typed JSON DSL → pure compiler → HTML ← **chosen**

Three invariants follow:

- The DSL is the contract
- The compiler is pure (no I/O, no clock, no randomness)
- Validation runs against the spec, not the rendered HTML

## DSL (`backend/app/schema/deck.py`)

- Discriminated union on `kind` for blocks: `text`, `bullets`, `image`, `math`, `code`, `chart`
- Closed enum for layouts: `title`, `title_content`, `two_column`, `full_bleed`, `quote`
- Hard caps: 40 slides, 6 blocks/slide, 8 bullets/block, 180 chars/bullet, 20 chart labels, 5 chart series
- Chart spec is ours, not Chart.js's — insulates from upstream version changes
- Validators emit positional errors (`bullet[2] exceeds 180 chars`) that flow into the repair prompt

## Compiler (`backend/app/compiler/`)

`compile_deck(deck) -> str` — pure, deterministic. Same input always produces the same output.

- `primitives.py` dispatches per block kind and per layout
- Every user string passes through `html.escape`
- Jinja env uses `autoescape=select_autoescape(["html", "j2", "html.j2"])` as defense in depth
- CDN-pinned: `reveal.js@5`, `katex@0.16`, `chart.js@4`

### Rendering primitives

- **text** / **bullets** — direct HTML with `html.escape`; `emphasis` maps to CSS classes (`normal`, `lead`, `caption`)
- **math** — LaTeX strings passed to KaTeX in the browser, rendered at slide load via the auto-render extension; display vs. inline controlled by the `display` field
- **code** — Prism-style highlighting (Prism CDN); `language` attribute passes through; content is escaped before insertion
- **chart** — declarative spec (`chart_type` + `labels` + `series`) serialized as JSON and embedded as a data attribute; Chart.js renders on slide ready. This insulates our DSL from Chart.js config drift across versions.
- **image** — `<figure>` with `src` + `alt` + optional `<figcaption>`; `src` is escaped, `alt` defaults to empty for decorative images. v0 expects Claude to provide stable URLs (e.g. Wikimedia, Unsplash); image generation is a v1 task.

## Validation and repair pipeline (depth area)

Two layers:

1. **Pydantic (structural)** — types, lengths, enum values, cross-field constraints (e.g. `series.values` length must match `labels` length)
2. **Semantic rules** (`rules.py`) — layout pathologies that schema can't catch

Stable error codes: `TWO_COL_NEEDS_TWO_BLOCKS`, `FULL_BLEED_ONE_BLOCK`, `TOO_MANY_CHARTS`, `CHART_CROWDED`, `TITLE_LAYOUT_NEEDS_TITLE`, `FIRST_SLIDE_SHOULD_BE_TITLE`, `QUOTE_NEEDS_TEXT`, `SLIDE_OVERFLOW_RISK`.

`SLIDE_OVERFLOW_RISK` runs a conservative height estimator (per-block heights at presentation scale) against reveal.js's fixed 960×700 canvas. It fires when stacked block heights exceed the ~540px usable area — typically a long text block above a math, chart, code, or image block. The repair prompt suggests shortening the text or splitting into two slides. The system prompt also warns Claude about the pattern preemptively so the repair loop is a backstop, not the primary defense.

**Repair budget: 2 retries.** Reasoning: attempt 1 catches most fixable errors; attempt 2 catches the long tail; attempt 3 success rate is empirically <20%, which means the prompt or schema has a deeper issue and engineering time belongs there rather than on more retries.

If the repair budget is exhausted, the API returns the deck (or `null`) with errors as warnings — non-blocking, surfaced to the user via the `warnings` field and the amber `repaired` badge in the editor.

## AI integration (`backend/app/ai/`)

Planning flow from prompt to deck spec:

1. User prompt arrives at `POST /api/generate`
2. System prompt embeds the JSON Schema (exported from Pydantic via `model_json_schema()`), a few-shot example, and 8 numbered authoring rules covering layout selection, density, overflow risk, and tone
3. Claude returns a single JSON object — no narration, no markdown wrapper (though we defensively strip fences in case)
4. Output is parsed via `Deck.model_validate`; structural failures fall to the repair loop with positional Pydantic errors as inputs
5. Repair calls reuse the same system prompt but prepend a structured error list with stable codes and per-slide locations
6. Same prompt, same model — only the user message changes — keeps the contract stable

No tool use (Claude reliably produces valid JSON with this prompt shape). No streaming (we need the full response to validate before responding). No multi-turn for generation; repair is the only multi-turn path. `_extract_json` defensively strips opening and closing markdown fences independently to handle responses truncated by `max_tokens`.

## HTTP surface

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/api/health` | Liveness |
| POST   | `/api/generate` | Prompt → deck |
| POST   | `/api/compile` | Deck dict → HTML |
| GET    | `/api/compile/{id}` | Stored deck → HTML |
| GET    | `/api/decks/{id}` | Read deck JSON |
| PATCH  | `/api/decks/{id}` | Update (revalidated every save) |

`POST /api/generate` returns `{deck_id, deck, repaired, attempts, warnings}`. Errors return structured detail: HTTP 400 for bad input (empty/too-long prompt), 422 for un-repairable validation failures, 502 for malformed AI output, 500 only for truly unexpected exceptions.

## Frontend (`frontend/`)

Next.js 14 App Router. Three routes:

- `/` — prompt input + example prompts
- `/deck/[id]` — Monaco editor + iframe preview side by side
- `/deck/[id]/present` — full-screen iframe

Monaco gets the JSON Schema for autocomplete and inline validation. Preview iframe sources `/api/compile/{id}`; we don't compile in the browser, keeping a single source of truth on the server.

### Editor state model

- **Initial load:** `GET /api/decks/{id}` → parse JSON → Monaco model
- **User edit:** Monaco emits `onDidChangeModelContent` → debounce 600ms → `PATCH /api/decks/{id}` with the full JSON body
- **Server response:** revalidated deck (with any new warnings) → updates the preview iframe's `src` with a cache-busting query param to force reload
- **Failure mode:** `PATCH` 400/422 → error banner with the validation message; user fixes the JSON; preview iframe stays on last-good render
- **No client-side validation** — we don't duplicate Pydantic rules in TypeScript; one source of truth lives on the server
- **No optimistic UI** — preview only updates after server confirms; trades ~700ms of latency for consistency

## Publishing flow

Every successful generation creates a stable deck ID (8-char UUID prefix) that produces three public URLs:

- `/deck/{id}` — editor view
- `/deck/{id}/present` — full-screen reveal.js
- `/api/compile/{id}` — raw HTML, embeddable anywhere

Anyone with the deck ID can view (no auth in v0 — decks are public by construction; auth/privacy is a v1 concern). The compile endpoint serves `text/html` with no API auth, making it trivially embeddable in an iframe or shared by URL. Decks persist in-memory; v1 swaps to Redis or Postgres for durability across container restarts.

## CLI and agent integration

The HTTP API is the integration surface. `POST /api/generate` is callable from anything — curl, Python, a CLI, an agent framework, a Slack bot. v1 will ship a thin CLI wrapper (`slidelang gen "5 slides on X"` → deck URL) and a webhook for agents to subscribe to generation completion. The architecture intentionally treats the browser editor as one client among many.

## Testing

**Backend — pytest, 22 tests, all critical paths covered.**

- `tests/test_schema.py` — round-tripping and validators (7 tests)
- `tests/test_compiler.py` — determinism, XSS escaping, all five layouts, chart payload escaping, CDN asset presence (7 tests)
- `tests/test_validation.py` — every semantic rule including `SLIDE_OVERFLOW_RISK` (positive and negative cases), repair loop convergence, repair exhaustion (8 tests)

AI integration is intentionally not unit-tested. Reasoning: it's slow, network-dependent, costs real money per run, and tests of "did Claude produce reasonable output" are subjective and flaky. The contract between Claude and our pipeline is `dict → Deck.model_validate`; everything downstream of that is fully tested. We catch Claude regressions via manual smoke prompts before deploy.

**Frontend — Playwright, 3 smoke tests, gated in CI.**

- `e2e/smoke.spec.ts` — landing page renders, generation redirects to editor with timer badge, present mode renders slides via reveal.js

CI runs E2E against the live Vercel deployment on every push to `main` and on PRs (see `.github/workflows/e2e.yml`).

**Coverage philosophy:** unit-test the engineering (schema, compiler, validation), smoke-test the integration (the user-facing critical path), defer comprehensive frontend coverage to v1. The v0 frontend is mostly orchestration over the heavily-tested backend; the marginal value of e.g. component tests for Monaco interactions is low at v0 scale. `CLAUDE.md` §12 testing posture documents this explicitly.

**Deferred to v1** (explicit roadmap items, not oversights):

- Comprehensive frontend e2e (edit flow, error states, mobile viewports)
- Visual regression via Playwright `toHaveScreenshot()`
- Cross-browser (Firefox/Webkit) — chromium-only in v0
- Backend API contract tests via Playwright (currently covered by pytest at the function level)

## Deployment

Backend on Railway (root: `backend`); frontend on Vercel (root: `frontend`). Required env vars: `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CORS_ORIGINS` on backend; `NEXT_PUBLIC_API_URL` on frontend. CORS is locked to the Vercel origin. CI runs backend pytest and frontend Playwright on every push to `main` — broken commits are caught before they reach the live URL.
