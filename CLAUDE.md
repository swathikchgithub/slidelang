# CLAUDE.md — Slidelang Engineering Guide

**Audience:** Claude Code sessions and human contributors working in this repo.
**Scope:** Architectural intent, invariants, and the rules of engagement.
**Read this before changing anything outside of comments.**

---

## 1. What Slidelang is, in one sentence

A deck-as-code authoring platform where a user's natural-language prompt is translated by Claude into a typed JSON deck spec, deterministically compiled to reveal.js HTML, and presented in the browser — with a validation/repair pipeline that catches both structural and semantic layout errors before they reach the user.

## 2. The three things that must stay true

These are invariants. Breaking any of them is a redesign, not a refactor.

1. **The DSL is the contract.** Claude produces JSON conforming to `app/schema/deck.py`. The compiler consumes the same shape. The frontend editor edits the same shape. If you're tempted to add a "rich text" string with embedded HTML to slip past the schema — don't. Extend the schema instead.

2. **The compiler is pure.** `compile_deck(deck: Deck) -> str` takes a validated `Deck` and returns an HTML string. No network, no clock, no random IDs generated inside, no environment lookups. Same input → same output, always. This is what makes the system testable and what makes a future PPTX exporter feasible.

3. **Validation runs against the spec, not the rendered HTML.** We do not parse HTML to detect overlapping text. We detect the conditions that *cause* overlapping text in the spec — too many blocks, wrong layout, oversized content — and refuse or repair the spec before compilation.

If a change you're considering breaks one of these, stop and discuss before writing code.

## 3. The system shape

```
[user prompt]
     ↓
[Claude: generate_deck]       ←─── system prompt embeds JSON Schema
     ↓
[raw dict]
     ↓
[validation pipeline]         ←─── pydantic (structural) + rules.py (semantic)
     ↓ (errors)                    ↑
     ↓                             │
[Claude: repair_deck] ─────────────┘  (bounded retries, max 2)
     ↓
[validated Deck]
     ↓
[compiler]                    ←─── pure function, deterministic
     ↓
[reveal.js HTML]
     ↓
[browser preview / present]
```

Four HTTP endpoints connect the halves: `POST /api/generate`, `POST /api/compile`, `GET /api/compile/{id}`, `GET|PATCH /api/decks/{id}`.

## 4. Directory map and where to make changes

```
backend/app/
├── schema/          → CHANGE HERE FIRST when adding block types, layouts, or fields
├── compiler/        → CHANGE HERE SECOND to render the new shape to HTML
├── validation/      → CHANGE HERE THIRD to add semantic rules
├── ai/              → System prompt + few-shot examples; touch when changing DSL
├── routes/          → HTTP surface; rarely needs changes
└── storage/         → In-memory v0; swap to Redis when persistence matters
```

The order matters. If you add a `VideoBlock` to compiler before schema, pydantic will reject every deck containing it, and you'll waste an hour wondering why.

## 5. The DSL extension protocol

To add a new block type or layout, do these in order:

1. Add the pydantic model in `schema/deck.py`. Include `kind: Literal["..."]` for the union, hard caps on string lengths, and a `field_validator` for any constraint that depends on other fields.
2. Add the renderer in `compiler/primitives.py`. Add the `isinstance` branch in `render_block` or the enum branch in `render_layout`. Renderers escape every user string with `html.escape` — no exceptions.
3. Add semantic rules in `validation/rules.py` for layout pathologies the new type enables. Each rule returns a `ValidationError` with a stable `code`.
4. Regenerate `schema/deck.schema.json` via `python -m app.schema.export_schema`. The system prompt loads from this file.
5. Update the few-shot example in `ai/prompts.py` to demonstrate the new type if it's a common case.
6. Add unit tests in `tests/test_schema.py` (validation), `tests/test_compiler.py` (rendering), and `tests/test_validation.py` (semantic rules).
7. Regenerate the frontend types: `npx json-schema-to-typescript backend/app/schema/deck.schema.json -o frontend/lib/types.ts`.

Skipping step 4 is the most common cause of "Claude keeps producing the old schema."

## 6. Prompting Claude — the rules

The system prompt in `ai/prompts.py` is load-bearing. Treat it like production code, not config.

- **One prompt for generation and repair.** They differ only in the user message. Don't add a second prompt template; you'll drift.
- **The JSON Schema is in the prompt verbatim.** Not a summary. The full thing. Claude is good at constraining output to a schema when it can see the schema.
- **Few-shot example must use real syntax**, including escaped LaTeX backslashes. Test it: copy the example output, parse it with `Deck.model_validate(...)`. If that fails, the prompt is teaching Claude to produce invalid decks.
- **Authoring rules are numbered and short.** Long paragraphs get partially ignored. Each rule is one line and addresses one failure mode you actually observed.
- **No prose, no fences, no commentary** is repeated in the system prompt for a reason. Claude still occasionally wraps output in ` ```json `. `_extract_json` defends against this, but the prompt should keep telling it not to.

When repair fails twice in a row on the same kind of error, the right fix is usually not "raise max attempts to 3" — it's "add an authoring rule that prevents the error in the first place."

## 7. The validation/repair loop

`validate_with_repair` in `validation/pipeline.py` is bounded. Two repair attempts max. The reasoning:

- Most fixable errors fix on attempt 1.
- If attempt 2 fails, attempt 3 almost never succeeds — the prompt or schema has a deeper issue.
- Each attempt is a Claude API call. Three attempts on a 40-slide deck is several seconds of latency and a non-trivial token bill.

If you increase the cap, instrument the success rate of attempt 3 first. If it's below 20%, the cap should stay at 2 and the engineering time should go into the prompt.

`ValidationError.code` is a stable identifier. Don't rename codes without grepping for callers — the frontend may eventually use them to render targeted UI hints ("This slide has too many charts — split it?").

## 8. The compiler — security and correctness

- **Every user-controlled string passes through `html.escape`.** Yes, even alt text. Yes, even chart series names. Especially LaTeX content (KaTeX handles its own parsing but we escape the HTML containers).
- **Chart configs are emitted as JSON inside a `data-` attribute, then parsed in the browser.** This avoids inline `<script>` tags with user data — defense in depth even though the JSON path is also escaped.
- **The reveal.js shell uses CDN-pinned versions** (`reveal.js@5`, `katex@0.16`, `chart.js@4`). Don't switch to `@latest` — that's how decks render fine today and break in three months.

## 9. Frontend conventions

- **Types come from the backend schema.** Run the `json-schema-to-typescript` step in CI or as a pre-commit hook. Manual TypeScript that "mirrors" the pydantic models will drift within a week.
- **The preview iframe sources the backend compile endpoint**, it does not compile in the browser. The compiler is in Python on purpose — single source of truth, easier to test, no React-rendering-LaTeX-rendering-Chart.js race conditions.
- **Monaco gets the JSON Schema** for editor-side validation. This is half the editing UX for free.
- **Debounce PATCHes** at ~500ms. Every keystroke is not a request.

## 10. Things deliberately not in v0

If a contributor proposes any of these for the 48-hour build, push back:

- A database. In-memory storage is fine for the demo; Railway restarts can be handled with a banner.
- User accounts. Decks have unguessable 8-char IDs; that's enough for demo sharing.
- Server-side PPTX/PDF export. The clean DSL means this is straightforward later, but it's a day of work and it's not on the critical path.
- Real-time collaborative editing. Different product.
- A "themes" system beyond reveal.js built-in themes. The theme enum has four values for a reason — each one is tested.
- Streaming Claude responses to the editor. Cute, but the validation pipeline needs the full deck. Stream the *status* (generating → repairing → done) instead.

## 11. Common failure modes and what to do

- **"Claude returned non-JSON"** — Almost always a markdown fence. `_extract_json` should catch it. If it doesn't, the model produced prose; check the prompt for ambiguity.
- **"Pydantic ValidationError on `slides.0.blocks.2.items.4`"** — A bullet too long. The repair loop should fix this. If it doesn't on attempt 2, the bullet content is genuinely unsplittable and the prompt should be told to summarize instead.
- **"Compiled HTML looks empty"** — Check the Jinja template autoescape isn't double-escaping pre-rendered block HTML. We use `| safe` for the `slides_html` list because the renderers already escaped user content.
- **"Chart doesn't render"** — Open browser devtools. 95% of the time it's a JSON parse error in the `data-chart-config` attribute because something didn't get escaped. The other 5% is Chart.js version mismatch on the CDN.
- **"KaTeX shows raw LaTeX"** — The auto-render delimiters in the template must match the delimiters the compiler emits (`$$...$$` for display, `\(...\)` for inline). Don't change one without the other.

## 12. Testing posture

- `tests/test_schema.py` — every block type round-trips through `model_validate`/`model_dump`.
- `tests/test_compiler.py` — `compile_deck(fixture) == golden_html` for at least one deck per layout.
- `tests/test_validation.py` — every rule in `rules.py` has a positive case (rule fires) and a negative case (rule doesn't fire on good input).
- AI integration is *not* covered by unit tests. It's covered by a `scripts/smoke_generate.py` that you run manually before deploys with ~5 varied prompts.

## 13. When you're stuck

Read this file. Then read `app/schema/deck.py`. Then read `app/compiler/compile.py`. In that order. 80% of confusion about Slidelang comes from forgetting which layer owns which concern.

---

*Last updated: initial build. Bump this when the architecture changes, not when you fix a typo.*
