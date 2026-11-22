# polish-motion

One scoped stylesheet, added on file load the way `heard.js` does it. `load()` was
wrong: it only runs when Settings > Tools opens, so a hover elsewhere would wait.
File I own: `peakcut/web/feat/polish-motion.js` (2,997 bytes, 62 lines).

## What I added

- **120 ms colour transition** on `button`, `a`, `.pill`, `label.ck` inside `#view`,
  `#toolsec` and `dialog`. Properties named: `background-color`, `border-color`,
  `color`. No `transition: all`.
- **160 ms opacity reveal** on `dialog[open]`, keyframes `pcPolishIn`.
- **All off** under `prefers-reduced-motion: reduce`: `transition-property:none`,
  `transition-duration:0s`, `dialog[open]{animation:none}`. Off, not shortened.

No `!important`, no `transform`, no `infinite`, no shadow, no new dependency.

## Gates

```
$ node --check web/feat/polish-motion.js && echo "JS OK"
JS OK
$ cd peakcut && python tests/test_feat_files.py
All checks passed.
```

## Measured

`grep -o` over `web/index.html` and all `web/feat/*.js`: **81** `transition:` (44
page, 37 feat), **49** `animation:` (25/19), **25** `@keyframes` (12/10), **18**
`infinite` (10/7). 23 of 52 feat files carry motion; durations had drifted across
100, 140, 150, 180, 200, 250, 320, 450, 500, 800 ms for one class of interaction.

Read live at `http://127.0.0.1:8798/app`: `#pcss_polish-motion` present, 1,186
chars, slug in `PeakCut._order`. `#view .btn` now `transition-duration: 0.12s`
(was 0.15s, index.html line 746). `.side` nav item still `0.15s, 0.15s, 0.15s`,
so the scope holds. `dialog#formdlg` open gives `animation-name: pcPolishIn`,
duration `0.16s`, `transform: none`. No `transform` or `!important` in my rules.

## Left alone, and why

- **index.html line 746**, the page's own 150 ms colour transition. Already right,
  and page chrome is not mine to restyle. The other 46 hover rules are colour only.
- **`transition:width` on `.bar i` (800 ms, line 537), `.tr-bar i` (500 ms, line
  813), `heard.js` (450 ms), `analytics-audience.js` (450 ms).** A bar changing
  width reports a number; it is not moving text someone is reading.
- **`grid-template-rows` on `.composer-opts` / `.att` (lines 301, 306).** These do
  move content, but they are in the frozen page. Flagged, not fixed.
- **The 18 looping animations** and the **`transform` entrances** (`rise`, `ntin`,
  `tr-in`, `tabin`). They mean "still running" or move content. Not mine.

## Still missing

- `heard.js` line 10 animates `width` at 450 ms with no reduced-motion guard on the
  transition itself (only its glow is guarded). Another agent's file.
- `style-tiles.js`, `formats.js`, `pill.js`, `stage.js`, `live.js` and
  `analytics-realtime.js` run `infinite` animations on six screens.
- I read the reveal's computed style with `open` set by hand: that proves the
  animation is attached, not that the paint is smooth on a slow machine.
