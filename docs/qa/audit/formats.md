# Audit: `/app/formats` + `web/feat/formats.js`

Auditor: agent-135 (QA swarm, audit wave). Skill loaded: `systematic-debugging`.
No browser tools used; audit by file reads, grep, and curl against `http://127.0.0.1:8798`.

## Owned

- Page: `/app/formats` (registered in `web/feat/formats.js` via `P.page("formats", ...)`, nav "Clip formats", group "Make", order 19)
- File: `web/feat/formats.js` (494 lines, read fully)

## Checks run

1. Read `web/feat/formats.js` fully (494/494 lines).
2. Page shell: `curl -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/formats` → **200**.
3. `/` → 303 (normal redirect). `/assets/feat/formats.js` → **200**; `/assets/plugins.js?v=9` → **200** (the loader at `web/plugins.js:248` fetches every `web/feat/*.js` from `/assets/feat/`, so the page draws).
4. Every route the feature calls exists in `studio/`:
   - `GET /api/formats` — `studio/api_style.py:104`
   - `GET /api/captions/styles` — `studio/api_style.py:46`
   - `GET /api/style/preview` — `studio/api_style.py:218`
   - `GET /api/style/motion` — `studio/api_style.py:326`
   - `GET /api/brand` / `PUT /api/brand` — `studio/api_brand.py:42/48`; PUT accepts `{brand:{...}}` (`api_brand.py:65-66`), the exact shape `fmtuse` sends.
   - `data-act="pcpage"` handled in `web/plugins.js:156`; icon `"film"` is a real icon (`web/index.html:941`).
5. No id clashes: `fmt_meta`, `fmt_status`, `fmt_looks`, `fmt_formats` appear nowhere in `web/index.html`.
6. Live API payloads fetched and inspected: `/api/formats` (8 shapes, `default:"moment"`, `needs_parts` present), `/api/captions/styles` (45 styles, `count:45`, server-side `default:"bounce"`), `/api/brand` (`brand.style:"beast"`).
7. Contrast computed for every text pair the page uses (all pass; table below). Pages render inside `<main id="main">` (`web/index.html:907`), so the `--faint:#A0948C` override in `web/feat/polish-contrast.js:29` applies.
8. `node --check web/feat/formats.js` → OK; 0 em dashes; all markup goes through `esc(...)` (`formats.js:75`); no absolute origins.
9. Programmatic check of the live styles payload: 12 styles where `anim` equals the label (duplicate descriptor), 15 with no `anim` (no descriptor line — intentional).

## Contrast results (computed `(L1+0.05)/(L2+0.05)`, body text judged at 4.5)

| Pair | Ratio | Used by | Verdict |
|---|---|---|---|
| `--dim` #A3A3A3 on `--bg` #0A0A0A | **7.85:1** | `.fmtp-hint`, `.fmtp-meta`, `.fmt-line`, `.ftile-lb`, `.fmtp-status` | pass |
| `--dim` #A3A3A3 on `--muted` #111111 | **7.49:1** | `.fmt-empty p`, "Frame not drawn" tile text | pass |
| `--faint` #A0948C on `--bg` #0A0A0A | **6.70:1** | `.ftile-do` descriptor line | pass |
| `--brand-deep` #FFB27A on `--bg` #0A0A0A | **11.22:1** | pressed "Use as default" buttons | pass |
| `.moving` #F5F5F5 on `rgba(0,0,0,.62)` over a white frame | **5.69:1** (worst case) | "Still frame" badge | pass |

No text on this page is below 4.5:1. No 404/500. No console-risky code (`typeof ic` on the undeclared `ic` is safe; `matchMedia`/`disconnect` are guarded).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `web/feat/formats.js:298-305` | 12 of 45 look tiles render the motion descriptor as a duplicate of the label: "Comic / Comic", "Drop / Drop", "Duo / Duo", "Glow / Glow", "Hollow / Hollow", "Meme / Meme", "Punch / Punch", "Shake / Shake", "Slide / Slide", "Stamp / Stamp", "Sweep / Sweep", "Whisper / Whisper" | `/api/captions/styles` returns `anim` equal to the label for those 12 looks (verified live); `tileHtml` prints `what = kind.charAt(0).toUpperCase()+kind.slice(1)` (`formats.js:299`) whenever `anim` is non-empty | In `tileHtml`, skip the descriptor when `kind.toLowerCase() === (x.label \|\| x.name).toLowerCase()`, or map motion names to words ("Bounce"→"Bounces in", "Glow"→"Glows") |
| important | `web/feat/formats.js:146,173,307` | The currently-default look is never marked: all 45 "Use as default" buttons render `aria-pressed="false"` / "Use as default" even for the look that *is* the default (beast right now). `lookPick`/`shapePick` are assigned and never read anywhere | `/api/brand` returns `brand.style:"beast"` (verified live); `formats.js:307` hardcodes `aria-pressed="false"`; `formats.js:146`/`173` write the pick fields with no reader. Note the styles API's `default` is a hardcoded `"bounce"` (`api_style.py:69`), so it cannot be trusted either — `brand.style` is the authority the page itself saves to in `fmtuse` | In `load()`, also fetch `GET /api/brand` (already used by `fmtuse`) and mark the matching tile `aria-pressed="true"` + "Default for new clips" |
| important | `web/feat/formats.js:116,195-196,208-209` (+ dead CSS `:23-26`) | `needs_parts` is fetched and normalized into `needs` but never rendered. The comment says "the foot line says how many moments it joins", but `shapeCard` outputs only a heading and one line, and `.fmt-foot`/`.fmt-parts`/`.fmt-need` CSS is never used. A user choosing Callback or Compilation never learns it needs 2-3 clips | `/api/formats` returns `needs_parts` (callback:2, compilation:3, escalation:3, thenvsnow:2 — verified live); `formats.js:116` computes `needs`; `shapeCard` (`:208-209`) emits no foot; CSS `:23-26` has no HTML producer | Render it in `shapeCard`, e.g. `<div class="fmt-foot"><span class="fmt-need">Joins N clips</span></div>` when `f.needs > 1`; or delete the dead CSS and correct the comment |
| minor | `web/feat/formats.js:83` | Dead helper `icon()` is defined and never called; it also references `ic`, which is not defined in this file (safe only because `typeof` guards it) | grep: no call site for `icon(` in the file | Delete it |
| minor | `web/feat/formats.js:300` | Comment claims the frame is "shown at a ninth" — 270×480 is a quarter of 1080×1920 | 1080/270 = 4 | Fix the comment to "a quarter" |
| minor | `web/feat/formats.js:470` vs `:478` | Nav row says "Clip formats" but the page h1 says "Caption styles"; the formats list itself sits collapsed inside a `<details>` at the bottom, so the two names never appear together and a beginner may think they landed wrong | `P.page nav:"Clip formats"` (`:470`); `view()` h1 "Caption styles" (`:478`) | Align the names (nav "Caption styles", or h1 "Clip formats & caption styles") |
| minor | `web/feat/formats.js:41` | The "Still frame" badge is 9.5px — the smallest text on the page, below every other size used (11-15px) | `.ftile .moving{font-size:9.5px;...}` | Raise to 11px like `.ftile-do` (contrast already passes at 5.69:1) |
| minor | `web/feat/formats.js:219-225` | Empty-state headline "Editing ideas could not be loaded." also shows when the server legitimately answered with an empty list; only the note below corrects it | `paintShapes` uses one headline for both the empty and the error case; `note` carries `shapeWhy` only on error | Use "No editing ideas yet." when `!shapeWhy` |

## Usability (first-class)

| where | what | fix |
|---|---|---|
| Look tiles (`formats.js:301-308`) | A beginner cannot see which caption style is already the default; every tile says "Use as default" and they must leave the page (Brand tab) to find out | Mark the current default tile `aria-pressed="true"` / "Default for new clips" on load |
| Shape cards (`formats.js:197-210`) | Shape cards never say how many clips a shape joins ("Callback needs 2"), though the server sends it and the code comment promises it | Show "Joins N clips" in the card foot |
| Nav vs page (`formats.js:470/478`) | "Clip formats" nav leads to a page titled "Caption styles" | Make the two names agree |
| Look tiles (12 styles) | Duplicated descriptor ("Meme / Meme") reads as a rendering bug | Skip or reword when the descriptor equals the label |
| `formats.js:41` | 9.5px "Still frame" badge is very small to read | 11px |

## No finding (verified clean)

- Loading states for both lists (`:216`, `:397`); distinct empty vs error states with the server's own message via `why()` (`:92-95`).
- `role="status"` on the save-status line (`:482`); `aria-pressed` + disabled button during save (`:432`, `:439-442`).
- Frames carry `width`/`height` so the grid does not jump (`:302`); IntersectionObserver lazy loading with 4 still / 3 motion slots and 20s/45s timeouts (`:234-252`, `:320-357`); `prefers-reduced-motion` handled in CSS (`:68-71`) and JS (`:371-374`); motion-video `error` events cannot double-fire the frame handler (guarded by `img.tagName !== "IMG"`, `:287`).
- Save flow read-then-PUT is correct: the PUT replaces the whole document, so reading first preserves keys the person set elsewhere (`api_brand.py:48-73`).
- `node --check` passes; no em dashes; ids unique vs `index.html`; all fetches same-origin.
