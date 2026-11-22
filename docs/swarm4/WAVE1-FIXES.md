# Wave 1 fixes

One line per finding from `docs/swarm4/WAVE1-REVIEW.md`: what it was and what I changed. The review was written
by the fixer because the reviewer slot produced no file; that is noted at the top of the review.

## Critical

- **C1, `refreshHost()` recurses forever, `web/index.html:2443-2447`** — not changed. This file is frozen for
  wave 1 and the sixteen save handlers that call it belong to the lead. The fix is to replace
  `if ($("#sform")) return refreshHost();` with `if ($("#sform")) return drawSettings();`. Escalated to the lead.

## Important

- **I1, the menu spine did not know "Set up", `web/feat/menu.js:16`** — added `["Set up", 35]` to `BASE`, so the
  heading the five moved pages use now ranks between "Look and sound" (30) and "Connect" (40) instead of falling
  through to 500 at the bottom of the menu. Used 35 rather than 50 because the live sidebar orders headings by the
  smallest page order under them, and tools/apps sit at 30 and 40; at 50 the spine and the sidebar would disagree.
  Verified after the change by loading the file and printing `pageRows()`: the five pages come out under "Set up",
  in order.

## Not changed, reviewed and judged sound

- `menu-pages.js` drawing the real form through `drawSettingTab(d.tab, box)` and handing the promise back. Left as
  is. Current shape, works.
- `web/plugins.js` `runAfter(node)` firing `after.drawSettings`. Left as is.
- `web/index.html` `refreshHost()` replacing `drawSettings()` in the sixteen save handlers. Left as is; the body of
  the function is C1, reported above, and not mine to change.

## Reported elsewhere and wrong, so nothing was changed

- Nine `data-act` values in other feature files looked unhandled. They are handled. My first check missed the
  method-shorthand and arrow-value forms; the files were correct and were not touched.
- `nav-search.js` hiding rows with `hidden` against a `display:flex` rule. `web/index.html:22` has
  `[hidden]{display:none!important}`, so it works. Not touched.
- `menu-icons.js` interpolating icon path data. It validates against `/^[Mm][0-9A-Za-z.,+\- ]*$/` first. Not touched.
- Escaping gaps in `analytics-kpi.js` and `analytics-table.js`. Every server string is wrapped; the unwrapped
  values are numbers, SVG geometry and in-file string constants. Not touched.

## Files touched

- `web/feat/menu.js` — one line, the `BASE` list.

`node --check web/feat/menu.js` passes. `node --check web/plugins.js` passes. All thirteen wave-1 feature files
pass `node --check`.

## Gates after the fix

```
python tests/test_feat_files.py
{"files": 28, "checks": 230}
All checks passed.

python tests/test_menu_pages.py
All checks passed. 133 ok
```

## Count

Two findings: one Critical, one Important. One fixed. One escalated because the file is frozen.
