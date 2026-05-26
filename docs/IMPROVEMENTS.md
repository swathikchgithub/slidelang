# Slidelang — Improvements & Bug Tracker

Issues identified during code review. Each item includes severity, location, description, and fix status.

---

## 🔴 High Priority

### BUG-001 — LaTeX XSS via MathBlock
**File:** `backend/app/schema/deck.py`, `backend/app/compiler/primitives.py`  
**Severity:** High — Security  
**Status:** ✅ Fixed

**Problem:** `MathBlock.latex` is written into HTML without escaping (`_math()` in `primitives.py`). The Jinja2 template uses `{{ slide_html | safe }}`, so raw HTML embedded in a LaTeX string is injected into the DOM. An attacker can submit `\text{<script>alert(1)</script>}` and execute arbitrary JavaScript.

**Fix:** Added `field_validator` on `MathBlock.latex` that rejects any value containing `<` or `>`. LaTeX does not use these characters; their presence always indicates injection.

---

### BUG-002 — Unbounded in-memory store, data lost on restart
**File:** `backend/app/storage/memory.py`  
**Severity:** High — Reliability  
**Status:** ✅ Fixed

**Problem:** `_STORE` is a plain module-level `dict`. It grows without bound (memory leak) and wipes on every process restart (data loss). No Redis backend was wired despite the docstring's note that Redis should replace this.

**Fix:**
- Replaced plain `dict` with `OrderedDict` capped at `MAX_STORE_SIZE = 500` entries; oldest entry evicted when the cap is hit.
- Made `save_deck` / `get_deck` `async` to support non-blocking I/O backends.
- Added optional Redis backend: if `REDIS_URL` is set in env, decks are stored in Redis with a 24-hour TTL and survive restarts.
- Removed unused `list_deck_ids()` export (see IMP-010).
- Added `redis[asyncio]` as an optional dependency in `pyproject.toml`.

---

### BUG-003 — No rate limiting on POST /api/generate
**File:** `backend/app/routes/generate.py`  
**Severity:** High — Cost / Abuse  
**Status:** ✅ Fixed

**Problem:** `POST /api/generate` calls the Claude API with no per-IP or per-user rate limit. A single client can exhaust the Anthropic quota or rack up unbounded cost.

**Fix:** Added an in-memory sliding-window rate limiter (10 requests per minute per client IP) in `generate.py`. Returns `429` with a structured error body when the limit is exceeded.

---

### BUG-004 — Outdated Claude model in config
**File:** `backend/app/config.py`  
**Severity:** High — Correctness  
**Status:** ✅ Fixed

**Problem:** `CLAUDE_MODEL` defaulted to `"claude-sonnet-4-5"`, a previous-generation model. The current production model is `"claude-sonnet-4-6"`.

**Fix:** Updated default to `"claude-sonnet-4-6"`.

---

## 🟡 Medium Priority

### IMP-005 — Frontend swallows structured API errors
**File:** `frontend/lib/api.ts`  
**Severity:** Medium — Developer / User Experience  
**Status:** ✅ Fixed

**Problem:** On non-2xx responses, `generateDeck()` and `updateDeck()` do `res.text()` and throw a raw string. FastAPI returns structured `{"detail": {...}}` bodies; callers see `"generate failed: 422 {"detail": {"message": "…", "error_type": "…"}}"` instead of the human-readable message.

**Fix:** Parse the response body as JSON first; extract `detail.message` when present, fall back to raw text otherwise.

---

### IMP-006 — CORS too permissive
**File:** `backend/app/main.py`  
**Severity:** Medium — Security  
**Status:** ✅ Fixed

**Problem:** `allow_methods=["*"]` and `allow_headers=["*"]` permit any HTTP method and header from any allowed origin. This is wider than necessary and violates the principle of least privilege.

**Fix:** Restricted to `allow_methods=["GET", "POST", "PATCH"]` and `allow_headers=["Content-Type"]`, which covers all routes currently in use.

---

### IMP-007 — POST /api/compile skips semantic validation
**File:** `backend/app/routes/compile.py`  
**Severity:** Medium — Correctness  
**Status:** ✅ Fixed

**Problem:** `POST /api/compile` validates the Pydantic schema but does not run `validate_semantic()`. A deck that fails semantic rules (e.g., `two_column` with one block, overflow risk) compiles silently to broken HTML instead of returning a descriptive error.

**Fix:** Added `validate_semantic()` call after `Deck.model_validate()`; returns `422` with the list of semantic errors if any are found.

---

### IMP-008 — No loading state on deck page initial fetch
**File:** `frontend/app/deck/[id]/page.tsx`  
**Severity:** Medium — UX  
**Status:** ✅ Fixed

**Problem:** When navigating to `/deck/[id]`, `fetchDeck()` is called but the editor renders immediately with an empty string. The user sees a blank Monaco editor with no indication that data is loading.

**Fix:** Added `loading` state; renders a centered spinner while the initial fetch is in flight.

---

### IMP-009 — sessionStorage timing data never cleaned up
**File:** `frontend/app/deck/[id]/page.tsx`  
**Severity:** Medium — Resource Leak  
**Status:** ✅ Fixed

**Problem:** The landing page stashes generation timing in `sessionStorage` under `slidelang:timing:{deckId}`. The deck page reads it but never removes it, leaving stale entries accumulating for every deck ever generated in the session.

**Fix:** Call `sessionStorage.removeItem(...)` immediately after successfully reading the timing data.

---

### IMP-010 — Dead export: `list_deck_ids`
**File:** `backend/app/storage/memory.py`  
**Severity:** Medium — Code Quality  
**Status:** ✅ Fixed (removed as part of BUG-002)

**Problem:** `list_deck_ids()` is exported but never imported or called anywhere in the codebase. It creates a false impression of a listing API that doesn't exist.

**Fix:** Removed the function.

---

## 🟢 Minor

### IMP-011 — User prompt not isolated from system instructions
**File:** `backend/app/ai/prompts.py`  
**Severity:** Minor — Security / Prompt Injection  
**Status:** ✅ Fixed

**Problem:** `build_generation_message()` concatenates the raw user prompt with no delimiter: `f"Create a deck for this request:\n\n{user_prompt}"`. A user can write "Ignore previous instructions…" and the boundary between instruction and data is unclear to the model.

**Fix:** Wrapped the user prompt in `<user_request>…</user_request>` tags and updated the instruction text to treat content inside those tags as data only.

---

### IMP-012 — Repair uses same token budget as generation
**File:** `backend/app/ai/generator.py`  
**Severity:** Minor — Correctness  
**Status:** ✅ Fixed

**Problem:** `repair_deck()` uses `MAX_TOKENS = 8000`, the same budget as initial generation. Repair prompts include the full broken deck plus the error list, so they consume more input tokens. Using the same output token budget risks truncating the corrected deck.

**Fix:** Added `MAX_REPAIR_TOKENS = 12000` used exclusively by `repair_deck()`.

---

### IMP-013 — PATCH /api/decks/{id} leaks raw Pydantic error string
**File:** `backend/app/routes/decks.py`  
**Severity:** Minor — API Contract  
**Status:** ✅ Fixed

**Problem:** `raise HTTPException(400, f"invalid deck: {e}")` serialises the entire Pydantic `ValidationError` as a plain string. Callers receive an unstructured blob rather than machine-readable error data.

**Fix:** Catches `PydanticError` specifically, formats `e.errors()` as a list, and returns `{"message": "…", "errors": [...]}`.

---

### IMP-014 — JSON syntax errors look identical to API errors in the editor
**File:** `frontend/app/deck/[id]/page.tsx`  
**Severity:** Minor — UX  
**Status:** ✅ Fixed

**Problem:** In the `onChange` debounce handler, both `JSON.parse` failures and `updateDeck` HTTP failures end up in the same `catch (e)` block and display `e.message` in the same red banner. Users cannot tell whether their JSON is malformed or the server rejected a valid-looking deck.

**Fix:** Separated the two failure modes with distinct prefixes ("JSON syntax error: …" vs the server error message) so users know immediately whether the problem is local or remote.

---

## Summary

| ID | Severity | Area | Status |
|---|---|---|---|
| BUG-001 | 🔴 High | Security (XSS) | ✅ Fixed |
| BUG-002 | 🔴 High | Reliability (storage) | ✅ Fixed |
| BUG-003 | 🔴 High | Cost/Abuse (rate limit) | ✅ Fixed |
| BUG-004 | 🔴 High | Correctness (model version) | ✅ Fixed |
| IMP-005 | 🟡 Medium | DX (error parsing) | ✅ Fixed |
| IMP-006 | 🟡 Medium | Security (CORS) | ✅ Fixed |
| IMP-007 | 🟡 Medium | Correctness (validation) | ✅ Fixed |
| IMP-008 | 🟡 Medium | UX (loading state) | ✅ Fixed |
| IMP-009 | 🟡 Medium | Resource leak (sessionStorage) | ✅ Fixed |
| IMP-010 | 🟡 Medium | Code quality (dead code) | ✅ Fixed |
| IMP-011 | 🟢 Minor | Security (prompt injection) | ✅ Fixed |
| IMP-012 | 🟢 Minor | Correctness (token budget) | ✅ Fixed |
| IMP-013 | 🟢 Minor | API contract (PATCH error) | ✅ Fixed |
| IMP-014 | 🟢 Minor | UX (error distinction) | ✅ Fixed |
