# fix-polish-critical — web/feat/polish-errors.js and web/feat/polish-contrast.js (agent-174)

Fix wave for PeakCut. Rule set: docs/qa/CONTRACT.md. Findings read from the sections
"## web/feat/polish-errors.js" and "## web/feat/polish-contrast.js" in docs/qa/FINDINGS.md,
both raised by docs/qa/audit/x-contrast.md.

## Files owned

- web/feat/polish-errors.js
- web/feat/polish-contrast.js

## Fixes

### 1. web/feat/polish-errors.js:281 (was 277) — critical: hover text unreadable at 2.77:1

- Finding: `.pcerr .pcerr-btn:hover{background:var(--bad);color:#fff}` paints white on the
  light red `--bad` hover ground. 12px button labels ("Retry", "Dismiss") need 4.5:1.
- Verified before editing: the real palette was read from web/index.html:21
  (`--bad:#F87171;--bad-soft:#2B1416`) and measured in Python (exit 0):
  white on #F87171 = 2.77:1 (fails), base state `--bad` on `--bad-soft` = 6.25:1 (fine).
  The finding holds exactly.
- Fix: the hover ground is darkened to the app's own deep red #C53030 (already used by the
  account menu at web/index.html:743), white text kept. Measured white on #C53030 = 5.47:1,
  which passes 4.5. The hover still changes colour only, as AGENTS.md asks. The alternative
  #B91C1C measured 6.47:1 but would have added a colour the page does not use, so #C53030
  was chosen for palette consistency. A plain-English comment above the CSS block records
  all three measured numbers.
- Proof: measured table (Python, exit 0); `node --check web/feat/polish-errors.js` -> OK;
  gates listed below. No `!important`, no shadows, no em dashes.

### 2. web/feat/polish-contrast.js:10-15 — minor: header numbers did not match measurement

- Finding: the header claims 8.10 / 4.79 / 7.24 / 6.86 / 5.68; measured 7.85 / 4.74 / 6.70 /
  6.39 / 5.63. Text 18.16 and #75695F = 3.72 already matched. The header's "None of them are
  estimates" line was therefore not true of its own numbers.
- Verified before editing: every pair re-measured in Python (exit 0) with the standard WCAG
  formula (the same one the file's own `ratio()` implements), from the hex values in the
  `:root` block of web/index.html (lines 17-21): --text #F5F5F5 on --bg #0A0A0A = 18.16;
  --dim #A3A3A3 on --bg = 7.85 (was 8.10); --faint #7C7C7C on --bg = 4.74 (was 4.79);
  --faint #A0948C on --bg = 6.70 (was 7.24); --faint #75695F on --bg = 3.72 (unchanged);
  --faint #A0948C on --muted #111111 = 6.39 (was 6.86); on --brand-soft #2A1B10 = 5.63
  (was 5.68). The finding holds.
- Fix: the table (lines 10-15) rewritten to the measured values. "None of them are estimates"
  is now true: every number is reproducible from the frozen page's `:root` block.
- Two further header numbers, named by the same fix instruction ("re-measure and rewrite the
  header numbers"), did not hold against the code and were corrected to the measured truth:
  - Line 17-18 (.bell .dotn): the header said "now uses the palette's dark ink, 5.9:1 on the
    same red". web/index.html:715 actually paints `.bell .dotn` white on #C81E28; measured
    5.72:1. Rewritten to that, with the line reference.
  - Line 24-25 (sidebar): the header said "--frame-dim, which measures 6.55 on #1E1612".
    The sidebar (.side) paints `var(--frame)` #000000 behind --frame-dim #8A8A8A, measured
    6.08:1. #1E1612 is the .stream card background (web/index.html:117), not the sidebar's
    ground. Rewritten to the measured pair and ground.
- Proof: measured table (Python, exit 0); `node --check web/feat/polish-contrast.js` -> OK.

## Skips

None. Both findings held: evidence was reproduced by measurement before either edit was made.

## Gates run

1. Contrast measurement, Python batch, exit code 0: white on #F87171 = 2.77; white on
   #C53030 = 5.47; white on #B91C1C = 6.47; --bad on --bad-soft = 6.25; --text on --bg =
   18.16; --dim on --bg = 7.85; --faint root #7C7C7C on --bg = 4.74; --faint #A0948C on
   --bg = 6.70; #75695F on --bg = 3.72; #A0948C on --muted = 6.39; #A0948C on
   --brand-soft = 5.63; white on #C81E28 = 5.72; #8A8A8A on #000000 = 6.08.
2. `node --check web/feat/polish-errors.js` -> OK (exit 0).
3. `node --check web/feat/polish-contrast.js` -> OK (exit 0).
4. `python tests/test_feat_files.py` -> {"files": 75, "checks": 606}, All checks passed,
   exit 0 (includes both owned files: parse, one plug-in named after itself, escapes its
   markup, no clashing id, no absolute origin).
5. `python tests/test_text_ink.py` -> All checks passed. 10 ok, exit 0.
6. Read-only curl against the running server: `/` -> 303 (redirect, as the audit also saw);
   `/assets/feat/polish-errors.js` -> 200; `/assets/feat/polish-contrast.js` -> 200.

Notes for the lead: no Python file was touched, so no py_compile gate applies and no server
restart is needed for this fix (both changes are static feature files; the page picks them
up on reload, and the lead's final restart covers everything anyway). Every changed colour
was measured first; the frozen page's `:root` block was read but not edited.
