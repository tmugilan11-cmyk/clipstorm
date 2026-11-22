# polish-colour

Skill loaded: make-interfaces-feel-better. I own `peakcut/web/feat/polish-colour.js` (64 lines, 2654 bytes). No other file touched.

## What I added

The palette lives once at `peakcut/web/index.html` lines 30 to 34. Some feature files
spelled those colours out as hex. My file calls `PeakCut.css(...)` with a scoped sheet
re-declaring only colour properties that held a literal, pointing them at the variable
that already meant the same thing, then `PeakCut.add("polish-colour", {})`.
- 25 selectors, all `background:var(--bg)`. Each was `background:#fff`, exactly `--bg`.
- `body .pcrun.btn`: `border-color:var(--brand-line)`, `background:var(--brand-soft)`.
- `body .pcrun.btn.is-rec`: `background:var(--bad-soft)`. `#FFF3F3` was that tint.

Every selector starts with `body`, so one extra element selector beats single-class rules
in other files whatever order their sheets append. No `!important`, no page, no handlers.

## Counts

```
feature files scanned (mine excluded)     58
   containing raw hex                     21
   raw hex tokens                         55
   distinct colours                       24
distinct colours mapped                    4
mapped occurrences                        31
```

`#fff` to `--bg` covers 23 of 23 background declarations, on 25 selector names (two rules
carry comma pairs). `#FFF7F0` to `--brand-soft` 1 of 2 uses, `#FFD9BC` to `--brand-line` 1,
`#FFF3F3` to `--bad-soft` 1. Four `#fff` are foreground and stay: `.akhelp[aria-expanded=
"true"]` and `.pcerr-btn:hover` colour, `.an-ret .rdot` fill, `.stile-check` colour.
`polish-dark.js` appeared mid-task with 56 deliberate dark tokens, not strays, excluded.

## Gates

`cd peakcut && node --check web/feat/polish-colour.js` gives no output, exit 0.
`python tests/test_feat_files.py` gives `{"files": 59, "checks": 478}`, then
`All checks passed.` My own 8 checks all report ok.

## What I measured

Computed styles on `/app`, one probe per selector, `--bg` set to `rgb(1,2,3)`:
```
--bg selectors 25 / tracking --bg 25
.pcrun.btn bg rgb(255,242,232)=#FFF2E8 | bd rgb(255,217,188)=#FFD9BC  both track
.pcrun.btn.is-rec bg rgb(253,236,238)=#FDECEE  tracks
```

An early pass said 24 of 25 because `document.hasFocus()` was false, not the sheet.

## What is still missing

20 distinct colours left, each with a reason. `#D4CAC3` (`history.js:24`, `peek.js:28`) sits
16 from `--line-2`; mapped then removed, since both rest on it and a mapped hover would
equal rest. The `analytics-audience.js` ramp (`#FFE6D3 #FFBE8C #FF9448 #D9691A`) is a brand
accent scale, out of scope. `pill.js` hover and recording steps (`#FFEEDF #FFC79E #7A3406
#FFD3D5 #FFB9BD #9E121B #FFE9EA`) are 4 to 62 out, and collapsing them flattens two-state
buttons. `#FFF7F0` in the `day.js` radial gradient is a stop, not a surface.
