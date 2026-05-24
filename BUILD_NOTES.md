# Slidelang — Build Notes

A short writeup on how this got built. Submitted alongside the PRD, TDD, and demo video.

---

## What I personally built

Designed and implemented the system end to end, from architecture to deployment.

**Backend (Python 3.12 / FastAPI):**
- The deck DSL — a typed Pydantic discriminated union with 6 block types (text, bullets, image, math, code, chart) and 5 layouts (title, title_content, two_column, full_bleed, quote). Bounded fields (max 40 slides, max 6 blocks per slide, max 180 chars per bullet) baked into the schema.
- The compiler — a deliberately pure function from `Deck` model to HTML. No I/O, no clock, no randomness. Same input always produces same output. Property-tested via a determinism test.
- The validation pipeline — semantic rules that emit stable error codes (`TOO_MANY_CHARTS`, `CHART_CROWDED`, `SLIDE_OVERFLOW_RISK`, etc.) which feed back into a bounded repair loop (max 2 retries) that asks Claude to fix specific issues.
- The AI integration — system prompt with explicit authoring rules, JSON-only output contract, robust fence-stripping that handles truncated responses.
- The FastAPI routes — `/api/generate`, `/api/compile`, `/api/decks/{id}` with PATCH for live edits. Structured error responses (400/422/502) instead of generic 500s.

**Frontend (Next.js 14 / TypeScript / Tailwind):**
- The editor page — Monaco editor (the VS Code editor) on the left, live preview iframe on the right, debounced PATCH save on changes.
- The landing page — prompt input with example prompts, live countdown timer during generation.
- The present mode — full-screen iframe of the compiled deck with a faint exit affordance (corner button + `q` key shortcut). Intentionally avoids hijacking `Esc` so reveal.js's overview mode still works inside.
- Timer + repair badges — visible signals that surface what the system is doing under the hood (`⚡ 12.3s`, amber `repaired` tag).

**Test infrastructure:**
- 22 backend unit tests covering schema, compiler determinism, XSS escaping, every layout, every semantic rule, repair loop convergence, repair loop exhaustion.
- 3 Playwright E2E smoke tests covering the critical user flow (landing renders, generation redirects, present mode renders).
- GitHub Actions CI — backend pytest on every push, E2E against the live Vercel deployment on every push to main.

**Deployment:**
- Backend on Railway (Python service, root `backend/`)
- Frontend on Vercel (Next.js, root `frontend/`)
- CORS locked down to the Vercel origin only
- Got the clean URL slug `slidelang.vercel.app`

---

## What I reused

Standard industry primitives. Slidelang's value is in how the pieces compose, not in reinventing any of them.

**Python ecosystem:** FastAPI, Pydantic, Jinja2 (templates), pytest, the Anthropic SDK. Nothing exotic.

**Frontend stack:** Next.js 14 App Router, React 18, Tailwind, Monaco (VS Code's editor, made open by Microsoft), TypeScript. Off-the-shelf.

**Slide rendering:** Reveal.js for slide framework (battle-tested for ~10 years), KaTeX for math rendering, Chart.js for charts. All loaded from CDN — no custom rendering engine.

**AI:** Claude Sonnet 4.6 via the official SDK. No fine-tuning, no agents, no retrieval. Just a system prompt and structured JSON output.

**Infrastructure:** Railway and Vercel for hosting; GitHub Actions for CI. Standard PaaS choices.

What I did NOT reuse: any existing deck-as-code system (e.g. Marp, RevealJS markdown). The DSL design — discriminated union, validation rules, repair loop — is original to this project.

---

## What broke

Five real breaks over the build. Listed in order encountered.

**1. Repo started in a broken state.** Initial scaffolding had inconsistent design patterns from earlier sandbox iterations — a factory-pattern `main.py` mixed with simple-design routes, broken `__init__.py` imports referencing non-existent modules. uvicorn refused to start. Fixed by rebuilding the repo from a known-good tarball where every file's imports were walked statically before packaging.

**2. CORS preflight blocked Vercel → Railway.** After deploying, the frontend couldn't reach the backend. Setting `CORS_ORIGINS=*` looked like it should fix it but didn't — FastAPI/Starlette silently rejects the wildcard when `allow_credentials=True` because the CORS spec forbids that combination. Fixed by setting `CORS_ORIGINS` to the exact Vercel URL.

**3. Truncated Claude responses crashed the route.** For very large prompts (25-slide stress test), Claude would hit `max_tokens=8000` mid-response, cutting off JSON inside a string. The fence-stripping regex required both opening and closing fences; truncated responses had only the opening fence, so the regex didn't match and `json.loads()` raised an unhandled `JSONDecodeError`. User saw HTTP 500. Fixed by stripping fences independently (opening and closing as separate regexes), and wrapping the generation call in try/except that returns a structured HTTP 502 with an actionable error message.

**4. Mobile Present mode had no exit.** Built present mode as a pure full-screen iframe with no chrome. On mobile, with no keyboard shortcuts and no visible UI, users had no way back to the editor except the browser back button. Fixed with a faint `← Editor` button (30% opacity, full on hover) plus a `q` keyboard shortcut. Deliberately did NOT hijack `Esc` because reveal.js uses it for slide overview mode.

**5. Long text + math slides overflowed the canvas.** Discovered during demo prep: a slide with a 270-char text block stacked above a display math equation visibly clipped the math at the bottom in reveal.js's fixed 960×700 canvas. The validation pipeline caught semantic issues like crowded charts but didn't have a rule for vertical overflow. Added `SLIDE_OVERFLOW_RISK` with a height estimator that conservatively predicts per-block render height at presentation scale. Wired into the repair loop. Updated the system prompt so Claude avoids the pattern preemptively. Now visible in the demo as the amber `repaired` tag triggered by a vector-embeddings prompt.

---

## How I debugged it

Same pattern repeated for every issue: get evidence before changing anything.

**Curl before browser.** Every endpoint got hit with `curl` first to confirm the contract. Status code, response body, response time. When a bug showed up in the frontend, the first question was always "does the backend return what I expect?" — verifiable in one shell command.

**Deploy logs over guesswork.** When the 25-slide prompt returned HTTP 500 in production, the obvious answer was "Claude is being slow." The real answer was in the Railway deploy logs — a stack trace showing `json.JSONDecodeError: Expecting value`. Five seconds of log reading saved an hour of speculative refactoring.

**Reproduction before fix.** For the CORS bug, before changing anything, I ran a `curl -I -X OPTIONS` preflight against the live URL. The response showed CORS headers were actually being sent correctly — which meant the bug was on the frontend side (stale build), not the backend. Saved another hour.

**Write the failing test first.** For the overflow bug, I wrote two tests before changing the rule code: one that should fire (long text + math) and one that should not (short text + math). The first test failed at first, which told me the height estimator constants were too lenient. Tuned them, watched the test pass, then ran the rest of the suite to confirm I hadn't broken anything else.

**Static reasoning over runtime hunting.** For the import-hell bug, instead of running `uvicorn` over and over looking at error messages, I walked the import graph by hand: which modules import what, what does each `__init__.py` export, is each import statement reachable. Found three inconsistencies in 5 minutes that runtime testing would have surfaced one at a time over an hour.

**Make the system tell you it's working.** The amber `repaired` tag wasn't strictly necessary — the repair loop worked fine with no visible UI. But surfacing it visibly turned an invisible mechanic into a debuggable surface. When something looks wrong, I want to be able to see at a glance whether the repair fired or not. That visibility paid off twice during demo prep.

---

## Status at submission

- Live: https://slidelang.vercel.app (frontend), https://slidelang-production.up.railway.app (backend API)
- Backend pytest: 22/22 green
- Frontend Playwright: 3/3 green on every push to main (CI gate)
- All five bugs above: shipped fixes, verified live, regression tests where applicable
- Demo video: 3:45, includes a live repair-loop trigger

What's deferred to v1 (explicit roadmap, not oversights): comprehensive frontend E2E coverage; Anthropic provider abstraction (currently single-provider); Redis-backed deck storage (currently in-memory); image generation pipeline (image blocks render but Claude isn't prompted to use them yet); CLI tool; PPTX/PDF export.
