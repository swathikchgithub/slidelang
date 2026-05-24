# Slidelang — Technical Design Document

**Version:** 0.1 · **Companion:** [`CLAUDE.md`](../CLAUDE.md)

## System overview

Two services connected by a JSON DSL and four HTTP endpoints:

```
Next.js (Vercel) ──POST /api/generate──▶  FastAPI (Railway) ──▶ Anthropic API
                 ──GET  /api/compile/{id}──▶
                 ──PATCH /api/decks/{id}──▶
```

## The pipeline

```
prompt → Claude → raw dict → validate ──ok──▶ compile → HTML
                                  └─errors──▶ Claude repair (max 2) → revalidate
```

## Load-bearing decision

Three options considered for the deck spec:
- Claude emits HTML — impossible to validate, no determinism
- Claude emits reveal markdown — layout still unconstrained
- **Claude emits typed JSON DSL → pure compiler → HTML** ← chosen

Three invariants follow:
1. The DSL is the contract
2. The compiler is pure (no I/O, no clock, no randomness)
3. Validation runs against the spec, not the rendered HTML

## DSL highlights (`backend/app/schema/deck.py`)

- Discriminated union on `kind` for blocks: `text`, `bullets`, `image`, `math`, `code`, `chart`
- Closed enum for layouts: `title`, `title_content`, `two_column`, `full_bleed`, `quote`
- Hard caps: 40 slides, 6 blocks/slide, 8 bullets, 20 chart labels, 5 series
- Chart spec is ours, not Chart.js's — insulates from upstream version changes
- Validators emit positional errors (`bullet[2] exceeds 180 chars`) that flow to repair prompt

## Compiler (`backend/app/compiler/`)

- `compile_deck(deck) -> str` — pure, deterministic
- `primitives.py` dispatches per block kind and per layout
- Every user string passes `html.escape`
- Jinja env uses `autoescape=select_autoescape(["html", "j2", "html.j2"])` as defense in depth
- CDN-pinned: `reveal.js@5`, `katex@0.16`, `chart.js@4`

## Validation pipeline (depth area)

Two layers:
1. **Pydantic** (structural) — types, lengths, enum values, cross-field constraints
2. **Semantic rules** (`rules.py`) — layout pathologies that schema can't catch

Stable error codes: `TWO_COL_NEEDS_TWO_BLOCKS`, `FULL_BLEED_ONE_BLOCK`, `TOO_MANY_CHARTS`, `CHART_CROWDED`, `TITLE_LAYOUT_NEEDS_TITLE`, `FIRST_SLIDE_SHOULD_BE_TITLE`, `QUOTE_NEEDS_TEXT`.

Repair loop: 2 retries max. Reasoning: attempt 1 catches most fixable errors, attempt 2 catches the long tail, attempt 3 success rate is <20% — that means the prompt or schema has a deeper issue and engineering time belongs there.

If exhausted, the API returns the deck (or null) with errors as `warnings` — non-blocking, surfaced to the user.

## AI integration (`backend/app/ai/`)

- Single system prompt embeds JSON Schema verbatim + few-shot example + numbered authoring rules
- Same prompt for generation and repair; only the user message changes
- No tool use — Claude reliably produces valid JSON with this prompt shape
- Defensive `_extract_json` strips markdown fences

## HTTP surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness |
| POST | `/api/generate` | Prompt → deck |
| POST | `/api/compile` | Deck dict → HTML |
| GET | `/api/compile/{id}` | Stored deck → HTML |
| GET | `/api/decks/{id}` | Read |
| PATCH | `/api/decks/{id}` | Update (revalidated every save) |

## Frontend (`frontend/`)

Next.js 14 App Router. Three routes:
- `/` — prompt input
- `/deck/[id]` — Monaco editor + iframe preview
- `/deck/[id]/present` — full-screen iframe

Monaco gets the JSON Schema for autocomplete and inline validation. Preview iframe sources `/api/compile/{id}`; we don't compile in the browser (single source of truth). PATCH debounced at ~600ms.


## Testing

**Backend — pytest, 20 tests, all critical paths covered.**

- `tests/test_schema.py` — round-tripping and validators (7 tests)
- `tests/test_compiler.py` — determinism, XSS escaping, all five layouts, chart payload escaping, CDN asset presence (7 tests)
- `tests/test_validation.py` — every semantic rule + repair loop convergence + repair exhaustion (6 tests)

AI integration is intentionally not unit-tested. Reasoning: it's slow, network-dependent, costs real money per run, and tests of "did Claude produce reasonable output" are subjective and flaky. The contract between Claude and our pipeline is `dict → Deck.model_validate`; everything downstream of that is fully tested. We catch Claude regressions via manual smoke prompts before deploy.

**Frontend — Playwright, 3 smoke tests, gated in CI.**

- `e2e/smoke.spec.ts` — landing page renders, generation redirects to editor with timer badge, present mode renders slides via reveal.js

CI runs E2E against the live Vercel deployment on every push to `main` and on PRs (see `.github/workflows/e2e.yml`).

**Coverage philosophy:** unit-test the engineering (schema, compiler, validation), smoke-test the integration (the user-facing critical path), defer comprehensive frontend coverage to v1. The v0 frontend is mostly orchestration over the heavily-tested backend; the marginal value of e.g. component tests for Monaco interactions is low at v0 scale. The CLAUDE.md §12 testing posture documents this explicitly.

**Deferred to v1 (explicit roadmap items, not oversights):**
- Comprehensive frontend e2e (edit flow, error states, mobile viewports)
- Visual regression via Playwright `toHaveScreenshot()`
- Cross-browser (Firefox/Webkit) — chromium-only in v0
- Backend API contract tests via Playwright (currently covered by pytest at the function level)

## Deployment

Backend on Railway (root: `backend`); frontend on Vercel (root: `frontend`). Env vars: `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `CORS_ORIGINS` on backend; `NEXT_PUBLIC_API_URL` on frontend.
