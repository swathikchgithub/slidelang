# Slidelang — Product Requirements Document
Version: 0.2 · Status: v0 prototype

## The wedge

Slidelang starts as **a tool for technical decks that get built repeatedly** — pitch decks, design reviews, postmortems, internal product reviews — and expands into a broader deck authoring platform built on a single insight: **the deck spec is the artifact, not the rendered slides.**

The wedge order:

1. **v0 — Single-prompt deck generation.** Solo founders writing pitch decks, engineers writing tech talks. They want a deck in 15 seconds and the ability to edit one line of JSON to fix the title without breaking the layout.
2. **v1 — Branded recurring decks.** Teams that ship the same kind of deck repeatedly (weekly business reviews, customer QBRs, on-call retros) — same structure, different data each time. Slidelang's typed spec is exactly the contract these teams need.
3. **v2 — Programmatic authoring.** CLI + webhook + plugin ecosystem so agents, internal tools, and CI pipelines can generate decks the same way they generate documents or dashboards.

Each step uses the same compiler and the same DSL. The platform compounds — every new feature applies to every deck type.

## Why structured authoring beats prompt-to-static slides

Today's authoring tools force a binary choice:

- **WYSIWYG editors (PowerPoint, Keynote, Google Slides, Gamma, Beautiful.AI)** — output looks polished but is unversionable, programmatically inaccessible, and visually inconsistent across authors. Layout decisions are baked into pixels; you can't grep them, you can't diff them, you can't ask the AI to rewrite "just the chart slide."
- **Prompt-to-HTML AI tools** — generate decks quickly but produce one-shot artifacts. The output is brittle: re-running the prompt produces something different, edits are textual hacks against generated HTML, and there's no structural contract to validate against.

Slidelang takes a third path: **Claude produces a typed JSON deck spec, and a deterministic compiler renders it.** This is strictly better than either alternative on four dimensions:

| Dimension | WYSIWYG | Prompt-to-HTML | Slidelang |
|---|---|---|---|
| Editable by humans | Yes (visually) | No (HTML is fragile) | Yes (JSON or visually via re-prompt) |
| Editable by agents | No | No | Yes (structured spec) |
| Versionable / diffable | No | Theoretically | Yes (it's just JSON) |
| Layout is consistent | Depends on author | No | Yes (compiler-owned) |
| Validation possible | No | No | Yes (against the spec) |

The typed spec is the contract. Every other product property follows from it.

## What makes the generated deck trustworthy and editable

Trustworthy and editable aren't aesthetic claims — they're specific engineering properties.

### Trustworthy means three things

1. **The output is reproducible.** The compiler is a pure function: same JSON spec, same HTML output, byte-for-byte. No clock, no randomness, no I/O. Property-tested.
2. **Layout pathologies are caught before the user sees them.** A bounded validation pipeline runs after Claude returns and before the deck reaches the user. Stable error codes (`TOO_MANY_CHARTS`, `SLIDE_OVERFLOW_RISK`, `CHART_CROWDED`, etc.) flag issues. A bounded repair loop (max 2 retries) feeds those codes back to Claude, which fixes specific issues rather than starting over. When the repair fires, the editor surfaces an amber `repaired` badge so the user knows what happened.
3. **User content can't break the renderer.** Every user-supplied string passes through `html.escape` plus Jinja autoescape — defense in depth. Tested with adversarial fixtures.

### Editable means three things

1. **The spec is human-readable JSON.** Monaco editor with the JSON schema gives autocomplete, type hints, and inline validation. Anyone who can read JSON can edit a slide.
2. **Edits round-trip cleanly.** The PATCH endpoint validates every save; if the user breaks the JSON, they get a structured error message; the last-good render stays in the preview pane.
3. **Edits don't break the layout.** Because the compiler — not the editor — owns geometry, you can't accidentally move a chart off the slide by typing in the wrong place. The compiler will lay it out correctly regardless.

## Target users

**Primary (v0):** technical communicators who think in structure — engineers writing conference talks, founders writing pitch decks, solo developers writing portfolio walkthroughs. They want speed and editability. They tolerate (or prefer) editing JSON.

**Secondary (v1):** teams that ship recurring decks — sales engineers writing customer-specific deep-dives, ops teams writing weekly business reviews, on-call engineers writing postmortems. They want the same template-with-fresh-data flow that already exists for docs but doesn't exist for slides.

**v2 expansion:** anyone whose pipeline produces structured data that should also produce a deck — CI summaries, dashboard exports, agent task results.

## Workflow (v0)

```
1. Visit https://slidelang.vercel.app
2. Type a prompt: "3 slides explaining vector embeddings with the cosine similarity formula"
3. Hit generate. ~12 seconds, timer counts up.
4. Land on the editor: Monaco JSON on the left, live preview iframe on the right
5. (Optional) Edit the JSON; preview updates within ~1 second
6. Click Present. Full-screen reveal.js, arrow keys to navigate, Q to exit.
7. Share the URL with anyone (no auth required in v0).
```

## v0 scope (48-hour build)

- Prompt → generated deck within ~15s
- Reveal.js preview rendering
- Monaco editor with schema-aware autocomplete and inline validation
- Edits round-trip to preview within ~1s
- Full-screen present mode
- Public deck URLs (unguessable 8-char IDs)
- Validation + bounded repair loop with stable error codes
- 6 block types: text, bullets, image, math, code, chart
- 5 layouts: title, title_content, two_column, full_bleed, quote

## v0 non-goals

User accounts; persistent storage; collaborative editing; PPTX/PDF export; custom themes beyond reveal.js built-ins; image upload (URLs only); branded recurring-deck templates (v1).

## Success criteria

A stranger lands on the homepage, types a prompt, and presents a deck in under 90 seconds with no visibly broken layout.

Quantitative bars across the first 20 test prompts:

- ≥90% produce a deck without manual intervention
- Of failures, ≥75% auto-fixed by repair loop within 2 attempts
- p50 latency ≤12s prompt → first preview paint
- ≤1 broken slide per 50 generated slides

## Key product decisions

| Decision | Why |
|---|---|
| Typed JSON DSL (not HTML/markdown) | Makes editing, validation, export, and agent integration tractable |
| Five named layouts | Compiler owns geometry; AI picks which, not where |
| Validate-then-repair loop, not blind retry | Targeted feedback to Claude with stable error codes; cheaper, faster, more reliable |
| No database in v0 | In-memory is fine; Redis swap is 30 minutes later |
| Server-side validation only | Single source of truth; no duplicated Pydantic rules in TypeScript |
| Public-by-URL in v0 | Sharing is the primary distribution mechanism; auth is a v1 concern |

## Risks

| Risk | Mitigation |
|---|---|
| Claude returns malformed JSON | Defensive fence-stripping handles truncated responses; structured 502 with actionable error if unrecoverable |
| Layout pathologies (overcrowded, overflow) | Semantic validation rules + bounded repair loop |
| Repair runs forever | Hard cap of 2 retries; warnings surfaced as non-blocking |
| Container restart loses decks | UI banner about ephemerality; trivial Redis/Postgres migration path |
| XSS via user content | `html.escape` in compiler + Jinja autoescape (defense in depth); tested with adversarial fixtures |
| Pathological prompts (25+ slides with charts on every slide) | 1000-char prompt cap; structured 502 with retry guidance if Claude still fails |

## v1 and beyond

The platform compounds because every feature works against the same DSL:

- **Branded recurring decks** — named templates (e.g. `weekly-business-review`) that lock in structure and theming; users supply only the data
- **Provider abstraction** — Claude + OpenRouter + Gemini behind one interface for cost/latency tradeoffs
- **CLI + agent integration** — `slidelang gen "..."` from the terminal; webhook on generation complete for agent pipelines
- **PPTX / PDF export** — the compiler already turns specs into HTML; a second compiler target produces native formats
- **Persistent storage** — Redis for hot decks, Postgres for archive
- **Auth + workspaces** — private decks, team sharing, audit logs
- **Image generation** — Claude block prompts → image generation API → image URL → image block
- **Visual editor mode** — for users who don't want to edit JSON; constrained to the same DSL via form-based editing
