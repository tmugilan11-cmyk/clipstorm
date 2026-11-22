# Swarm plan — 18 agents, one pass

Goal: finish the PeakCut UI overhaul that is still on the list in
`docs/port/18-clipper-ui-reference.md` §6, with zero broken controls and no
regressions. Work fast, but every agent verifies its own work before saying done.

## Hard rules (every agent reads these)

1. **`peakcut` is not a git repo.** There are no commits and no `git diff`.
   Work directly on files on disk. Do not run `git init`.
2. **Never touch a file another agent owns.** Ownership table below. If you need
   a change in someone else's file, do not make it — write a note in your report
   under `NEEDS:` naming the file, the line, and the exact change.
3. **`web/index.html` is one giant file and is written by several agents at once.**
   You may only edit inside the marker regions you were given. The regions are:
   ```
   /* ==== SWARM:css:NAME ==== */   ... /* ==== end SWARM:css:NAME ==== */
   // ==== SWARM:js:NAME ====      ... // ==== end SWARM:js:NAME ==== */
   ```
   Add your code between your own markers. If no markers exist for your name,
   append your block at the very end of the relevant area and create the markers
   yourself, then say so in your report.
4. **After any edit to `web/index.html` you must run the JS gate** and it must
   print `JS OK`:
   ```bash
   cd peakcut && python -c "import re;h=open('web/index.html',encoding='utf-8').read();open('.pctest/_jscheck.js','w',encoding='utf-8').write(max(re.findall(r'<script>(.*?)</script>',h,re.S),key=len))" && node --check .pctest/_jscheck.js && echo "JS OK"
   ```
5. **Never start a long server in the foreground.** The test server on port 8798
   is already running (`.pctest/start.sh`). Check it with
   `curl -s http://127.0.0.1:8798/healthz`. Do not restart it; if it is down, say
   so in your report instead of starting your own.
6. **No new Python dependencies.** Everything you need (ffmpeg, httpx, Pillow) is
   already installed.
7. **All user-facing text is plain English**, short, and says what will happen.
   No jargon, no emoji, no em dashes.
8. **Escape everything you interpolate into HTML** with `esc()`; never build
   `innerHTML` from server strings without it. This is a security rule, not a style.
9. **Load a skill before you start.** At minimum `frontend-design` or
   `ui-design-guide` for UI work, `python-patterns` or `fastapi-patterns` for
   backend work, `python-testing` for tests. Say which skill you used in your report.

## Ownership table

| Agent | Owns | May not touch |
| --- | --- | --- |
| A1 style-tiles | `web/index.html` region `swarm:style` (caption picker markup + CSS) | everything else |
| A2 mood-picker | `web/index.html` region `swarm:mood` (clip dialog Look tab) | everything else |
| A3 clip-stats | `web/index.html` region `swarm:stats` (clip dialog Numbers block) | everything else |
| A4 library-filters | `web/index.html` region `swarm:filters` (All videos pills + search) | everything else |
| A5 stage-checklist | `web/index.html` region `swarm:stage` (job card steps) | everything else |
| A6 running-pill | `web/index.html` region `swarm:pill` (topbar) | everything else |
| A7 job-log | `web/index.html` region `swarm:log` + `studio/server.py` `log_tail` | others' routes |
| A8 peek-cards | `web/index.html` region `swarm:peek` | everything else |
| A9 schedule-grid | `web/index.html` region `swarm:grid` | everything else |
| A10 autopilot | `web/index.html` region `swarm:auto` (settings Tools tab) | everything else |
| A11 shortcuts | `web/index.html` region `swarm:keys` | everything else |
| A12 make-my-day | `web/index.html` region `swarm:day` | everything else |
| A13 progress-viz | `web/index.html` region `swarm:heard` (job card) + `studio/jobs.py` already emits `heard_to`/`watched_pct`/`blocks_done`/`blocks_total` | everything else |
| A14 backend-gaps | `studio/api_stats.py`, `studio/api_preview.py`, `studio/server.py` (schedule route only) | `web/index.html` |
| A15 tests | `tests/test_ui_overhaul.py` + `tests/run.py` | product code |
| A16 docs | `README.md`, `AGENTS.md`, `DEPLOY.md`, `docs/port/18-clipper-ui-reference.md` | code |
| A17 reviewer | nothing (read only) | all writes |
| A18 fixer | whatever the reviewer reports | new features |

## Region marker convention

Each UI agent writes exactly one CSS block and one JS block:

```html
<style>
/* ==== SWARM:css:style ==== */
... your css ...
/* ==== end SWARM:css:style ==== */
</style>

<script>
// ==== SWARM:js:style ====
... your js ...
// ==== end SWARM:js:style ====
</script>
```

To avoid merge races, every agent appends its blocks **immediately before the
closing `</body>`** if the region does not exist yet, and its JS must be inside
the existing big `<script>` block instead if it needs the helpers (`api`, `esc`,
`toast`, `S`, `put`). In that case put it at the **very end of that script
block**, just before the closing `</script>` tag, wrapped in its own markers.
The helpers are all defined earlier in the same block, so a trailing block can
use them.

## Build list (what each agent does)

- **A1 style tiles**: replace the caption `<select>` in the Brand settings tab with
  a grid of tiles, each showing a real `<img src="/api/style/preview?style=NAME">`
  frame. Keep a hidden input with the same `id` so saving still works. Lazy-load
  images only when visible; cache nothing on the server side.
- **A2 mood picker**: a `<select data-f="mood">` in the clip dialog's Look section,
  filled from `GET /api/moods` (already mounted). It rides the existing `[data-f]`
  collector, so do not add a new save path.
- **A3 clip stats**: a collapsible "Numbers" section in the clip dialog calling
  `GET /api/stats/video?id=<the job's source id or url>`; show views/likes as
  tiles and any reasons the API returns. Fail soft with a one-line message.
- **A4 library filters**: pills All / Making / Ready / Failed with live counts over
  `S.jobs`, plus a text box filtering by hook, title and source name. Client-side
  only. Remember the choice in `S.libFilter` / `S.libQ`.
- **A5 stage checklist**: on each job card, map the known stage strings to four
  steps (Download, Listen, Pick moments, Make clips) and draw done / active /
  waiting dots next to the existing percentage.
- **A6 running pill**: a topbar slot showing "2 videos running" (or the live count)
  with a button that jumps to the running video. Driven by the existing poll.
- **A7 job log**: extend `GET /api/jobs/{jid}` in `studio/server.py` with
  `log_tail` (last 80 lines of the job's log, if one exists) and a "Show log"
  toggle in the job card that renders it in a `<pre>`.
- **A8 peek on cards**: for finished clips, show the peek still on the card if it
  exists, with a "Take stills" button that calls `POST /api/jobs/{jid}/peek`.
- **A9 schedule grid**: a 7-day by 24-hour grid in Settings > Tools fed by the
  posting queue (`GET /api/posts` if present, else `/api/schedule/preview`), with
  queued posts as chips. Read-only is acceptable; do not move posts.
- **A10 autopilot card**: a Settings > Tools card calling `GET /api/autopilot/spec`
  and `preview`, with an Install button that must send `{"confirm": true}` and a
  Remove button. Show the preview text as a `<pre>`.
- **A11 keyboard shortcuts**: a global keydown handler that does nothing unless a
  dialog or the Review view is open: arrows move, A approves, X rejects, Esc
  closes, and show a one-line hint.
- **A12 make my day**: a primary button on Overview that picks the newest video of
  the selected channel and posts a job, after one confirm dialog. No silent action.
- **A13 progress visualization**: use the `heard_to` / `watched_pct` /
  `blocks_done` / `blocks_total` fields the server now sends on each job to draw a
  real bar: how much of the video has been listened to, and one mark per part
  written. Remove the spinner-only look; keep the percentage.
- **A14 backend gaps**: check every route the UI calls exists and answers; add the
  ones that are missing (a schedule/queue listing route is likely). Verify each
  with a live `curl` and report the exact JSON.
- **A15 tests**: one plain-assert test file in the house style that checks every
  new route and every new static marker in `web/index.html`, then register it in
  `tests/run.py`.
- **A16 docs**: bring `README.md`, `AGENTS.md` and `docs/port/18-clipper-ui-reference.md`
  in line with what was actually built. Mark the built items done and delete claims
  that are no longer true.
- **A17 reviewer**: read-only audit of the whole diff area. Reports Critical /
  Important / Minor with file:line. Runs after everybody else.
- **A18 fixer**: fixes only what A17 reported, nothing new.

## Report format (every agent)

Write your report to `peakcut/docs/swarm3/NAME.md` and return only this summary:

```
status: DONE | DONE_WITH_CONCERNS | BLOCKED
skill: <the skill you loaded>
files: <files you changed>
gate: JS OK | not applicable | FAILED: <why>
live: <the curl or browser check you ran and what it printed>
needs: <changes needed in files you do not own, or "none">
concerns: <anything a reviewer should look at, or "none">
```
