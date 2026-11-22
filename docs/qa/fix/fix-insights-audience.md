# Fix report - web/feat/analytics-audience.js and web/feat/analytics-retention.js

Fixer: agent-195 (fix wave, 40-agent QA swarm). Date: 2026-11-22.
Brief: docs/qa/FINDINGS.md (Insights section) plus the audit report
docs/qa/audit/insights-audience.md (agent-138). Rules: docs/qa/CONTRACT.md.
No `dsh_browser_*` call, no subagent, no file outside my ownership edited,
server untouched (read-only curl only).

## Files owned

- `web/feat/analytics-audience.js`. Only this file and the retention file below were written.
- `web/feat/analytics-retention.js`.

## Findings verified then fixed

### 1. [important] "New viewers" series invisible: dark ink on a dark track (audience.js .aa-dot.new / .aa-fill.new)

- Audit evidence held: both rules set `background:var(--brand-ink)`, which is
  #160D05 (web/index.html:17), drawn on the `.aa-track` background `var(--muted)`
  = #111111. A white-page remnant.
- Measured (docs/qa/fix/measure_audience.py, exit 0): #160D05 on #111111 = 1.02:1,
  far below the 3.0 non-text minimum, so the "new" bars were invisible. The fix
  colour #22D3EE on #111111 = 10.45:1 (on #0A0A0A = 10.96:1). #22D3EE is already
  in the app, used by `.aed-chip.ai` in web/feat/audio-edit.js:81-82, so no new
  palette colour is introduced.
- Fix: `.aa-dot.new` and `.aa-fill.new` now use `background:#22D3EE`, with a
  plain-English comment above the injected stylesheet recording the measured
  1.02:1 old and 10.45:1 new. No text colour changed, no `!important`, no shadow.
- Proof: `node --check web/feat/analytics-audience.js` -> OK (exit 0);
  measured ratios above; `python tests/test_feat_files.py` all passed (below).

### 2. [usability] Heatmap hour labels set at 10px (audience.js .aa-h)

- Audit evidence held: `.aa-h` carried `font-size:10px`. Contrast itself passes
  (the labels use `--faint`, lifted to #A0948C inside `#main` by
  web/feat/polish-contrast.js, 6.39:1 on #111111), so this is a comfort fix, not
  a contrast fix. This file is one part of a six-file 10px finding; the other
  five files (audio-page.js, history.js, keys.js, pictures.js) belong to other
  agents and were left to them.
- Fix: `.aa-h` raised from 10px to 11px (web/feat/analytics-audience.js:26).
- Proof: `node --check` OK (exit 0).

### 3. [usability] No-token note in audience.js was a dead end

- Audit evidence held: the server note (studio/api_analytics.py:338) reads
  "Viewer types, countries and hours come from YouTube. Connect a channel to
  see them." and paint() drew it as plain escaped copy with no way to Connected
  apps. Five sibling analytics cards already link it, for example
  analytics-traffic.js:141 with `.atf-say a`.
- Fix: paint() now appends `Check <a href="/app/apps">Connected apps</a>.` when
  the note matches /connect a channel/i, and a `.aa-note a` rule was added
  matching `.atf-say a` (color:var(--brand-deep) #FFB27A, 10.70:1 on #111111,
  weight 600, no underline, 1px bottom border). The note text itself stays
  escaped via esc().
- Proof: read-only curl against the live server:
  `GET /api/analytics/audience?days=7` -> HTTP 200 with body
  `{"source":"peakcut","days":7,...,"note":"Viewer types, countries and hours come from YouTube. Connect a channel to see them."}`
  so the phrase the fix keys on is the real one the route sends. `node --check` OK.

### 4. [usability] Heatmap gave no swipe hint on a narrow screen

- Audit evidence held: the 7x24 map is `min-width:520px` inside
  `.aa-scroll{overflow-x:auto}` with no hint; on a 390px phone about 130px of
  the day is visible and the rest hides off-screen with no sign of it.
- Fix: blockHours now emits a hidden hint `<p class="aa-swipe" hidden>Swipe to
  see the whole day</p>` under each scroll area, and a new markSwipe(root)
  helper, called from paint() right after the markup lands, shows the hint only
  when the scroll area really overflows (scrollWidth > clientWidth + 1). The
  hint is 11px `--faint`, so it never shows when there is nothing to scroll.
- Proof: `node --check` OK; the same curl above answers `"hours":[]` without a
  channel, so in the no-token state the map is absent and the hint stays hidden.

### 5. [usability] Retention fail state was a dead end

- Audit evidence held: the curveErr branch of web/feat/analytics-retention.js
  drew "Could not read the retention curve for this video." plus the server
  body and a retry button, with no link. The server body
  (studio/api_analytics.py:411) is an HTTP 400 that reads "Retention comes from
  YouTube. Connect a channel under Connected apps."
- Fix: a linked(t) helper was added: it escapes the text with esc() and, only
  when the phrase is present, turns "Connected apps" into a link to /app/apps.
  The curveErr branch now draws `${linked(st.curveErr)}`, and a
  `.an-ret .rerr a` rule styles the link with color:inherit, weight 600,
  underline, so it inherits the error text pair (#F87171 on #2B1416, measured
  6.25:1). The fix is scoped to curveErr only: the videos route without a token
  answers 200 with PeakCut's own posts (api_analytics.py:280-292), so listErr
  can never carry the connect phrase.
- Proof: `node --check web/feat/analytics-retention.js` -> OK (exit 0);
  measured pair above.

## Skips

- None. All five findings' evidence held at the named lines. The other five
  files of the 10px finding belong to other agents and were not touched.

## Gates run

1. `node --check web/feat/analytics-audience.js` -> OK (exit 0).
2. `node --check web/feat/analytics-retention.js` -> OK (exit 0).
3. `python tests/test_feat_files.py` -> `{"files": 75, "checks": 606}`, all checks passed.
4. `python tests/test_text_ink.py` -> 9 of 10 checks passed. The one failure is
   `index.html .pill.live`, a rule in lead-owned web/index.html:258
   (`color:var(--brand-ink)` behind `--live:#EF4444`). Pre-existing, not caused
   by these edits: the two rules this report changed set `background`, not
   `color`, so the check never collects them, and index.html was never written.
5. `python -m py_compile docs/qa/fix/measure_audience.py` -> OK (exit 0).
6. Read-only `GET /api/analytics/audience?days=7` -> HTTP 200 (body quoted above).

No Python file was edited, so no server restart is involved in this fix; the
two JS changes take effect on the next page reload (feature files are served
no-cache). The folder is not a git repository ("fatal: not a git repository"),
so no baseline diff was possible; the pre-edit evidence is quoted from the
audit report instead.
