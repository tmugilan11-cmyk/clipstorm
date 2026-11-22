# Fix report — web/feat/analytics-trends.js

Fixer: agent-204 (fix wave, 40-agent QA swarm). Date: 2026-11-22.
Brief: docs/qa/FINDINGS.md section `## web/feat/analytics-trends.js` (3 findings).
Rules: docs/qa/CONTRACT.md. No `dsh_browser_*` call, no subagent, no file outside my
ownership edited, server untouched.

## Files owned

- `web/feat/analytics-trends.js` (393 lines before, 399 after). Only this file was written.

## Findings verified then fixed

### 1. [minor] `.atr-x` close button 26×26 (was line 44)

- Audit evidence held: the pre-edit file had `width:26px;height:26px` literal on
  `.atr-x`, and `web/feat/polish-mobile.js` names `.chip`/`.btn`/`.icon-btn` but never
  `.atr-chip` or `.atr-x`, so the sub-44 box really renders on phones (docs/qa/audit/x-mobile.md,
  "The one rule" section).
- Fix: added one `@media (max-width:640px)` block inside the same injected stylesheet
  (now web/feat/analytics-trends.js:57-62): `.atr-chip{min-height:44px}` and
  `.atr-x{width:44px;height:44px}`. The close glyph (`.atr-x svg`) keeps its 15×15 size,
  so only the hit box grows, as the audit asked. Base desktop sizes are unchanged; inside
  ≤640 px the later media declaration wins the cascade, no `!important`, no shadow, no colour.
- Proof: `node --check web/feat/analytics-trends.js` → OK (exit 0);
  `python tests/test_feat_files.py` → `{"files": 75, "checks": 606}` all passed.

### 2. [minor] `.atr-chip` capped at 32 px (was line 42)

- Audit evidence held: `min-height:32px` literal in the pre-edit file; polish-mobile's
  sweep does not name `.atr-chip` (it is not `.chip`), so the 32 px cap stands on phones.
- Fix: same new ≤640 px block raises the chip to `min-height:44px`
  (web/feat/analytics-trends.js:60). The 44×44 close button sits inside a 44 px pill,
  which the chip's `align-items:center` handles; `.atr-chip{max-width:100%}` still wraps.
- Proof: same two gates as fix 1.

### 3. [usability] "Breakout videos" title promises the wrong chart (was line 232)

- Audit evidence held: `studio/api_trends.py:265-314` answers this channel's own videos
  ranked by views, and its docstring (lines 268-271) and note (lines 311-313) both say
  "It is not YouTube's trending chart". The block title drawn by this file said
  "Breakout videos", which a beginner reads as YouTube's public trending chart.
  docs/INSIGHTS.md:71 already explains it the same way the route does.
- Fix: renamed the block to "Your videos this range" (web/feat/analytics-trends.js:238),
  the audit's first suggested name. The help line (line 219) now carries the route's own
  explanation — "This channel's own videos in this range, most views first, with the link
  to each one. It is not YouTube's public trending chart: other channels' videos are not
  shown here." — so the beginner reads it before any response arrives, not only when the
  note lands. The loading line (line 221) and fail label (line 222) were updated to match
  ("Reading your videos this range." / "Your videos could not be read."), and the file
  header comment (lines 1-2) no longer says "breakout videos".
- Proof: `node --check` OK; route live read-only:
  `GET /api/trends/videos?days=28&limit=5` → 200 (also /api/trends/searches → 200,
  /api/trends/saved → 200). No Python file edited, so no server restart is involved in
  this fix; the JS change takes effect on the next page reload (feature files are served
  no-cache).

## Skips

- None. All three findings' evidence held at the named lines.

## Gates run

1. `node --check web/feat/analytics-trends.js` → exit 0, no syntax error.
2. `python tests/test_feat_files.py` → 75 files, 606 checks, all passed.
3. `python tests/test_text_ink.py` → 1 check failed: `dark ink is only used on the
   brand colour`, naming `index.html .pill.live (behind it: var(--live))`. That is the
   shell rule `.pill.live{color:var(--brand-ink);background:var(--live)}` at
   `web/index.html:258` (`--brand-ink:#160D05` at line 17, `--live:#EF4444` at line 21).
   `web/index.html` is lead-owned; I never wrote it, and this fix introduces no colour
   declaration at all (the new CSS only sets min-height/width/height), so the failure
   pre-exists this change and belongs to the lead's file. Every other check in that run
   passes, including `the feature files were swept too`, which covers this file.
4. Read-only curl: `/api/trends/videos`, `/api/trends/searches`, `/api/trends/saved`
   all → 200 against http://127.0.0.1:8798.

## Contract items checked

- No em dash written, no `!important`, no shadow, no colour changed (so no ratio needed).
- All markup keeps flowing through `esc(...)`; the renamed title goes through `esc(title)`
  inside `section(...)` as before.
- Only `web/feat/analytics-trends.js` written; `web/index.html` untouched.
