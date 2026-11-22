# Fix wave: autopilot

Fixer: agent-170. Section: `## web/feat/autopilot.js` in `docs/qa/FINDINGS.md`.
Contract: `docs/qa/CONTRACT.md` (one owner per file, measured colours, no em dashes, no `!important`, no shadows, gates must pass).

## Files owned

- `web/feat/autopilot.js` (the only file written)

Read for context (not written): `docs/qa/CONTRACT.md`, `docs/qa/FINDINGS.md` (own section),
`docs/qa/audit/tools-schedule.md`, `docs/qa/audit/x-copy.md`, `web/index.html` (palette lines 12-24,
`toolsec` grep), `web/feat/schedule.js` (the `.sch-arm` precedent, lines 34-35), `tests/test_feat_files.py`.

## Fixes

### 1. Critical - `.pcauto-warn` unreadable ink (autopilot.js:21-23, now 24-26)

`color: var(--brand-ink)` (#160D05, near-black) sat on `background: var(--brand-soft)` (#2A1B10,
near-black). Measured before choosing: **1.15:1** (fails 3:1 and 4.5:1) - any scheduler warning
inside the card was invisible.

Fix: `color: var(--brand-deep)` (#FFB27A). Measured: **9.43:1** on #2A1B10, comfortably above AA
for 12px text. This is the palette's own pairing for the same panel in `web/feat/schedule.js:34`
(`.sch-arm` = brand-deep on brand-soft), so the two scheduling cards cannot drift. A plain-English
comment with both numbers now sits above the rule.

Proof: `python docs/qa/fix/contrast_pcauto.py` prints before 1.15:1, after 9.43:1; grep of the
edited file shows `color: var(--brand-deep)` at line 26. The warn text still reaches the page
through `esc(spec.warn)` (unchanged).

### 2. Minor - shared `arming` timer (autopilot.js:176, 193, now 179-204)

One module-level `arming` variable was shared by the Install and Remove buttons: arming one after
the other made the first button's timeout fire later and clear the second button's countdown, so a
button could stay armed ("Really remove it?", red) indefinitely. Reachable on the no-`ask()`
fallback path.

Fix: one countdown per button, kept on the element itself (`b.dataset.pcArmTimer`), with a
`stopArmClock(b)` helper that `disarm()` now calls first. The module-level variable is gone.

Proof: `node --check web/feat/autopilot.js` (exit 0); grep shows `pcArmTimer` at lines 182, 183,
201 and no leftover `let arming`.

### 3. Minor - toast copy (autopilot.js:253, 292, now 261, 300)

"The schedule is installed." read as odd English for a schedule; "The schedule is off this
machine." read as "disabled".

Fix, per the x-copy audit's suggested verb pair: install toast is now "The schedule is set.";
remove toast is now "The schedule was removed.". Kept to the named lines - the longer `showDone()`
messages (lines 101-104) were not named by the finding and are left alone.

Proof: grep shows the two new toasts at lines 261 and 300; `node --check` exit 0.
Note for the schedule.js owner: the matching pair there is install -> "The schedule is set.",
remove -> "The schedule was removed." (`schedule.js:254` is that agent's file).

## Verified, fix owned elsewhere

### Critical - the "Clip on a schedule" card is unreachable (autopilot.js:322, 344)

Evidence holds: `watchMount()` returns when `#toolsec` is absent, and `grep toolsec web/index.html`
returns 0 matches, so the card never mounts and the plan restore never runs. The fix (re-add
`<div id="toolsec"></div>` to `toolsPage()` and call `P.loadTools()` after it) belongs to
`web/index.html`, which the lead owns. Per the audit's own split ("the mount fix belongs to the
index.html owner"), nothing was changed in `autopilot.js` for this finding. The colour fix above
was made in the same wave, as the audit asked, so the first mounted warning is readable.

## Skips

None. Every finding's evidence held when re-checked against the code.

## Gates run

- `node --check web/feat/autopilot.js` - exit 0.
- `python docs/qa/fix/contrast_pcauto.py` - measured ratios for the pair (1.15:1 before, 9.43:1 after).
- `python tests/test_feat_files.py` - 75 files, 606 checks, "All checks passed."
- `python tests/test_text_ink.py` - 10 checks, "All checks passed."
- No Python source touched, so `py_compile` was not applicable. No server route changed; the JS
  edits take effect on the next page load, no restart needed.
