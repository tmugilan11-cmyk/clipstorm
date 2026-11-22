# x-contrast — cross-cutting WCAG contrast audit (agent-158)

Swarm wave: audit (peakcut, http://127.0.0.1:8798). Rule set: docs/qa/CONTRACT.md.
Scope: every colour pair used as text/background across the shell CSS of `web/index.html`
(`:root` + lines 11–896) and the CSS blocks of all 76 `web/feat/*.js` files. I do not own a
page; I own the contrast dimension across the app.

## Method

- Ratio formula `(L1+0.05)/(L2+0.05)` with the WCAG sRGB luminance function, computed in
  Python for ~90 resolved pairs (batch run, exact values below).
- Translucent overlays composited over their real ground first (e.g. `.count`
  `rgba(255,255,255,.1)` over `--frame #000000` -> `#1A1A1A`; `.ai-ic`
  `rgba(255,139,51,.16)` over `--frame-2 #0F0F0F` -> `#352315`).
- Hover/base pairs resolved by CSS specificity before judging (e.g. `body .pcrun.btn`
  (0,2,1) in polish-colour.js beats `.pcrun.btn` (0,2,0) in pill.js for background only).
- Big text = >=24px or >=18.66px bold judged at 3.0; everything else 4.5. The app's body
  sizes are 11–14px, so 4.5 applies nearly everywhere.
- Severity: text <3:1 = critical (contract rule 5), 3.0–4.49 on user-facing text =
  important, non-text polish / doc drift / WCAG-exempt states = minor.

## Root cause (one sentence)

Every contrast bug below is a white-page remnant: `web/feat/polish-colour.js` maps the old
light surfaces onto the dark palette with `body`-prefixed background overrides, which
strands the old literal light-theme text colours (dark browns, deep reds) on the new dark
grounds and light shimmer grounds, while `tests/test_text_ink.py` only pins
`color:var(--brand-ink)` usage — the reverse (dark literals on dark grounds) is checked by
nothing, so all of these survive the suite.

## Checks run

1. Read `docs/qa/CONTRACT.md` (50 lines) and loaded skill `systematic-debugging`.
2. Read the whole shell style block `web/index.html` lines 11–896 (~890 CSS lines).
3. Read fully: `web/feat/polish-contrast.js`, `polish-colour.js`, `pill.js`,
   `learn-hooks.js`, `polish-focus.js`; read the relevant CSS contexts of `day.js`,
   `audio-edit.js`, `audio-page.js`, `analytics-audience.js`, `style-tiles.js`,
   `polish-errors.js`, `formats.js`.
4. `ops_grep` sweeps across `web/` for `toolsrow|--bg2|pcrun`, `--brand-line|--brand-deep|--faint`
   declarations, `/api/styles` usage (0 hits — no feature calls it), and live-markup
   confirmation for `.vb`, `.making`, `.toolsrow`.
5. Read `tests/test_text_ink.py` lines 1–80 to learn what is already enforced.
6. Python batch contrast compute (~90 pairs, exit code 0) — all numbers below.
7. curl against the server: `/` => 303 (redirect), `/app/insights|settings|live|audio|heard`
   => 200, bogus `/app/nope-404-test` => 200 (shell catch-all, app falls back to its default
   view), `/api/sync` => 200, `/api/learn/hooks?limit=1` => 200, `/api/styles` => 404 but no
   feature references it (probe only, not a bug).
8. Spot-checked escaping: `learn-hooks.js:18`, `style-tiles.js:67`, `polish-errors.js:236`
   all run template output through `esc`/`escHtml` before `innerHTML` — no unescaped插值 found
   in the files I read.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| critical | web/index.html:90 (`.vb b`) + markup 1392–1398 | The bold lead of every status banner is near-invisible: dark brown #5A2C06 on #2A1B10. These bolds carry the one sentence a beginner must read ("The new version is downloaded.", "PeakCut can't make clips yet…", "The AI isn't answering.", "The drive … is almost full", "Confirm your email…") | Computed 1.42:1 (needs 4.5 at 14px); banner bg `#2A1B10` at index.html:87 | Set `.vb b{color:var(--brand-deep)}` (#FFB27A = 12.59:1) or `#FFD9BC`; never a darker-than-ground literal |
| critical | web/feat/pill.js:7 + web/feat/polish-colour.js:54 | Run-pill base text unreadable on its overridden background. pill.js paints light bg + dark text; polish-colour.js:54 (`body .pcrun.btn`, specificity 0,2,1) overrides only the background to `--brand-soft #2A1B10`, leaving `color:#8A3C08` stranded. This is the topbar "Make clips" button on every page, 13px (`btn sm`, index.html:211) | Computed #8A3C08 on #2A1B10 = 2.16:1 (needs 4.5). Hover (pill.js:8) is light-on-light and fine at 7.99:1 — base state is the broken one | In polish-colour.js:54 also set `color:#FFD9BC` (12.59:1) or delete the override; measure before choosing |
| critical | web/feat/pill.js:10 + web/feat/polish-colour.js:58 | Recording-state run pill unreadable: `color:#9E121B` stranded on `--bad-soft #2B1416` by the same body-prefixed background override (0,3,1 beats 0,3,0) | Computed 2.10:1 (needs 4.5 at 13px). is-rec:hover (pill.js:11) fine at 7.08:1 | Same fix: set a pale red ink (`#FFB4B7`-class) or remove the override; measure first |
| critical | web/feat/day.js:17 (with 21, 27) | Day card background is a white-page remnant gradient — light at both ends, dark in the middle: `radial-gradient(130% 190% at 0% 0%, #FFF9F4 0%, var(--brand-soft) 62%, #FFF7F0 100%)` — under light text. `.day-help` `var(--text) #F5F5F5`, `.day-note` `var(--dim) #A3A3A3` | Computed help on #FFF9F4 = 1.04:1, note on #FFF7F0 = 2.38:1 at the light corners; mid is 15.25:1 — text is unreadable near top-left/bottom-right | Flat dark ground (`var(--brand-soft)` or `#1E1612`) so the existing light text reads |
| critical | web/index.html:803 (`.step:hover`) | Hover paints the guided-step cards light (#F1EBE6) under light text — shell-wide hover remnant on the dark page. Card text is `.step b/.n` `var(--text) #F5F5F5` and `.step .d` `var(--dim)` | Computed #F5F5F5 on #F1EBE6 = 1.08:1, #A3A3A3 = 2.13:1 while hovering | Hover to a dark tint (`var(--line-2)` #2A2A2A or #1E1E1E); hover states change colour only, per AGENTS.md |
| critical | web/index.html:809 (`tr:hover>td`) | Hover paints every table row light (#FCFAF8) under light text — hits any table in the app | Computed #F5F5F5 on #FCFAF8 = 1.05:1, faint #A0948C = 2.84:1 while hovering | Hover to `#181818`/`var(--muted)`-over-card; never a light literal |
| critical | web/index.html:570 (`.making`) + markup 1871, 2726, 3447 | The render overlay's shimmer background is light (#F4EFEE/#FBF8F7) under `var(--dim) #A3A3A3` text — "Making this clip…", "Waiting its turn…", "Taking a look…" are unreadable on every clip card while it renders (the error variant at 1870 sets dark `--bad-soft` inline and is fine at 6.25:1) | Computed 2.21:1 on #F4EFEE, 2.39:1 on #FBF8F7 | Dark ground like formats.js:42 does for its video chip: `rgba(0,0,0,.62)` + light text |
| critical | web/index.html:335 (`.lp .tx em`) | The emphasised copy inside the link-composer preview is deep red #A12A2A on the dark `--muted #111111` panel | Computed 2.59:1 (needs 4.5) | Pale warm red (`#F8A9A9`-class) or `var(--brand-deep)`; measure first |
| critical | web/feat/pill.js:13 (`.pcrun.btn.is-wait:hover`) | Hover-only: keeps `color:var(--dim) #A3A3A3` under a light #F1ECE7 hover background | Computed 2.15:1 while hovering (base state 7.49:1 is fine) | Add `color:#3A2C25` to the hover rule (dark on light = readable) or hover to a dark tint |
| critical | web/feat/polish-errors.js:277 (`.pcerr .pcerr-btn:hover`) | Hover-only: white on the light red `--bad #F87171` hover background, 12px button label "Dismiss" | Computed 2.77:1 while hovering (base transparent + `--bad` on `--bad-soft` = 6.25:1 is fine) | Hover to `--bad-soft` + keep `--bad` text, or darken the hover ground (`#C53030`-class, white = 5.6:1) |
| important | web/feat/audio-edit.js:81-82 (`.aed-empty`) | Empty-state copy on the audio-edit lane is #6E6E6E at 11.5px on lane bg `#111` (audio-edit.js:68) | Computed 3.70:1 (needs 4.5) | Use `var(--dim)` #A3A3A3 (7.49:1) or `var(--faint)` #A0948C in main (6.39:1) |
| important | web/feat/audio-edit.js:65-66 (`.aed-ruler b`) | Ruler time labels #7C7C7C at 10px on `--track2 #161616` (audio-edit.js:61) | Computed 4.34:1 (needs 4.5) — borderline fail on the smallest text in the app | `var(--dim)` or #8F8F8F; keep the 10px size but raise the ink |
| important | web/index.html:130 (`.sinfo .lv`), 150 (`.sbadge.rec`), 198 (`.sb-tag.rec`), 199 (`.nav-item.on .sb-tag`), 324 (`.lp .ok.live`) | White 11–12px text on `#E5323F` badges (live/record states) fails AA | Computed 4.32:1 each (needs 4.5) | Darken the badge red to `#C81E28`-class (white on #C81E28 = 5.72:1, proven by `.bell .dotn` index.html:715) |
| important | web/index.html:258 (`.pill.live`) | White 11px text on `--live #EF4444` chip | Computed 3.76:1 (needs 4.5) | Same darkening, or `--brand-ink` text on the red |
| important | web/index.html:743 (`.pop.menu .danger`) on `.pick-menu` ground | Account-menu "sign out/delete" red #C53030 at 13px on the menu ground `#2A1A1A` | Computed 3.04:1 (needs 4.5) | Lighten to `#F87171` on dark (7.16:1) |
| important | web/feat/analytics-audience.js:20-21 (`.aa-dot.new`, `.aa-fill.new`) | The "new viewers" legend dot and bar fill use `var(--brand-ink) #160D05` — a near-black fill on the near-black `--muted #111111` track. The Audience tab's "new viewers" bars are invisible (white-page remnant: dark ink bars on a white page) | Computed 1.02:1 (WCAG 1.4.11 non-text wants 3:1) | Give the "new" series its own visible colour (e.g. `#22D3EE`, 9.26:1 on `#2A1A12`-class grounds, already used by `.aed-chip.ai`) |
| important | web/feat/polish-focus.js:69 (comment 61–63) | Keyboard focus ring on `.side` links/buttons, dialog fields and `.pick-opt` uses `outline-color:var(--brand-line)` = #4A2E18 — dark brown on black, effectively invisible. The comment claims "‑-brand-line is #FFD9BC", which is true only of the old light palette still living in `web/admin.html:14`; index.html:21 has `#4A2E18` | Computed 1.70:1 on sidebar `#000000`, 1.52:1 on dialog `#111111` (WCAG 1.4.11 wants 3:1); the base rule's `--brand-deep` would be 10.70–11.22:1 | Change line 69 to `outline-color:var(--brand-deep)` and rewrite the comment to the measured dark-theme values |
| minor | web/index.html:558 (`.toolsrow small`) | Latent trap: `color:var(--muted)` #111111 as text on `--bg` = 1.05:1 — but dead CSS, no markup uses `.toolsrow` anywhere in `web/` (grep: only CSS lines 555–558) | Computed 1.05:1; grep shows 0 usages | Delete the rule or set `var(--dim)` before anybody revives it |
| minor | web/index.html:559 (`.toolpre`) | `background:var(--bg2)` — `--bg2` is not defined in `:root` (transparent fallback); also dead CSS (no markup) | grep: `--bg2` appears once, in this rule | Use `var(--bg)`/`var(--card)` or delete the rule |
| minor | web/index.html:391 (`.nstep .ctl button:hover`) + web/feat/style-tiles.js:47-49 (`.stile-check`) | White icon on the orange `--brand` ground is under WCAG 1.4.11's 3:1 for graphics; both controls carry other indicators (outline, tile state) so impact is small | Computed 2.34:1 | Use `--brand-ink` icons on brand grounds (8.22:1) |
| minor | web/index.html:346 (`.btn.primary:disabled`) | Disabled-state pair #B9A597 on #F3E7DD = 1.94:1 — WCAG exempts disabled controls; noted so the fix wave doesn't "fix" it | Computed 1.94:1 | None needed (exempt) |
| minor | web/index.html:226-227 (`label.sw input`) | Light switch track #DCD2D0 with #fff knob on the dark page — knob-on-track 1.48:1 makes the knob hard to see; state still readable from position/border | Computed 1.48:1 | Dark track (`#2A2A2A`) with the pale knob; measure first |
| minor | web/feat/polish-contrast.js header vs measured | Header numbers are off: claims 8.10/4.79/7.24/6.86/5.68, measured 7.85 (dim on bg) / 4.74 (#7C7C7C on bg) / 6.70 (#A0948C on bg) / 6.39 (on muted) / 5.63 (on brand-soft). Text 18.16 and #75695F=3.72 match. Header says "None of them are estimates" — they are rounded from a different rounding path | Measured table in this report (Python, exit 0) | Re-measure and rewrite the header numbers; keep "None of them are estimates" true |
| minor | web/index.html:14-16 (`:root` comment) vs measured | Claims 18.4/8.1/4.6/7.6/10.4/9.0/6.3, measured 18.16/7.85/4.74/8.48 (brand on bg)/11.22 (brand-deep on bg)/10.30 (good on bg; 8.01 on good-soft)/7.16 (bad on bg) | Measured table in this report | Update the comment to the same Python rounding as polish-contrast.js so the two agree |

## Verified-OK pairs (no action)

body text #F5F5F5/bg 18.16 · dim 7.85 · faint(root) 4.74 · faint(main override #A0948C)
6.70 bg / 6.39 muted / 5.63 brand-soft · .btn 17.32 · .btn.primary 8.22 (hover 9.12) ·
.btn.danger 6.25 · pcrun hovers 7.99 / 7.08 · .vb text 12.59 · day-sun icon 11.22 ·
.aed-chip 15.35 / .t 9.48 / .ai 9.26 · .aed-box p 6.39 · .aed-hint 6.62 · .alb-cat white on
all nine catalogue colours 5.02–8.23 · .lhk .pill.w #B98900 5.97 / 6.26 · .noembed 19.31 /
8.18 · .stream 14.37 · .savebar 16.44 · .pcerr text 15.86 · .sbadge.live #C53030 on #FDECEC
4.79 · .lp .ok #1F7A4D on #E3F4EA 4.66 · .chprev.bad 6.38 · .lp.bad bg 16.53 · .bell .dotn
white on #C81E28 5.72 · .count 17.40 · .avatar 9.45 · .working 6.54 · .utabs on .n 13.58 ·
.ai-ic 6.41 · aa heatmap cells 15.75 / 5.38 · focus ring --brand 8.48 / --brand-deep
10.70–11.22.

Out of scope, for admin.html's owner: `--faint #A0948C` on its light bg measures 2.70:1.

## Usability findings

1. **The bold in every banner is the message, and it is unreadable** (bug row 1). A beginner
   who sees "PeakCut can't make clips yet: ffmpeg isn't installed" gets the pale tail but the
   dark bold lead disappears. Fix is the same one-line colour change; verify by reading the
   banner after the fix.
2. **The audio editor runs on 10–11.5px text** (`audio-edit.js` ruler 10px, `.aed-empty`
   11.5px, `.aed-note` 11.5px, `.aed-hint` 10.5px). With the ruler already at 4.34:1 and the
   empty state at 3.70:1, the smallest copy in the app is also the least legible. Fix: raise
   the ruler/empty/hint sizes to 12px together with the colour fixes above.
3. **`audio-page.js:38-44` catalogue pills are 11.5px uppercase with 0.09em letter-spacing
   and a 10px count inside** — dense for a beginner scanning sound shelves. Contrast passes
   (5.02–8.23), so this is polish only: drop the uppercase or raise to 12px.
