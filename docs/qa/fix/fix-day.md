# Fix report: web/feat/day.js (slug fix-day)

Fixer agent in the 40-agent fix wave. The binding rules are docs/qa/CONTRACT.md; the findings
come from docs/qa/FINDINGS.md, section "## web/feat/day.js" (three findings, all critical).

## Files owned

- `web/feat/day.js` (the only file edited)

## Fixes

### 1. Day card painted a light cream gradient under light text (all three findings, one root cause)

**Where:** `web/feat/day.js:17` in the old file (the `.day` card background), read with
`.day-help` (old line 21) and `.day-note` (old lines 27, 29).

**Finding:** the card painted
`radial-gradient(130% 190% at 0% 0%,#FFF9F4 0%,var(--brand-soft) 62%,#FFF7F0 100%)` on the
dark app. The two cream stops are near-white, so every ink the card uses fails where the
ground goes light: the help sentence ink `--text #F5F5F5`, the status grey `--dim #A3A3A3`
and the bad red `--bad #F87171`. This is a white-page remnant: the sheet was written when the
page was white and the page is black now (`--bg #0A0A0A`), the same story as
`web/feat/polish-contrast.js` records in its header.

**Evidence (verified, not taken on trust):** the gradient line and the three ink lines were
read in the source; every ratio below was measured with a script
(docs/qa/fix/measure_day.py, run and captured in this session), not estimated:

- before: `--text #F5F5F5` on `#FFF9F4` = 1.04:1 and on `#FFF7F0` = 1.03:1
- before: `--dim #A3A3A3` on the same stops = 2.42:1 and 2.38:1
- before: `--bad #F87171` on the same stops = 2.65:1 and 2.61:1

All far below the 3:1 floor for large text and the 4.5:1 floor for the 13 to 14px text this
card draws. The findings hold.

**Fix applied:** the cream stops are gone. The card now sits on a dark warm ground made of
two palette tokens, same gradient shape and anchor:

`background:radial-gradient(130% 190% at 0% 0%,var(--brand-soft) 0%,var(--brand-ink) 100%)`

No colour was invented: `--brand-soft #2A1B10` and `--brand-ink #160D05` are both in the
frozen page's `:root` block (web/index.html:17). The measured ratios on the lightest point of
the new ground (`var(--brand-soft)`, the top-left where the help sentence starts):

- after: `--text #F5F5F5` on `#2A1B10` = 15.25:1
- after: `--dim #A3A3A3` on `#2A1B10` = 6.59:1
- after: `--bad #F87171` on `#2A1B10` = 6.01:1

All above the 4.5:1 floor. On the darker stop the numbers only improve (17.61 / 7.61 / 6.94).
A plain-English comment with the measured numbers now sits above the background line, in the
tone the repo asks for. No `!important`, no shadows, no em dashes were introduced.

**Proof:** `node --check web/feat/day.js` exits clean; `python tests/test_feat_files.py`
passes all 606 checks over 75 feature files (day.js: parses, declares one plug-in, named
after itself, does not write into index.html, no absolute origin, no clashing id);
`python tests/test_text_ink.py` passes all 10 checks (dark ink still only on the brand
colour, page ink still pale, no light-theme hover washes).

## Skips

None. All three findings in the section were real and were fixed by the one change above:
findings 1 and 2 named the help sentence and the status line over the light region, finding 3
named the same gradient from the cross-page contrast audit. One root cause, one fix.

## Gates run

- `python docs/qa/fix/measure_day.py` - measured every before/after pair listed above (exit 0)
- `node --check web/feat/day.js` - clean
- `python tests/test_feat_files.py` - `{"files": 75, "checks": 606}`, "All checks passed."
- `python tests/test_text_ink.py` - 10 ok, "All checks passed."

## Notes for the lead

- The change is CSS inside the feature's own stylesheet string, so it takes effect on the
  next page load of the served file; no server restart is needed for a `web/feat/*.js` edit.
- `web/index.html` was only ever read (palette tokens and the loader check), never edited.
- The server was not killed or restarted; no subagent was dispatched.
