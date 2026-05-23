# Slidelang — Product Requirements Document

**Version:** 0.1 · **Status:** v0 prototype

## Problem

Building presentations today forces a choice between WYSIWYG editors (visually inconsistent, unversionable) and AI slide generators (slick output but locked-in canvas, no edit-as-code). There is no tool where a domain expert can describe a deck in natural language, get a structured artifact they fully own, and trust the rendering because layout decisions are made by a deterministic compiler — not by an LLM picking pixels.

## Users

- **Primary:** technical communicators — engineers writing tech talks, founders writing pitch decks
- **Secondary:** teams that need branded, consistent decks compiled the same way every time

## v0 Scope (48 hours)

1. Type a natural-language prompt → receive a generated deck within ~15s
2. View the deck rendered as reveal.js in a live preview
3. Edit the underlying JSON spec in Monaco with schema-aware autocomplete
4. Edits reflect in preview within ~1s
5. Full-screen present mode with reveal.js navigation
6. Share via unguessable 8-char URL

## v0 Non-goals

User accounts; persistent storage; collaborative editing; PPTX/PDF export; custom themes beyond reveal.js built-ins; image upload (URLs only); landing page beyond the prompt.

## Success criteria

A stranger lands on the homepage, types a prompt, and presents a deck in under 90 seconds, with no visibly broken layout.

Quantitative bars across first 20 test prompts:
- ≥90% produce a deck without manual intervention
- Of failures, ≥75% auto-fixed by repair loop within 2 attempts
- p50 latency ≤12s prompt → first preview paint
- ≤1 broken slide per 50 generated slides

## Key product decisions

- **Typed JSON DSL** (not HTML/markdown) — makes editing, validation, export tractable
- **Five named layouts** — compiler owns geometry; AI picks *which*, not *where*
- **Validate-then-repair loop** — targeted feedback to Claude, not blind retry
- **No database in v0** — in-memory is fine; Redis swap is 30 minutes later

## Risks

| Risk | Mitigation |
|---|---|
| Claude returns non-JSON | Defensive fence-stripping + explicit prompt instructions |
| Layout pathologies | Semantic rules + repair loop |
| Repair runs forever | Hard cap of 2 retries with structured warnings |
| Container restart loses decks | UI banner; trivial Redis migration path |
| XSS via user content | `html.escape` in compiler + Jinja autoescape (defense in depth) |
