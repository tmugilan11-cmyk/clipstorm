# Fix report: web/feat/filters.js

Fixer agent-199, fix wave for PeakCut. One file owned: `web/feat/filters.js`.
Findings read from `docs/qa/FINDINGS.md` ("## web/feat/filters.js"), evidence checked
against the audits `docs/qa/audit/videos.md` and `docs/qa/audit/x-mobile.md` before
any change.

## Files

| File | Role |
|---|---|
| `web/feat/filters.js` | The only file this fixer owned and changed |

`web/index.html` was not edited (the lead owns it). The server was not killed or
restarted. No Python route was touched, so no restart is needed for this file.

## Finding 1 (minor): the pill ring was nearly invisible

**The finding** (`web/feat/filters.js:17-18`, audit videos). `.pcf-pill` sat on the
page with `border:1px solid var(--line)` (#1E1E1E). The pill's own background is
`var(--bg)` (#0A0A0A), the page behind the bar is `var(--bg)` too, and the clip
dialog's ground is `var(--bg)` as well (index.html:641), so the 1px ring was the only
thing separating the pill from its surroundings.

**Evidence, verified before fixing.**

- Palette read from web/index.html:19-20: `--bg:#0A0A0A`, `--line:#1E1E1E`,
  `--muted:#111111`.
- Measured with Python (WCAG `(L1+0.05)/(L2+0.05)`, sRGB piecewise linearisation):

| Candidate | On #0A0A0A (page/pill ground) | On #111111 (hover ground) |
|---|---|---|
| #1E1E1E (current, var(--line)) | 1.19:1 | 1.13:1 |
| #2A2A2A (var(--line-2)) | 1.38:1 | 1.32:1 |
| #666666 | 3.45:1 | 3.29:1 |
| **#6B6B6B (chosen)** | **3.72:1** | **3.54:1** |
| #7C7C7C (var(--faint)) | 4.74:1 | 4.52:1 |

The audit's 1.33:1 figure and this table agree on the conclusion: far below the 3:1
non-text minimum (WCAG 1.4.11). #2A2A2A (the app's standard `.btn` border) would still
fail it; #6B6B6B passes on both grounds, matches the precedent grey the grid fix
(docs/qa/fix/fix-grid.md) already introduced for the same 1.33:1 family, and stays
quieter than `--faint`.

**The fix.** `border:1px solid #6B6B6B` on `.pcf-pill`, with the measured numbers in a
plain-language comment beside the rule. The pressed pill keeps its own
`border-color:var(--brand-line)` override (line 26), unchanged. Hover, active, count
and search rules are untouched.

**Proof.** The measurement table above (Python, exit 0); the rule in the file now
reads `border:1px solid #6B6B6B` (filters.js:23); `node --check web/feat/filters.js`
exit 0; `python tests/test_feat_files.py` 606 checks all pass; the live server serves
the fixed asset (`GET /assets/feat/filters.js` 200 with the new ring, static files
take effect without a restart).

## Finding 2 (minor): `display:none!important` is on the fix-wave ban list

**The finding** (`web/feat/filters.js:33`, audit videos). The hide rule was
`[data-pcfilter="out"]{display:none!important}`.

**Evidence, verified before fixing.** The only competing `display` rule on the page is
`.empty{...display:flex...}` (index.html:262, specificity 0,1,0). No CSS in index.html
names `section[data-job]`. `data-pcfilter` is written only by filters.js, and only on
two kinds of element: `section[data-job]` cards inside `#jobs` (lines 175-177) and the
page's own empty-state block, a direct child of `#jobs` (lines 187-188).

**The fix.** The ban-list `!important` is replaced by scoped selectors that win on
specificity regardless of load order:

```css
#jobs section[data-pcfilter="out"],#jobs > .empty[data-pcfilter="out"]{display:none}
```

Specificities (1,1,1) and (1,2,0) both beat `.empty{display:flex}` (0,1,0) and every
page rule; the same two kinds of element still hide. A comment beside the rule says
why the selectors are written long.

**Proof.** `node --check web/feat/filters.js` exit 0; the old `!important` rule is
gone (`grep "display:none!important" web/feat/filters.js` returns nothing); the scoped
rule is at filters.js:41; `python tests/test_feat_files.py` 606 checks all pass.

## Finding 3 (minor): the pills were capped at 32px on phones

**The finding** (`web/feat/filters.js:17`, audit x-mobile). `.pcf-pill` carried an
explicit `height:32px`, and polish-mobile's absent sweep leaves an explicit
declaration alone, so the pills stayed 32px tall on small screens, below the 44px tap
target.

**The fix.** A mobile block added at the end of the sheet, matching the app's own
breakpoint (index.html:179 uses `max-width:640px`):

```css
@media (max-width:640px){.pcf-pill{min-height:44px}}
```

`min-height` wins over the 32px `height` above it, so the pills grow to a 44px tap
target on phones; desktop keeps the 32px look. A comment says what it does.

**Proof.** `node --check web/feat/filters.js` exit 0; the block is at filters.js:44;
`python tests/test_feat_files.py` 606 checks all pass; the live server serves the
block.

## Gates run

| Gate | Result |
|---|---|
| `node --check web/feat/filters.js` | exit 0 |
| `python tests/test_feat_files.py` | 75 files, 606 checks, all pass (filters.js parses, declares one plug-in named after itself, escapes what it draws, no absolute origin, no clashing id) |
| `python tests/test_text_ink.py` | 9 of 10 checks pass; every check that reads filters.js passes (see note below) |
| Colour measurement (Python, WCAG ratios) | exit 0, table above |
| `curl http://127.0.0.1:8798/assets/feat/filters.js` (read-only) | 200 with all three fixes in the served bytes |

## Skips

None. All three findings held up against the code and were fixed.

## Note for the lead

One `tests/test_text_ink.py` check fails, and it is not this file: `dark ink is only
used on the brand colour` reports `index.html .pill.live` with `--brand-ink` text on
`var(--live)` (#EF4444, index.html:258). That rule lives in `web/index.html`, which
this fixer does not own and did not edit; `web/feat/filters.js` contains no
`--brand-ink` reference at all, and both checks that read this file
(`a_chosen_control_uses_a_page_ink`, `the_sweep_really_reached_the_feature_files`)
pass. The failure pre-exists in the tree and needs a one-line decision on index.html:
either `color:#fff` or a pale ink on the red live pill.
