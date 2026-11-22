# fix-usage — web/feat/usage.js

Fixer: agent-177 (subagent of lead), fix wave, 2026-11-22.
Owned file: `web/feat/usage.js` only. No other file touched; `web/index.html` left to lead.
Source findings: `docs/qa/FINDINGS.md` section "## web/feat/usage.js" (line 690); audit `docs/qa/audit/apps-ai-usage.md`.

## Verification

Every finding was checked at its named line in the pre-fix file before any edit. All 8 held: the quoted code was present and the cited backend behaviour confirmed in `studio/usage.py` / `studio/server.py` / `web/feat/menu-pages.js`. Nothing skipped, nothing invented. Colours were measured, not felt (ratios below).

## Fixes

### 1. Wrong service copy (important) — line 252

The panel said "One model answers every call listed below." That is false on two counts: `studio/usage.py:63` takes `(ai.models() or [""])[0]`, i.e. the current provider's model only, and `forget_all()` (`studio/usage.py:39-41`) clears only `_brief`, so call rows persist across provider switches — a row answered by an older model stays listed.

Now: "The service in use now answers new calls." with a rationale comment at line 251 recording both backend facts.

### 2. Invisible zero tick on the chart (important) — lines 36-38

`.usg-plot .none` (fill) and `.usg-plot .base` (stroke) used `--line-2` #2A2A2A on the chart's `--bg` #0A0A0A. Measured: **1.38:1** — fails the 3:1 WCAG 1.4.11 requirement for meaningful graphics; the 2×1 px tick at line 158 was effectively invisible.

Measured alternatives with the WCAG formula (L1+.05)/(L2+.05): `--faint` #A0948C on #0A0A0A = **6.70:1** (passes; polish-contrast.js's header claims 7.24 — my own measurement is 6.70), `--dim` #A3A3A3 = 7.85:1, `--faint` on `--muted` #111111 = 6.39:1. Chose `--faint`: the palette's own quiet grey, resolved inside `#main` by `polish-contrast.js:29`, so no new colour enters the theme. Both rules now use `var(--faint)` (base also gets `stroke-width:1`), with the measured numbers in the CSS comment.

### 3. Purposes beyond 8 dropped silently (minor) — lines 215-218, 230-231

`got.slice(0, 8)` discarded the rest without a word, while `studio/usage.py:76-78` sends every purpose uncapped. Now the trimmed count is kept (`smaller = got.length - shown.length`) and, when non-zero, a sub line states it: "and N smaller purpose(s), still counted in the totals above." Singular/plural handled.

### 4. Exact token total hidden in a title attribute (minor) — lines 131-133

The visible figure came from `tokens()` (abbreviates above 10,000); the exact number lived only in a hover-only `title`. Now the title is gone and the sub line shows the exact figure in text: "N exactly, read in and written out together" (or "Read in and written out together" when unknown).

### 5. Tip promised a cost the page disclaims (minor) — line 309

Plug-in tip said "How much AI was used, and what it cost" while the page's own cost card says "Not known". Now: "How much AI was used, in calls and tokens".

### 6. Wrong add-a-key instruction for non-admins (minor) — lines 243-247

"Add one under AI in Settings" is unreachable for non-admins: `studio/server.py:1409-1412` gates `/api/ai` behind `_admin(request)`, and `menu-pages.js:51` marks the page `admin:true`. The admin-detection helper `mayChangeAI()` (lines 86-92) mirrors `menu-pages.js:74-79` `owner()`: `PeakCut.state().status.user.is_admin` (with `auth.py:252` `local_user()` being `is_admin=True` when accounts are off, so default single-user installs get the admin branch). Non-admins now get the phrasing the audit verified elsewhere: "Ask the owner to add one under AI in Settings." The `/app/settings/ai` link is kept in both branches.

### 7. Axis dates readable only on hover (minor) — lines 192-206

With up to 30 daily bars, only the first and last got axis labels and per-bar dates lived in hover-only `<title>`s. Now a middle label is added when it does not collide: indices `[0]`, plus `floor((n-1)/2)` when `n > 2` and it is strictly interior, plus `n-1` when `n > 1`, joined into the `.usg-axis` spans. Keyboard/touch readers get the shape of the range without a pointer.

### 8. Stale header reference (minor) — line 4

Header comment cited `studio/server.py:1374`; the actual route `@app.get("/api/usage")` is at `studio/server.py:1398`. Comment corrected.

## Gates

- `node --check web/feat/usage.js` → `NODE_CHECK_OK`, exit 0.
- `python tests/test_feat_files.py` → 75 files, 606 checks, "All checks passed." exit 0. usage.js rows all ok: parses, declares one plug-in, named after itself, only owner, does not write into `index.html`, draws only fixed markup, no absolute origin, no clashing id.
- `python tests/test_text_ink.py` → 10 ok, "All checks passed." exit 0.
- Read-only curls against the running server: `GET /api/usage` → 200, `GET /app/ai-usage` → 200. No restart performed; server-side Python was not edited by this agent, so nothing here depends on a restart.

## Notes

- The workspace is not a git repository (`git diff` exits 128), so no before/after diff exists; line numbers above refer to the final 327-line file (17,732 bytes, sha256 c72e47c20b3e2098118f6888e7443892a158b2d01c1b4339aa27af51a137b3a8).
- One block outside my eight edits — the final count/tokens/exact formatting block (lines 94-99) — reads slightly differently from my first-pass transcription. With no git history to check against, no claim is made about its history; its current state is correct and passes all gates.
- No em dashes, no `!important`, no shadows, no new colours introduced.
