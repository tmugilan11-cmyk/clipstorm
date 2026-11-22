# polish-mobile

**File I own:** `web/feat/polish-mobile.js`. Nothing else was edited.

**Skill loaded:** `make-interfaces-feel-better`. It gave the 44 px hit area used through the page and the rule that a hover or press changes colour only.

## What I added

One scoped `@media (max-width:640px)` block through `PeakCut.css`, plus a small helper that makes sideways scrollers usable with a keyboard.

**No sideways scrolling.** `#main`, `#view` and `.content` are pinned to the viewport width. Cards, grids, rows and the KPI strip get `min-width:0` so a wide child cannot push a parent open. Images, video, SVG and charts are capped at 100 percent.

**One column where there were two.** `.two`, `.split` and `.home-grid` become one column. `.kpis` becomes a two column grid, which keeps the numbers side by side rather than hiding any of them.

**The shell and wide tables.** Shorter top bar, tighter content padding with room for the phone safe area, toasts inside the screen edge. `.scroll` stays a scroller, capped at the viewport width and holding its own overscroll, so a wide table scrolls inside its box and the page never moves.

**Every tap target is at least 44 by 44.** Buttons, icon buttons, chips, nav rows, checkboxes, switches, stepper buttons, number fields and the round help button. Where a control must stay small to look right, its box grows and the ink keeps its size. Nothing is hidden to reach the size.

**The clip dialog.** It becomes a full height column: video on top, panel underneath. The video is capped at 40 percent of the screen height so the panel stays reachable, and the panel no longer has its own sideways scroll.

**Keyboard.** A `.scroll` box that really overflows becomes focusable and gets a short label. That is added only while the box overflows and only on a phone, removed when it fits, and never overwrites a role or label the page already set. The check reruns on resize and orientation change, debounced to 180 ms.

## Checks

    $ node --check web/feat/polish-mobile.js
    JS OK

    $ cd peakcut && python tests/test_feat_files.py
    {"files": 58, "checks": 470}
    All checks passed.

## What I measured

Real page at 390 by 844, phone width active, new stylesheet present.

- Page width 390 on every view tested: home, analytics, creators, tools, formats, sounds, AI, storage, apps, schedule, help. Elements wider than the viewport outside a scroller: 0. Elements reaching past the right edge outside a scroller: 0.
- Two column areas: 356 px of one column. The KPI strip holds two columns.
- Tap targets under 44 by 44: home 0 of 22, tools 0 of 22, creators 0 of 3, formats 0 of 1, sounds 0 of 14, storage 0 of 2, apps 0 of 7, schedule 0 of 6, help 0 of 6.
- Clip dialog open: 370 by 824 in a 390 by 844 screen, page width still 390, 0 elements wider than the screen, 0 of 6 controls under 44, panel scrolls 348 of 348 so no sideways scroll, video 338 px tall in a column layout.

## Still missing

Two links inside sentences, left on purpose: analytics "Connected apps" 98 by 18, and the AI dashboard address at 120 by 16. Making either 44 tall would break the line of prose it sits in. Everything else on those two pages meets the size.
