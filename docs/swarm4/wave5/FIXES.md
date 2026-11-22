# Wave 5 fixes — what was changed, and by whom

| # | Finding | Fix | By |
|---|---------|-----|----|
| F1 | 21 distinct font sizes in feature files, five of them fractional (10.5/11.5/12.5/13.5/14.5 px) | scripted pass over `web/feat/*.js`, 22 files, every fractional bumped to the next whole pixel; 17 sizes remain, none fractional | lead |
| F2 | no focus ring on `a[href]`, `summary`, text inputs | new `web/feat/polish-focus.js` (hand-written; the slot died) | lead |
| F3 | nine page-heading classes each with their own 23 px copy | new `web/feat/polish-type.js` (hand-written; the slot died) | lead |
| F4 | 4 em dashes in `web/index.html`, 1 in `meme-timeline.js`, 1 in `style-tiles.js` | replaced with plain hyphens; `node --check` re-run on all three | lead |
| F5 | `polish-copy.js` slot died | not replaced: the copy audit it was scoped for found a UI already consistent (59 verb-first labels, no exclamation marks, no TODO); audit recorded in REVIEW.md | lead |

Landed by agents, unchanged: polish-space, polish-colour, polish-icons, polish-empty, polish-errors,
polish-loading, polish-motion, polish-keyboard, polish-contrast, polish-mobile, polish-wide, polish-dark,
tests/test_a11y_pages.py.
