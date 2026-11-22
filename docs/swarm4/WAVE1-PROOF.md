# Wave 1 — Proof

Prover: `agent-35` (subagent of `lead`). Date run: 2026-11-20, 04:39–04:46 (Asia/Calcutta).
Repo: the `peakcut` folder (all commands were run from its root).
Skill applied: `verification-before-completion` (evidence before claims; no status claim without a fresh run).

Every command below was run in this session, in this order, from the repo root. Nothing here is
copied from another agent's report, and nothing is inferred from "it worked before". Where a
command printed nothing on its first line, that is stated rather than dressed up.

Toolchain actually present: `node v24.22.2`, `Python 3.15.0`, and the system `curl`.

---

## 1. `node --check` on every file in `web/feat`

`web/feat` holds **29** files (28 feature files plus `_example.js`).

Command (one run per file, unchanged form):

```
for f in web/feat/*.js; do node --check "$f"; done
```

Exact first line of output: **none — the loop produced no output at all.**
`node --check` prints nothing when a file parses. Every one of the 29 invocations exited 0.

Per-file record (command → exit code → first line of output):

| # | Command | Exit | First line of output |
|---|---|---|---|
| 1 | `node --check web/feat/_example.js` | 0 | *(no output)* |
| 2 | `node --check web/feat/analytics-audience.js` | 0 | *(no output)* |
| 3 | `node --check web/feat/analytics-charts.js` | 0 | *(no output)* |
| 4 | `node --check web/feat/analytics-kpi.js` | 0 | *(no output)* |
| 5 | `node --check web/feat/analytics-table.js` | 0 | *(no output)* |
| 6 | `node --check web/feat/analytics-traffic.js` | 0 | *(no output)* |
| 7 | `node --check web/feat/analytics.js` | 0 | *(no output)* |
| 8 | `node --check web/feat/autopilot.js` | 0 | *(no output)* |
| 9 | `node --check web/feat/day.js` | 0 | *(no output)* |
| 10 | `node --check web/feat/filters.js` | 0 | *(no output)* |
| 11 | `node --check web/feat/grid.js` | 0 | *(no output)* |
| 12 | `node --check web/feat/heard.js` | 0 | *(no output)* |
| 13 | `node --check web/feat/history.js` | 0 | *(no output)* |
| 14 | `node --check web/feat/keys.js` | 0 | *(no output)* |
| 15 | `node --check web/feat/learn.js` | 0 | *(no output)* |
| 16 | `node --check web/feat/log.js` | 0 | *(no output)* |
| 17 | `node --check web/feat/menu-icons.js` | 0 | *(no output)* |
| 18 | `node --check web/feat/menu-pages.js` | 0 | *(no output)* |
| 19 | `node --check web/feat/menu.js` | 0 | *(no output)* |
| 20 | `node --check web/feat/mood.js` | 0 | *(no output)* |
| 21 | `node --check web/feat/nav-responsive.js` | 0 | *(no output)* |
| 22 | `node --check web/feat/nav-search.js` | 0 | *(no output)* |
| 23 | `node --check web/feat/page-guard.js` | 0 | *(no output)* |
| 24 | `node --check web/feat/peek.js` | 0 | *(no output)* |
| 25 | `node --check web/feat/pill.js` | 0 | *(no output)* |
| 26 | `node --check web/feat/settings-explain.js` | 0 | *(no output)* |
| 27 | `node --check web/feat/stage.js` | 0 | *(no output)* |
| 28 | `node --check web/feat/stats.js` | 0 | *(no output)* |
| 29 | `node --check web/feat/style-tiles.js` | 0 | *(no output)* |

**Negative control** — an exit 0 is only worth something if the check can fail. A deliberately
broken file was run through the same command:

```
node --check .local_tmp/proof/broken.js
```
Exit **1**, first line of stdout: *(no stdout)*; stderr began:
```
SyntaxError: Unexpected number
```
So the 29 zeros above are real passes, not a silent no-op. The scratch file was deleted afterwards.

---

## 2. `python tests/test_feat_files.py`

Command: `python tests/test_feat_files.py`
Exact first line of output: `ok   plugins.js is there`
Exit code: **0**. Counts (`ok` lines): **230**, `FAIL`/`not ok`/`Traceback` lines: **0**.
Last two lines: `{"files": 28, "checks": 230}` then `All checks passed.`

Coverage across all 28 feature files: parses, declares one plug-in, is named after itself, is the
only owner of its name, does not write into `index.html`, escapes what it draws, uses no absolute
origin, invents no clashing id.

**Negative control (red-green)** — appended a syntax error to `web/feat/style-tiles.js`, re-ran:
exit **1**, ending `SyntaxError` / `Node.js v24.22.2`. Restored the file from a copy, re-ran:
`{"files": 28, "checks": 230}` / `All checks passed.` (exit 0). File count back to 29 and
`node --check web/feat/style-tiles.js` exit 0. This file is **not** under git (`fatal: not a git
repository`), so the restore was verified by re-running the checks rather than by `git diff`.

---

## 3. `python tests/test_menu_pages.py`

Command: `python tests/test_menu_pages.py`
Exact first line of output: `ok   there is at least one feature file   28 files`
Exit code: **0**. `ok` lines: **133**. `FAIL`/`not ok`/`Traceback`: **0**.
Last line: `All checks passed. 133 ok`

Checks every menu registration for a label of its own, its own path, a tip, a group, a real icon and
no shared path; and that each page-owning file actually draws its page (`analytics.js draws its
page`, `learn.js draws its page`, `menu-pages.js draws its page`).

---

## 4. `python tests/test_overhaul.py`

Command: `python tests/test_overhaul.py`
Exact first line of output: `brand`
Exit code: **0**. `ok` lines: **58**. `FAIL`/`Traceback`: **0**.
Last line: `All checks passed.`

**Two skips, recorded honestly:** `skip  translate.text (no engine installed)` and
`skip  translate.words (no engine installed)`. These are skips, not passes — the translation path
is not exercised on this machine because no translation engine is installed. Everything else
(brand schema/normalisation/colour cleaning/escape from the user-id path, autopilot preview and
confirmation gate, edit parse/apply leaving the original alone) passed.

---

## 5. `python tests/test_mood_sound.py`

Command: `python tests/test_mood_sound.py`
Exact first line of output: `the sound a clip can be given`
Exit code: **0**. `ok` lines: **10**. `FAIL`/`Traceback`: **0**.
Last line: `All checks passed. 10 ok`

The run also prints, by design, an unreadable-file case: `Sound funny: could not read clip.mp4 as a
video: ffprobe failed: ... moov atom not found` followed by `The clip is unchanged.` That is the
test asserting that a bad file is left alone — it is expected output, not a failure.

---

## 6. The two live routes

Command: `curl -s http://127.0.0.1:8798/healthz`
Exact first line of output: `{"ok":true}` — HTTP 200.

Command: `curl -s http://127.0.0.1:8798/assets/feat`
Exact first line of output:
`{"files":["analytics-audience.js","analytics-charts.js","analytics-kpi.js", ...` — HTTP 200.

The body lists **28** files. `_example.js` is correctly not served. That 28 matches the 28 the tests
check, so the loader and the test agree on the same set.

Every menu route was probed for status, all **200**:
`/app`, `/app/analytics`, `/app/brand`, `/app/improve`, `/app/settings/transcription`,
`/app/settings/tools`, `/app/settings/connected`, `/app/settings/ai`, `/app/settings/storage`,
`/app/settings/account`.

---

## 7. The browser

### `/app` — menu labels that are visible

Opened `http://127.0.0.1:8798/app` in the built-in browser. Title `PeakCut`, load complete. The
sidebar is grouped, and every row carries a real inline `<svg>` icon (checked in the DOM, not
assumed from the text):

| Group | Rows |
|---|---|
| *(top, ungrouped)* | Home · All videos *(badge 4)* · Review |
| **Make** | Brand · Improve |
| **Understand** | **Insights** · Transcription |
| **Set up** | Tools · Connected apps · AI · Storage · Account |
| **Creators** | New creator |

Plus the menu's own search field (`Find a page in the menu`). The footer rail shows `AI / Logfare /
0 today` and `Settings / AI key, connected apps` with a `2` notification badge.

Note the label is **"Insights"**, not "Analytics" — which matches `AGENTS.md:84` ("YouTube's
analytics page is called Insights now. The nav row says 'Insights'; internal names stay
'analytics'"). The internal address is still `/app/analytics`.

### `/app/analytics` — did it draw, and what did it say

**It drew.** Full page render confirmed by screenshot, not just by text. It said:

- Heading: `stream_sniper_369`, `Last updated 04:42`, `Last 28 days, ending 20 Nov 2026`.
- Tabs: `Overview` (active) · `Content` · `Audience` · `Traffic`.
- Range picker `Last 28 days` with `Compare: Off`.
- Six KPI tiles, each showing `–` as the value (no channel connected):
  `Views – views`, `Watch time – hours`, `Impressions – impressions`,
  `Click-through rate – %`, `Average view duration – min:sec`, `Subscribers gained – people`,
  all dated `Oct 23 to Nov 19`.
- Explanatory line: *"PeakCut's own records. Connect a YouTube channel for views, watch time and
  click-through rate. Connect a channel in Connected apps to fill these in."*
- `Views` card: `No views in this range yet.` — the documented empty state, no empty axis drawn.
- `Watch time` card: a drawn line chart with y-axis `0 / 1 / 2`, dates `Nov 7 … Nov 20`, legend
  `This range`, annotation `clips`, rising to 2 today.

No console errors (`No console lines yet`). No failing requests: everything the page fetched
returned; the `status 0` rows in the network list are resource-timing rows, which never carry a
status.

**One thing that looks wrong but is not.** The Watch time chart's y-axis unit reads `clips`. That is
deliberate and documented: with no YouTube channel connected the route serves PeakCut's own daily
counts, and `studio/api_analytics.py:245-248` returns `"unit": "views" if name == "views" else
"clips"` for exactly this path. `docs/swarm4/wave1/analytics-charts.md:5` states the intent: *"watch
time reads `minutes` when YouTube is connected and `clips` when it is not, instead of promising a
unit the data does not carry."* So the axis is honest about what the numbers are. It is a wording
oddity for a reader who expects minutes, not a defect — and it is a wave-2 item to revisit when the
real analytics route lands.

---

## What was not proven

- **No git.** `peakcut` is not a git repository, so there is no VCS diff to prove that no one else
  changed files during this run. The restore-after-negative-control step was verified by re-running
  the checks instead.
- **Two translation checks skipped** in `test_overhaul.py` (no engine installed). That code path is
  unproven on this machine, by design of the test.
- **No connected YouTube channel**, so the analytics KPIs are all `–` and the YouTube-backed branch
  of the timeseries route (which returns `"unit": "minutes"`) was not exercised live. Only the
  PeakCut-local branch was.
- **`tests/test_mood_sound.py` does not render real audio**; it checks the wiring (the word is
  stored, `render.render_clip` runs before `_add_sound`, an unknown mood falls back, a bad file is
  left alone) rather than listening to the result.

---

## Verdict

Every gate the task named was run fresh in this session and every one passed on its own evidence:
29/29 `node --check` passes (with a negative control proving the check can fail); `test_feat_files`
230/230, `test_menu_pages` 133/133, `test_overhaul` 58 ok with 2 documented skips, `test_mood_sound`
10/10, all exiting 0; both live routes answered 200 with the expected bodies and the served 28-file
list matching the tested 28; and the browser showed the grouped menu (Insights present under
Understand, real icons on every row) and an analytics page that genuinely drew, with its empty states
and its own-records explanation correct. The four caveats above are scope limits — no git, no
translation engine, no connected channel, no audio played — not failures of anything Wave 1 claimed,
and the one suspicious-looking detail (`clips` as the Watch time unit) was traced to documented,
intentional behaviour rather than left as an open doubt.

Wave 1 is proven
