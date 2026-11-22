# QA audit: Transcription + Brand pages

Auditor: agent-141 (swarm of 40). Date: 2026-11-22.
Rules: docs/qa/CONTRACT.md. No browser tools used (lead owns the browser). Evidence: file lines, measured
contrast ratios, HTTP codes from the live server on http://127.0.0.1:8798.

## Pages and files owned

| What | Where | Size |
|---|---|---|
| Page /app/transcribe | registered in web/feat/menu-pages.js:147, drawn by drawSettingTab (web/index.html:2538) | 200 OK |
| Page /app/brand | registered in web/feat/menu-pages.js:130, drawn by drawSettingTab | 200 OK |
| web/index.html (transcribe + brand bodies, handlers, CSS) | transcribe body 2558–2574, brand body 2687–2707, brandPage() 2384–2466 | 3504 lines |
| web/feat/style-tiles.js | caption-look tile grid beside #br_style | 279 lines |
| web/feat/settings-explain.js | one-line explanations for settings fields | 173 lines |

Also read for wiring (not owned, no findings filed): web/feat/menu-pages.js (page registration + fill()),
web/plugins.js (after-hook machinery, P.state, wireActs).

## Checks run

1. **Page shells**: `curl -s -o /dev/null -w "%{http_code}"` on /app/transcribe and /app/brand — both **200**.
2. **Every API route the pages call exists in studio/**: /api/brand GET+PUT (studio/api_brand.py:42,48),
   /api/captions/styles (studio/api_style.py:46), /api/style/preview (studio/api_style.py:218),
   /api/transcribe GET+PUT (studio/server.py:1496,1502), /api/transcribe/models POST (server.py:1552),
   /api/transcribe/test POST (server.py:1571), /assets/font/{name} (server.py:484),
   /assets/feat/{name} (server.py:497). No 404 candidates.
3. **Live probes**: GET /api/captions/styles returns `{"default":"bounce","styles":[...]}` with ~30 looks
   (bounce, hype, clean, beast, brainrot, …) — so the preview fallback `b.style || "bounce"`
   (web/index.html:2414) names a real style. GET /api/brand returns a real document (style beast, font
   Anton-Regular, colours FFFFFF/00E5FF/000000/FF3B30/FF2E93, watermark @nocodehack). GET
   /api/style/preview?style=bounce → **200 in 0.57 s**; ?style=beast → **200**.
4. **Read every owned file fully**, line by line: all drawSettingTab bodies, brandPage(), brPaintFonts()
   (2484–2495), brPreviewUrl/brPreviewSoon (~3030–3054), trModelField/trHints/trLoadModels (2270–2324),
   brandsave handler (3166–3194), trsave/trtest handler (3146–3164), style-tiles.js and settings-explain.js
   in full, plugins.js after-hook machinery (110–139), menu-pages.js page registration + fill() (82–123).
5. **Contrast measured** (WCAG relative luminance, 1.4.3 / 1.4.11):
   - label.f and .help/.sub 12–13px `--dim` #A3A3A3 on `--bg` #0A0A0A = **7.85:1** (pass).
   - `.stile-lb` 12px `--dim` on tile = **7.85:1**; on hover bg `--muted` #111111 = **7.49:1** (pass).
   - Inputs' placeholder/hints `--faint` overridden to #A0948C by web/feat/polish-contrast.js: on
     `--muted` #111111 = **6.39:1** (pass, even at 11–12px).
   - Input text `--text` #F5F5F5 on `--muted` = **17.3:1** (pass).
   - `.pill.warn` #FFB27A on `--brand-soft` #2A1B10 = **9.42:1** (pass) — owner-only card on Transcription.
   - `.stile-check` #fff on `--brand` #FF8B33 = **2.34:1** (fails 3:1; decorative — see findings).
6. **Mobile width measurement** at a 390 px viewport: `.content` padding 18px 14px (web/index.html:876) →
   362 px wide; `.brand-preview` padding 14px (:466) → 334 px inner; `img` 172px `flex:none` (:474) +
   18px gap (:466) → the `.sub` text column gets **144 px**. No stacking query exists for `.brand-preview`.
   `main#main` has `overflow-x:hidden` at ≤640px, so nothing scrolls sideways; the text just squeezes.
7. **Handler wiring**: brandsave reads all 9 colour ids and validates each against /^[0-9A-Fa-f]{6}$/
   after stripping a leading #, and the toast names the wrong field; trsave/trtest send only on-screen
   fields and omit the key when empty so a saved key is never wiped; pickstyle writes the #br_style select
   and fires change, which reaches brPreviewSoon (debounced 650 ms); every #br_* field is covered by the
   preview listeners (index.html:1750, 3052–3054) — the preview really does follow edits.
8. **After-hook timing**: `P.drawPage` awaits `load()` before running paint hooks (web/plugins.js:130–136),
   so the style-tiles grid and settings-explain always find the form already drawn; on error the page shows
   an inline error card (menu-pages.js:114–122), never an empty box.
9. **Guards**: `document.fonts` feature-detected (index.html:2477), `IntersectionObserver` feature-detected
   with an eager-fill fallback (style-tiles.js:151), `esc()` used on every interpolated value in both feat
   files; `esc`/`ic` resolve to globals defined at index.html:930/992; `PeakCut.state` exists
   (plugins.js:260) so the owner-only gate works.
10. **State coverage**: Loading… (menu-pages.js:101), error state "Brand settings are not available on this
    server yet." (index.html:2705-ish catch), font-picker empty state "This server sent no font list…"
    (brPaintFonts), tile loading sheen + failed frame keeps its label (style-tiles.js:46), tile grid falls
    back to the select's own list when /api/captions/styles fails. Transcribe: trLoading guard, quiet model
    auto-load, ok/bad toasts. The one missing state is the brand preview on error (finding B1).

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | web/index.html:2414 | Brand preview hides itself silently on error. The `<img id="br_preview">` has `onerror="this.parentElement.style.display='none'"`, so when /api/style/preview fails (for example a server without ffmpeg, which the preview needs to draw a frame) the whole `#br_prevbox` — the picture **and** the sentence explaining what it shows — vanishes with no message. A missing error state on the page's centrepiece. | index.html:2414; preview draws with ffmpeg (studio/api_style.py:218); no other error surface for the box | In the onerror, keep the box, hide only the img, and show one line instead: "The preview could not be drawn on this server yet." (keep the existing .sub explanation visible) |
| important | web/index.html:466,474,876 | Brand preview is cramped at phone width: measured at 390 px viewport the `.sub` text column is squeezed to 144 px (about 20 characters per line of 13 px text) because the 172 px `flex:none` image plus the 18 px gap take 190 px of the 334 px box interior. There is no stacking query for `.brand-preview`, so the two-column layout never reflows. | measured: .content 362 px (index.html:876), preview padding 14px (:466), img 172px flex:none (:474), gap 18px (:466) → sub = 144 px | Add `@media (max-width:560px){.brand-preview{flex-direction:column}}` (or cap the img width) so the explanation gets full width on a phone |
| minor | web/index.html:484–490 | Dead CSS: a legacy bare `.stile` block styles a `class="stile"` that no longer exists anywhere in web/ — style-tiles.js now scopes every rule as `.stilegrid .stile` (style-tiles.js:36–52). Harmless, but it is a second truth about the tiles that nothing uses. | grep: no `class="stile"` outside the grid; style-tiles.js:36+ uses `.stilegrid .stile` selectors | Delete the legacy block (or fold anything still wanted into style-tiles.js's own sheet) |
| minor | web/feat/style-tiles.js:48 | The selected tile's check glyph is #fff on `--brand` #FF8B33 = 2.34:1, below the 3:1 non-text minimum. It is `aria-hidden`-decorative and duplicates the orange border, the label flipping to `--text` and aria-pressed, so nothing is lost without it — but it is the one below-minimum pair on the page. | style-tiles.js:47–51; measured L(#FF8B33)=0.3997 → 1.05/0.4497 = 2.34:1; decorative: `.stile.on .stile-lb` turns `--text` (:45) | Use `--brand-ink` #160D05 for the check stroke (about 8.5:1 on the orange), or leave as decorative and note it |

## Usability findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| minor | web/index.html:2414 + 2465 | The preview follows edits live (debounced 650 ms) while the brand is only saved by "Save brand" at the very bottom of a six-section form. The copy explains both ("It follows your edits as you type" / "Save here and every clip made from now on uses it"), but a beginner who edits a colour and sees the frame change can reasonably believe the change is already applied, then close the page. | index.html:2414 (.sub copy), 2465 (button), brandsave handler 3166–3194 (PUT /api/brand is the only save) | Once any #br_* field changes, label the button "Save brand — not saved yet" (or add a sticky save bar), and clear it after the PUT |

Everything else on both pages reads clean: every field has a one-line explanation a beginner can follow in
five seconds (hex fields carry "Six letters or numbers, without the #.", opacity says "0 is invisible, 1 is
solid", the watermark field says what it accepts), "Save and test" folds two steps into one on Transcription,
the style tiles give each look a name and a real frame, and every load/error/empty state except the preview
one listed above is present.

## Verdict

No critical findings. Two important ones (silent preview failure, phone-width squeeze), three minor.
All routes live, both pages 200, handlers wired, contrast passes everywhere except one decorative glyph.
