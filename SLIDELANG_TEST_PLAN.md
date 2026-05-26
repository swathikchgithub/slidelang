# Slidelang — Test Plan (v0)

**Live URL:** https://slidelang.vercel.app
**Tester:** _____________________
**Date/Time:** _____________________
**Total est. time:** 20-30 minutes

---

## Before you start — read this

Slidelang takes a text prompt and generates a slide deck using AI. After generation, you can edit the underlying JSON and present the deck in full screen. You're testing the live website.

**This is a v0 prototype.** A few things that look like bugs are actually expected behavior:

- The first deck you generate might take 25-35 seconds (the server was asleep). Decks 2-4 should be ~10-15 seconds.
- The mobile editor view (when you tap on a deck) is cramped. That's a known limitation — you're testing whether **present mode** works on mobile, not whether you can comfortably edit JSON on a phone.
- Decks disappear when the server restarts. If you come back tomorrow and a deck URL gives "404 deck not found," that's expected.
- The AI sometimes picks themes/transitions you wouldn't have picked. That's not a bug.

**What IS a bug:**
- Errors that prevent you from completing a test (red banners, 500 errors, blank pages)
- Slides with overlapping text or content cut off the slide
- Math equations showing as raw `$$x^2$$` instead of rendered math
- Charts not appearing where they should
- The website becoming completely unresponsive

**How to fill this out:**
- For each test case below, complete the steps and write what you saw in the "Actual" row
- Mark each case **PASS** or **FAIL** at the end
- If FAIL, note the issue using the bug template at the bottom

---

## Environment check

Before running tests, complete this table:

| Item | Value |
|---|---|
| Browser 1 (primary) | _e.g. Chrome 124 on macOS_ |
| Browser 2 (secondary) | _e.g. Safari 17 or Firefox 125_ |
| Mobile device | _e.g. iPhone 15, iOS 17.4, Safari_ |
| Network | _Home WiFi / Office WiFi / Mobile data_ |

---

## Section 1 — Desktop, Primary Browser (Chrome recommended)

### TC-01: Landing page loads

**Steps:**
1. Open https://slidelang.vercel.app in a fresh tab
2. Wait for the page to fully load

**Expected:**
- Page title shows "Slidelang"
- Subtitle says "Describe a deck. Get editable, presentable slides."
- A large text input box is visible
- A "Generate deck" button is visible below the input
- Three example prompts are listed under "Try one of these"
- No error messages or broken layout

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-02: Generate a simple deck

**Steps:**
1. Type this exact prompt into the text box:
   ```
   3-slide intro to recursion for beginners
   ```
2. Click "Generate deck"
3. Watch the button text — it should change to "Generating… X.Xs" with a counter
4. Wait until you're redirected to a new page (this may take 10-35 seconds)

**Expected:**
- The button shows a counting timer while waiting
- You're redirected to a URL like `/deck/abc12345`
- The new page shows JSON text on the left side and a slide preview on the right
- The slide preview shows the first slide with the title "Recursion" or similar
- Near the top of the page, a green badge shows `⚡ X.Xs` with the time it took
- No red error banners

**Actual:**
_______________________________________________
_______________________________________________

Record the timing: **____ seconds**
Did you see an amber "repaired" tag next to the timer? **YES / NO**

**Result:** PASS / FAIL

---

### TC-03: Present mode (the main demo flow)

**Steps:**
_(Continue from the deck generated in TC-02)_

1. Click the "Present" button in the top-right of the editor page
2. A new full-screen view opens with the deck
3. Press the **right arrow key** on your keyboard to move to the next slide
4. Continue pressing right arrow until you reach the last slide
5. Press **left arrow** to go back
6. Press **Esc** to exit present mode

**Expected:**
- Present mode opens in full screen
- Slides have a dark background (default theme)
- The first slide is clearly a title slide (large centered text)
- Subsequent slides have a heading + content (bullets, text, or code)
- Arrow keys navigate forward and backward correctly
- No slides appear blank or broken
- Esc returns you to the editor (or exits — either is fine)

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-04: Live editing updates the preview

**Steps:**
1. Go back to the editor page from TC-02 (or generate a new deck)
2. In the JSON editor on the left, find the first slide's `"title"` field
3. Click into the title value and change it to "Edited Title Test"
4. Click somewhere outside the editor to deselect
5. Wait about 2 seconds
6. Look at the preview on the right

**Expected:**
- The preview reloads after a brief delay
- The new title "Edited Title Test" appears in the rendered slide
- A small "saving..." indicator may appear briefly near the top
- No error messages appear

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-05: Generate a deck with math

**Steps:**
1. Click "← New deck" in the top-left to go back to the homepage
2. Type this prompt:
   ```
   4 slides explaining the Pythagorean theorem with the formula
   ```
3. Generate and wait
4. When the editor opens, click Present
5. Navigate to slides that should contain math equations

**Expected:**
- At least one slide contains a mathematical formula
- The formula is rendered as proper math notation (e.g., proper exponents, square root symbols, equals signs)
- The formula is NOT shown as raw text like `$$a^2 + b^2 = c^2$$` (this would be a bug)

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-06: Generate a deck with a chart

**Steps:**
1. Go back to the homepage
2. Type this prompt:
   ```
   4 slides comparing PostgreSQL vs MongoDB vs Redis, include a chart of one quantitative tradeoff
   ```
3. Generate and wait
4. Open Present mode and find the slide with the chart

**Expected:**
- One slide contains a visible chart (bar, line, or pie)
- The chart has labels (axis labels, category names)
- The chart is not blank or missing data
- Chart fits within the slide (not cut off)

**Actual:**
_______________________________________________
_______________________________________________

Record the timing: **____ seconds**

**Result:** PASS / FAIL

---

### TC-07: Provoke the repair loop (advanced)

This test tries to give the AI a difficult prompt to see if the "self-healing" feature works.

**Steps:**
1. Go back to the homepage
2. Type this prompt:
   ```
   25-slide pitch deck for a startup, every single slide must have at least 3 charts and detailed financial data
   ```
3. Generate (this may take 30-60 seconds because the AI may have to retry)

**Expected:**
- Generation eventually completes (does NOT show a red error)
- After redirect, the green timer badge may show an amber "repaired" tag next to it
- The deck loads successfully and renders without broken layout
- The number of slides may be less than 25, and each slide may have fewer charts than requested — that's expected, the system is preventing over-crowded slides

**Actual:**
_______________________________________________
_______________________________________________

Did you see the "repaired" tag? **YES / NO**
Generation time: **____ seconds**

**Result:** PASS / FAIL

---

### TC-08: Browser console check

**Steps:**
1. While on any deck page, open the browser DevTools (`Cmd+Option+I` on Mac, `F12` on Windows)
2. Click the "Console" tab
3. Look for any red error messages
4. Note: yellow warnings are usually fine; red errors are the issue

**Expected:**
- No red errors related to "slidelang" or "api/generate" or "api/compile"
- It's OK to see warnings or errors from third-party scripts (Tailwind, Next.js dev warnings, etc.)

**Actual:**
_______________________________________________
_______________________________________________

If any red errors, paste the first line of each here:
_______________________________________________

**Result:** PASS / FAIL

---

## Section 2 — Desktop, Secondary Browser (Safari OR Firefox)

### TC-09: End-to-end in a different browser

**Steps:**
1. Open https://slidelang.vercel.app in your secondary browser (Safari or Firefox)
2. Generate this prompt:
   ```
   3 slides on the Fibonacci sequence with the formula
   ```
3. Open Present mode
4. Navigate through all slides

**Expected:**
- Same behavior as Chrome — page loads, deck generates, present mode works
- Math formula renders correctly (not as raw text)
- No browser-specific layout breaks (overlapping text, cut-off content)

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

## Section 3 — Mobile

### TC-10: Mobile landing + generation

**Steps:**
1. On your phone, open https://slidelang.vercel.app in your default browser
2. Type a short prompt:
   ```
   3 slides on photosynthesis for a 10 year old
   ```
3. Tap "Generate deck"
4. Wait for the editor page to load

**Expected:**
- The landing page is readable on the phone screen (might need to scroll, that's OK)
- The text input is usable on the touch keyboard
- The deck generates successfully
- The editor page loads (the JSON view will look cramped — that's expected)

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-11: Mobile present mode

**Steps:**
_(Continue from the deck generated in TC-10)_

1. On the editor page, tap the "Present" button
2. Try to navigate slides by tapping the right side of the screen or swiping
3. Try going backwards

**Expected:**
- Present mode opens full-screen
- Slide content fits the phone screen (text is readable without zooming)
- Tap or swipe navigation works between slides
- Pinch-to-zoom is not required for normal reading

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

## Section 4 — Edge cases (optional but valuable)

### TC-12: Empty prompt rejection

**Steps:**
1. Go to the homepage
2. Without typing anything (or after deleting your text), click "Generate deck"

**Expected:**
- The button is disabled / nothing happens / a friendly error appears
- The page does NOT crash or show a server error

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-13: Very short prompt

**Steps:**
1. Type just one word:
   ```
   recursion
   ```
2. Generate

**Expected:**
- The system still produces a deck (the AI fills in the details)
- No error, no crash

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

### TC-14: Page refresh on a deck URL

**Steps:**
1. After generating any deck, copy the URL from the address bar (something like `https://slidelang.vercel.app/deck/abc12345`)
2. Open a new tab
3. Paste the URL and press Enter

**Expected:**
- The deck loads in the new tab
- The JSON editor and preview both appear
- The timer badge does NOT appear (it only shows for decks generated in the current tab — that's expected behavior)

**Actual:**
_______________________________________________
_______________________________________________

**Result:** PASS / FAIL

---

## Summary

| Test | Pass | Fail |
|---|:-:|:-:|
| TC-01 Landing page loads | | |
| TC-02 Generate simple deck | | |
| TC-03 Present mode | | |
| TC-04 Live editing | | |
| TC-05 Math rendering | | |
| TC-06 Chart rendering | | |
| TC-07 Repair loop | | |
| TC-08 Console clean | | |
| TC-09 Secondary browser | | |
| TC-10 Mobile generation | | |
| TC-11 Mobile present | | |
| TC-12 Empty prompt | | |
| TC-13 Short prompt | | |
| TC-14 Direct URL refresh | | |

**Total passes:** ___ / 14
**Critical bugs (blocking):** ___
**Non-critical issues:** ___

---

## Bug Report Template

For each failed test, fill in one of these blocks:

```
BUG #___
Test case: TC-__
Severity: BLOCKER / MAJOR / MINOR

What I did (steps to reproduce):
1.
2.
3.

What I expected:

What happened instead:

Browser/device:

Screenshot attached: YES / NO
Console errors (if any):
```

**Severity guide:**
- **BLOCKER:** prevents demo recording or makes the product unusable for users (500 errors, blank pages, app crashes)
- **MAJOR:** noticeable problem but workaround exists (slide layout broken on one browser, slow on first request)
- **MINOR:** cosmetic or rare (chart colors not great, one obscure prompt fails)

---

## Notes / observations

_Anything else worth flagging that didn't fit a test case — UX confusion, surprising behavior, things that look polished or unpolished, etc._

_______________________________________________
_______________________________________________
_______________________________________________

---

**Done?** Save this filled-in document and send it back to Swathi.
