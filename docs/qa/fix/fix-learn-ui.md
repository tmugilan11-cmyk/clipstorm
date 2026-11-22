# Fix report — fix-learn-ui

Fixer agent in the 40-agent fix wave for PeakCut. Binding rule set: `docs/qa/CONTRACT.md`.
Findings source: `docs/qa/FINDINGS.md`, sections `## web/feat/learn-arms.js` and `## web/feat/learn-arrows.js`.

## Files owned

- `web/feat/learn-arms.js`
- `web/feat/learn-arrows.js`

No other file was written. `web/index.html` (lead-owned) was never edited. The server was
never killed or restarted; no subagents were dispatched.

## Fixes

### 1. web/feat/learn-arrows.js:28 — blank setting name on every change row (important)

**Finding** (audit `api-learn`): `/api/learn/report` builds each change row with
`{"setting": ..., "from": ..., "to": ...}` (studio/learn_report.py:127, wired into the report
at learn_report.py:183,188), but the "Every round, before and after" card read `c.key`.
`NAMES[undefined]` is undefined, `esc(undefined)` returns `""`, so every change rendered as
"from X → Y" with a blank setting name.

**Verification**: read studio/learn_report.py:100-129 (`_change_rows` outputs `setting`/`from`/
`to`/`why`/`expect`, never `key`) and learn_report.py:183,188 (`out["changes"] = _change_rows(row)`).
The mismatch is real in code.

**Fix applied**: line 28 now reads `esc(NAMES[c.setting] || c.setting)`. The `NAMES` map keeps
its existing five setting-name keys, which is exactly what the route sends.

**Proof**: `node --check web/feat/learn-arrows.js` exit 0; `tests/test_feat_files.py` "learn-arrows.js parses / escapes what it draws" ok, full run 606 checks all passed, exit 0.

### 2. web/feat/learn-arms.js:200, 168, 170-172, 295 — A/B-testing jargon on the trial card (minor)

**Finding** (audit `x-copy`): the card speaks "arm" everywhere: heading "Two arm trial"
(line 200), "Both arms have run." (168), "Arm a is running now: ... Arm b is ..." (170-171),
toast "The trial is written down. Arm a runs first." (295). "Arm" means nothing to a beginner.

**Fix applied**: replaced arm a/b wording with plain "setting" language everywhere the card
speaks:

- Heading (line 200): "Two arm trial" → "Two-setting trial".
- Done line (168): "Both arms have run." → "Both settings have been tried."
- Running line (170-172): "Arm a is running now: X at Y. Arm b is Z, and it runs after this one."
  → "Running now: X at Y. Z runs after this one." (the internal `arm` variable still selects
  which setting is running; only the printed words changed).
- Toast (line 295): "The trial is written down. Arm a runs first." → "The trial is written
  down. The first setting runs first."

**Proof**: `node --check web/feat/learn-arms.js` exit 0; grep over the file shows the only
remaining "arm" wording is an internal code comment (line 93) and the internal `t.arm`/`runs`
record keys the server writes, not user-facing text; `tests/test_feat_files.py` "learn-arms.js
parses / draws only fixed markup" ok, 606 checks all passed, exit 0.

### 3. web/feat/learn-arms.js:178-179 — edge state explains itself with mechanism (minor)

**Finding** (audit `x-copy`): when both arms have run but no comparison sentence was sent, the
card said "PeakCut has not sent the sentence that compares them yet, so there is nothing to
quote here." — that is a description of a missing server field, not a sentence a person can use.

**Fix applied**: reworded to "Both settings have been measured. The sentence comparing them is
not written yet. It appears here once PeakCut has finished." (the suggested copy used an em
dash, which the fix-wave ban list forbids, so a full stop is used instead).

**Proof**: `node --check web/feat/learn-arms.js` exit 0; grep confirms no em dash (`—`) in the
file; `tests/test_feat_files.py` 606 checks all passed, exit 0.

## Skipped

- None of the three findings under my sections was skipped; all three held on the named lines.

## Out-of-scope pre-existing failure (reported, not fixed)

`tests/test_text_ink.py` currently fails 1 of 10 checks: "dark ink is used as page text in:
index.html .pill.live (behind it: var(--live))". That node is in `web/index.html`, which the
lead owns; neither of my two files references `.pill`, `--live`, or any literal colour
(verified by grep: 0 matches in both). This failure predates and is unrelated to my edits —
routing it to the lead.

## Gates run

- `node --check web/feat/learn-arrows.js` — exit 0.
- `node --check web/feat/learn-arms.js` — exit 0.
- `python tests/test_feat_files.py` — 75 files, 606 checks, all passed, exit 0.
- `python tests/test_text_ink.py` — 1 pre-existing failure on `index.html .pill.live`
  (out of scope, see above); all checks touching my files pass ("the feature files were
  swept too" ok).
- `python -m py_compile` — not applicable: no Python file was touched.
