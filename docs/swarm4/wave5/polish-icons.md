# polish-icons

**File I own:** `peakcut/web/feat/polish-icons.js` (244 lines). Nothing else was edited.

## What I found

The page draws icons from one mutable object named `I`, and `ic(name)` is a bare `const`. A
feature file shares that scope, so `I` can be read and added to and `ic` can be called, but it
cannot be replaced. `icons-extra.js` already seeds 3 names in; `menu-icons.js` seeds 14 more.
I scanned all 57 served feature files: they ask for 26 names by a literal string, and the page
can draw all 26. **No icon name is missing**, so I added none: inventing one breaks the rule.

Two real faults instead:

1. `ic("unknown_name")` draws the word `undefined` inside an 18 by 18 svg, not an empty box.
   The template pastes `I[name]`, which is undefined. Measured live.
2. `window.ic` was undefined. The page's `ic` is a script-scope const, so it never reaches
   window. `usage.js:71` guards on `typeof window.ic === "function"`, so its `icon("bolt")`
   at `usage.js:216` drew nothing.

## What I added

1. `window.ic`, published only if absent. Unknown names give `""`, never the word undefined.
2. `PeakCut.ic(name)` and `PeakCut.hasIcon(name)` for new files that test before drawing.
3. One scoped CSS fallback: a childless svg inside `#app` gets `font-size:0` and a transparent
   colour, so the word stops painting but the box keeps its size. No `!important`, no motion.
4. A Tools card that re-runs the scan live, so the claim is checkable, not just asserted.

The scanner strips comments and strings first, so a name in a comment is not counted.

## `node --check`

```
$ node --check web/feat/polish-icons.js
NODE_CHECK_OK
```

Exit code 0. Node printed nothing. Suite:

```
$ cd peakcut && python tests/test_feat_files.py
{"files": 57, "checks": 462}
All checks passed.
```

## Measured, live at http://127.0.0.1:8798/app

- 57 files scanned, 26 names asked for, 0 missing. Tools card drew 26 rows, 0 "missing".
- `window.ic` is a function. `ic("unknown")` gives `""`, never the word undefined.
- `ic("bolt")` paints an 18 by 18 svg, one child, empty text.
- 27 svgs on the page: 0 childless, 0 holding the word undefined.
- A real icon keeps `font-size: 14px`. The empty box stays 18 by 18, so nothing shifts.

## Still missing

- Two files also guard on `window.esc`, which the page never publishes. Another file should.
- Three files draw icons on a 24 grid, not the page's 256: `day.js:61`, `filters.js:86`,
  `style-tiles.js:190`. Not mine to edit.
- The scan reads literal names only. 15 sites build names at run time; a wrong one would paint
  the word undefined until the CSS rule catches it.
