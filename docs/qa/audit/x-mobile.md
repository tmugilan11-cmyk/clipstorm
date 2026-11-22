# X-MOBILE — cross-cutting audit at 390 px

Auditor: agent-165 (x-mobile), 40-agent QA swarm.
Scope: cross-cutting. At a 390 px-wide phone viewport: fixed widths, grids without a
narrow collapse, dialog widths, and tap targets under 44 px — across **all** of
`web/feat/*.js` CSS plus `web/index.html` shell CSS (no single page owned).
Rule set: `docs/qa/CONTRACT.md`. Method: static audit only (no browser) — media-query
and CSS box-model arithmetic against the 390 px viewport, grep-swept over every file.
Server check: `GET /app/home` → 200 (http://127.0.0.1:8798), `GET /` → 303.

## Pages / files owned

- `web/index.html` — shell CSS (palette, `.app` grid, dialogs, toasts, pop, tour,
  stream panel, clip editor) — shared with every other auditor; this report covers it
  cross-cuttingly, not page by page.
- All 76 files in `web/feat/` — their injected CSS and the media queries inside them.

## The one rule that decided most tap-target findings

`web/feat/polish-mobile.js` (lines 12–90) is a dedicated `@media (max-width:640px)`
block that gives **`.btn`, `.btn.sm`, `.btn.icon`, `.icon-btn`, `.nav-item`, `.chip`,
`.tabbtn`, `button.pill`, `a.pill`, every `input`/`select`** (via `:where()`) and
`label.ck`/`label.sw` a `min-height` of 44–46 px. `min-height` clamps `height` in the
used-value calculation regardless of which `height` declaration has higher specificity,
so a control that polish-mobile names is **never** sub-44 at ≤640 px even when an
older, more specific rule sets `height: 30px`. Two draft findings were retracted on
this rule after verification:

- `index.html:836` `.topbar #actions .btn{height:34px;padding:0 10px;font-size:13px}` — covered by `polish-mobile.js:47` (`.btn{min-height:44px}`) → renders 44 px. Not a finding.
- `web/feat/pill.js:27` `.pcrun.btn{height:30px}` at ≤560 px — the element carries `.btn`, covered by `polish-mobile.js:47` → 44 px. Not a finding.

Every finding below is a control that polish-mobile's sweep does **not** name.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `web/index.html:670` | Clip-editor word chips `.ed-w` are ≈26 px tall — the primary transcript interaction: tapping a word seeks the video. On a phone the chips are one dense row of ~26 px targets. | `padding:4px 8px;font-size:12px;line-height:1.3` → 12×1.3 + 8 + 2 = 25.6 px. polish-mobile names `.chip` (line 54) but `.ed-w` is not a `.chip`. | Add `.ed-w{min-height:44px;padding:8px 10px}` to the polish-mobile 640 px block (or an index.html 640 px rule). Dense transcript rows still wrap fine at 44 px. |
| important | `web/feat/audio-page.js:85-87` | Sounds-page per-sound buttons `.alb-mini` are ≈31 px tall — the only preview/download control on every catalogue sound row. | `padding:4px 8px;font-size:11px` with `font:inherit` line-height 21 px → 21 + 8 + 2 = 31 px. No matching min-height in polish-mobile. | `@media (max-width:640px){.alb-mini{min-height:44px}}` (page-side override already narrows `.alb-sidebar` inputs, line 52–55, so this fits the same block). |
| minor | `web/index.html:678` | Clip-editor rail-nav buttons `.ed-railnav button` ≈35 px tall — the pane tabs inside the editor dialog. | `padding:6px 8px;font-size:12px`, `font:inherit` line-height 21 px → 21 + 12 + 2 = 35 px. | `min-height:44px` at ≤640 px. |
| minor | `web/index.html:142` | `.splat button` is a fixed 30×30 box — the platform buttons of the live-stream panel. | `width:30px;height:30px` literal. | 44×44 box at ≤640 px (or 30 px icon inside a 44 px hit box). |
| minor | `web/feat/analytics-trends.js:44` | Trend-chip close button `.atr-x` is 26×26. | `width:26px;height:26px` literal. | 44 px hit box at ≤640 px; keep the glyph small, pad the box. |
| minor | `web/feat/analytics-trends.js:42` | `.atr-chip` itself (button) is capped at 32 px via explicit `min-height:32px`. | `min-height:32px` literal — an explicit declaration, so polish-mobile's absent sweep leaves it at 32. | Raise to `min-height:44px` at ≤640 px. |
| minor | `web/index.html:703` | New-toast close `.ntoast .x` is 22×22 — the smallest control on the page. | `width:22px;height:22px` literal. | 44 px hit box (toasts auto-dismiss, but a user may still tap close). |
| minor | `web/feat/polish-keyboard.js:31` | Keyboard-palette close `.pckb-x` is 30×30. | `width:30px;height:30px` literal. | 44 px box at ≤640 px. |
| minor | `web/feat/peek.js:25` | "Take stills" button `.pcpeekbtn` is 30 px tall. | `height:30px` literal (dashed secondary button on clip cards). | `min-height:44px` at ≤640 px; container query at `web/feat/peek.js:31` already handles the narrow card. |
| minor | `web/feat/audio-page.js:63-64` | Sounds-page tabs `.alb-tab button` ≈31 px tall. | `padding:5px 11px;font-size:12px`, `font:inherit` line-height 21 px → 31 px. | `min-height:44px` at ≤640 px. |
| minor | `web/feat/filters.js:17` | Filter pills `.pcf-pill` capped at 32 px via explicit `height:32px`. | `height:32px` literal. | `min-height:44px` at ≤640 px. |
| minor | `web/index.html:850` | Tour close `.tr-x` is 32×32. | `width:32px;height:32px` literal. | 44 px box at ≤640 px (a 700 px query for `.tr-card` already exists at line 869). |
| minor | `web/index.html:722` | "Mark read" in the notifications pop, `.pop-head button`, ≈29 px tall. | `padding:4px 6px;font-size:12px`, inherited line-height 21 px → 29 px. | `min-height:44px` at ≤640 px. |
| minor | `web/index.html:712` | Sidebar account button `.me-btn` ≈38 px tall (borderline, included for completeness). | `padding:4px;margin:-4px` around a 30 px avatar → 38 px. | `min-height:44px` at ≤640 px. |
| minor | `web/index.html:362` | Dropdown option buttons `.pick-opt` ≈37 px tall — the picker listbox rows (creator/brand pickers on every page). | `padding:8px 10px;font-size:13px`, `button{font:inherit}` line-height 21 px → 21 + 16 = 37 px. The trigger `.pick-btn` has `.chip` and is covered; the options are not. | `@media (max-width:640px){.pick-opt{min-height:44px}}`. |
| minor | `web/index.html:396` + `:421` + `:397` | `.tiles3{repeat(3,minmax(0,1fr));gap:8px}` has **no ≤640 px fold** (the 640 px query at 421 folds only `.og`/`.nsteps`). In the create dialog at 390 px (358 px dialog, 24 px padding → 310 px inner, 2×8 gap) each `.tile-o` button is ≈98 px wide and ≈35 px tall. | `repeat(3,minmax(0,1fr))` literal; arithmetic above; no `@media` anywhere names `.tiles3` (grep over both files, 68 `@media` hits reviewed). Labels like "Word by word" wrap to two lines. | Add `@media (max-width:640px){.tiles3{grid-template-columns:repeat(2,minmax(0,1fr))}.tile-o{min-height:44px}}` — 2 columns makes the tiles ~151 px wide, one line of label, and a real tap target. |

### Usability findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `web/index.html:836` | At ≤560 px the shell hides **every** `.hint` from the page (`display:none`). A beginner on a phone loses all inline explanations of what a field or control does — the hints exist precisely for people who do not program. | `.hero,.hint{display:none}` inside the 560 px block. `web/feat/settings-explain.js:21` re-shows some settings hints at ≤560 as `display:block` — partial coverage only; hints on other pages (jobs, live, sounds, insights) stay gone. | Either stop hiding `.hint` and let it wrap, or scope the hide to the handful of hints that genuinely do not fit, and extend the settings-explain re-show to the other pages. |
| minor | `web/index.html:396,397` | Create-dialog caption-style tiles are ≈98 px wide at 390 px, so their labels wrap to two cramped lines; readable, but the same `.tiles3` fold that fixes the tap target fixes the wrap. | Same arithmetic as findings table row above. | Covered by the `.tiles3` fold fix. |

## Verified-OK (checked, no finding)

- **Grids**: every repeat-N grid found has a narrow collapse or a bounded box: `.akpi` 6→3(1180)→2(640)→1(430) (`web/feat/analytics-kpi.js:7,19-21`); `.arv-cells` 3→1fr(640) (`web/feat/analytics-revenue.js:18,29`); `.pcgrid .wk` 7→4(640) (`web/feat/grid.js:12,36`); `.pcstr-modes`/`.pcstr-grid` 3→1fr(680) (`web/feat/streamer-mode.js:19,40,77-86`); `.aed-body` 3→2(1320)→1(760) (`web/feat/audio-edit.js:130-131`); `.alb-body`→column(640) (`web/feat/audio-page.js:52`); `.usg-ledger`→1fr(700) (`web/feat/usage.js:59-64`); `.cr-grid`/`.cr-row`→1fr(560) (`web/feat/creators.js:61-66`); `.editor` 3-col→`1fr` at ≤900 (`index.html:830-833`); `.two`/`.split`/`.home-grid`→1fr (`polish-mobile.js:26-27`); `.kpis`→2col (`polish-mobile.js:28`).
- **Fixed widths**: all wide fixed widths live inside a horizontal-scroll box: `.ant-t{min-width:960px}` in `.scroll` (`web/feat/analytics-table.js:18,156`); `.aa-map{min-width:520px}` in `.aa-scroll{overflow-x:auto}` (`web/feat/analytics-audience.js:25`); `table:not(.stack){min-width:560px}` in `.scroll` (`index.html:887`). Bounded inputs: `.day-url{width:300px;max-width:100%}` (+680 px fallback, `web/feat/day.js:26,30`); `.ant-tools input{width:240px;max-width:100%}` (`web/feat/analytics-table.js:17`); `.an-ret .rpick select{max-width:300px}` (+700 px fallback, `web/feat/analytics-retention.js:19,47`); `.pics-canvas{width:405px;max-width:100%}` (`web/feat/pictures.js:48`); `.pclive` input `min-width:210px`→`min-width:0;width:100%` at 560 (`web/feat/live.js:39,44`); `.atr-chip{max-width:100%}` (`web/feat/analytics-trends.js:42`); `.kv div{grid-template-columns:180px 1fr}` folded at 860 (`index.html:496,524`); `.tr-chip`/`.tr-chips` wrap (`index.html:846-847`); `.toast{max-width:380px}`→`none` + full-width toasts at ≤640 (`index.html:686`, `polish-mobile.js:88-89`); `.pop{width:360px;max-width:calc(100vw - 24px)}` (`index.html:716`); `.tr-card{width:400px;max-width:calc(100vw - 24px)}` (`index.html:842`).
- **Dialogs at 390 px**: `dialog{max-width:calc(100vw - 32px)}` = 358 px (`index.html:641`); `dialog.wide{width:min(1560px,calc(100vw - 32px))}` (`index.html:650`), 374 px at ≤900 (`index.html:829`); polish-mobile forces `width:max-width:calc(100vw - 20px)` and `max-height:calc(100dvh - 20px)` at ≤640 (`polish-mobile.js:78`) and stacks `#clipdlg .editor` to one column with the video capped at 40 vh (`polish-mobile.js:80-82`); `.ed-side{max-height:32vh}` bounds the transcript pane (`index.html:833`). All dialog content fits 390 px.
- **Drawer / shell at ≤900 px**: `nav-responsive.js` (NARROW = 900 px, line 9) makes the sidebar a `min(280px, 86vw)` drawer, hidden when closed, `inert` when closed, wired through `data-act=collapse`, closed by Escape (lines 18-27, 49) — no content sits off-screen.
- **Scroll reachability**: `polish-mobile.js mark()` (lines 97-124) gives every `overflow-x:auto` region `tabindex=0`, `role=region`, `aria-label`, re-run on resize/rotation (127-143) — horizontally scrolled tables stay keyboard-reachable.
- **Feature loading chain** (so the polish-mobile sweep actually runs on every page): `index.html:925` loads `/assets/plugins.js?v=9` → `web/plugins.js:245` fetches `/assets/feat` → `studio/server.py:473` globs `web/feat/*.js` (skipping `_`-prefixed) → `web/plugins.js:247-250` appends each `/assets/feat/<file>.js` script → `studio/server.py:497-504` serves it → `web/feat/polish-mobile.js:11` `P.css("polish-mobile", …)` injects the block once into `document.head` (`web/plugins.js:34-41`). `plugins.js` is served `no-cache` (`server.py:480`), feature files too (`server.py:504`).
- **Contrast**: no contrast finding found in the swept CSS; palette ratios are declared in the shell header (`--bg #0A0A0A`, `--text #F5F5F5` 18.4:1, `--faint #7C7C7C` 4.6:1, `--brand #FF8B33` 7.6:1), and dark ink never returns onto the page colour (existing `tests/test_text_ink.py` guard).
- **No dead handlers**: the picker/stepper/choice markup (index.html:1584-1601) is wired by a document-level click handler for `.pick-btn`/`.pick-opt`/`[data-seg]`/`[data-step]` (index.html:1603-1620); late plugin registration works (`web/plugins.js:28`).

## Checks run

1. `ops_glob` web inventory: 85 files under `web/` (76 feat files + shell assets).
2. `curl http://127.0.0.1:8798/app/home` → 200; `curl http://127.0.0.1:8798/` → 303.
3. Grep sweeps (all 76 feat files + index.html): `@media` (68 hits reviewed),
   `grid-template-columns` (33 index + 11 feat hits),
   `width|min-width|left|right|top|bottom|margin|padding:\d{3,}px` (84 feat files),
   `white-space:nowrap|overflow-x` (49 feat files), `repeat(\d)` grids (11 feat),
   small boxes `height:\s*(2[0-9]|1[0-9]|[0-9])px` and `width:\s*(2[0-9]|1[0-9]|[0-9])px`
   (89 files), `tiles3`/`tile-o` (2 + 7 hits), `script src` (2), `feat/` (1).
4. Full reads: `web/index.html` lines 1-150, 640-909, 1575-1634; `web/feat/nav-responsive.js`,
   `web/feat/polish-mobile.js` (1-130), `web/feat/grid.js` (1-80), `web/feat/usage.js` (40-109),
   `web/feat/creators.js` (50-129), `web/feat/streamer-mode.js` (70-129),
   `web/feat/analytics-table.js` (1-60 + scroll grep), `web/feat/analytics-compare.js` (1-40),
   `web/feat/audio-page.js` (50-109), `web/feat/live.js` (36-75), `web/feat/peek.js` (1-35),
   `web/plugins.js` (1-60), `studio/server.py` (460-514).
5. Cascade re-verification of every sub-44 control against polish-mobile's min-height
   sweep (see "The one rule" section); two draft findings retracted on evidence.
