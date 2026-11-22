# Fix report: polish-focus, polish-empty, polish-keyboard

Fixer: agent-175, PeakCut QA fix wave (polish-rest)
Date: 2026-11-22
Findings source: docs/qa/FINDINGS.md, sections at lines 1093 (polish-focus), 1396 (polish-empty), 1403 (polish-keyboard)
Contract: docs/qa/CONTRACT.md

## Files owned

- web/feat/polish-focus.js (edited)
- web/feat/polish-empty.js (edited)
- web/feat/polish-keyboard.js (not edited, see skip below)

## Verdict summary

| # | Where | Severity | Verdict |
|---|---|---|---|
| 1 | web/feat/polish-focus.js:69 | important | FIXED |
| 2 | web/feat/polish-empty.js:39-47 | minor | FIXED |
| 3 | web/feat/polish-keyboard.js:31 | minor | SKIPPED, already implemented |

## Finding 1: invisible focus rings (web/feat/polish-focus.js:69)

**Claim (docs/qa/FINDINGS.md:1095-1098, audit x-contrast):** the focus ring drawn on sidebar links and buttons, dialog fields and pick options used `outline-color: var(--brand-line)`. The comment above it said `--brand-line` is `#FFD9BC`, a pale colour that would be visible. On the dark theme it is not: web/index.html:17 defines `--brand-line: #4A2E18`, a dark brown.

**Verified.** Grep confirms web/index.html:17 has `--brand-line:#4A2E18` and `--brand-deep:#FFB27A`. The claimed `#FFD9BC` exists only in the old light palette (web/admin.html:14), which this feature never runs against: web/admin.html loads no plugins.js and no feat files, so polish-focus.js only runs on index.html's dark theme.

**Measured grounds.** The rings sit on three backgrounds:

- `.side { background: var(--frame) }` which is `#000000` (web/index.html:38)
- `dialog { background: var(--bg) }` which is `#0A0A0A` (web/index.html:641)
- `.pick-menu { background: #2A1A12 }` (web/index.html:359)

WCAG contrast ratios, measured with Python (not by eye):

| Colour | On #000000 | On #0A0A0A | On #2A1A12 |
|---|---|---|---|
| #4A2E18 (old, --brand-line) | 1.70 | 1.60 | 1.35 |
| #FFB27A (fix, --brand-deep) | 11.9 | 11.22 | 9.48 |

A focus indicator at 1.35 to 1.70 is invisible on every background it is drawn on. The fix colour clears 3.0 everywhere it appears.

**Fix applied.**

- web/feat/polish-focus.js:69 now reads `outline-color: var(--brand-deep)` instead of `var(--brand-line)`.
- The comment above it (old lines 61-63) was rewritten in plain language with the measured numbers, stating that the old colour was the dark-brown `--brand-line` and naming the three backgrounds and their ratios. No em dashes.

**Proof.** `node --check web/feat/polish-focus.js` passed (exit 0).

## Finding 2: dead helper P.empty (web/feat/polish-empty.js:39-47)

**Claim (docs/qa/FINDINGS.md:1398-1401, audit x-dead-handlers):** the helper `P.empty({act, ...})` builds dynamic markup with `data-act="${act}"` at line 43, and no feature file ever calls it, so it is dead code; the audit also claimed the handler branch at line 86 never runs.

**Verified, in part.** Grep across web/ finds `P.empty` only at its own definition (line 39). No caller exists, so the helper is genuinely dead: that part of the claim holds.

The audit's second claim, that the handler at line 86 never runs, does not hold:

- `unify()` at line 80 emits a static `data-act="peemptyfocus"` into the empty block it draws.
- That markup is drawn through plugins.js: the repaint hook runs `watch("#jobs", drawJobs)`, and the `after.drawJobs` hook calls `unify()`.
- `wireActs` (plugins.js:150-169) dispatches `act.peemptyfocus`, which is handled at polish-empty.js:86.
- The audit's own check 3 states "line 80 peemptyfocus has handler line 86", which contradicts its verdict line.

So the live path is: draw the empty block, press the focus button, focus moves to the first field. Real and working.

**Fix applied.**

- Removed only the dead helper `P.empty` (old lines 38-47). Nothing else in the file changed: the handler, `toLinkBox`, `tail`, `unify`, `say()` and the CSS are untouched, so the fix adds no new dead code.
- Rewrote the file header, dropping the sentence advertising "one helper, PeakCut.empty(), that any feature file can call", which was no longer true.
- Added a short comment where the helper used to be: "No P.empty helper: nothing ever called it, so the empty-block markup is built inline in unify() below. One builder, not two."

**Proof.** `node --check web/feat/polish-empty.js` passed (exit 0).

## Finding 3: small close button on mobile (web/feat/polish-keyboard.js:31)

**Claim (docs/qa/FINDINGS.md:1405-1408, audit x-mobile):** `.pckb-x` is 30 by 30 px and should grow to a 44 px box at widths of 640 px and below.

**Skipped: the requested fix is already implemented.** The literal `width: 30px; height: 30px` at line 31 is true, but it is the desktop size only. The same file already contains, at lines 46-49:

```
@media (max-width: 640px) {
  .pckb-x { width: 44px; height: 44px; margin: -8px -8px 0 0; font-size: 21px; }
}
```

That is exactly the fix the finding asks for: a 44 px touch box at 640 px and below. The 30 px desktop size is fine for pointer use and sits above the WCAG 2.5.8 minimum of 24 px. Editing the file would duplicate a rule that already exists.

**web/feat/polish-keyboard.js was not edited.**

## Gates run

| Gate | Result |
|---|---|
| `node --check web/feat/polish-focus.js` | OK, exit 0 |
| `node --check web/feat/polish-empty.js` | OK, exit 0 |
| `python tests/test_feat_files.py` | All checks passed. 75 files, 606 checks, exit 0 |
| `python tests/test_text_ink.py` | All checks passed. 10 ok, exit 0 |

No Python files were touched, so no server restart is involved. The two JS edits take effect when the page is reloaded in the browser.
