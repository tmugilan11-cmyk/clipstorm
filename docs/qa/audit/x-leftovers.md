# Audit report — x-leftovers (cross-cutting)

Auditor: agent-166 (cross-cutting), 40-agent QA swarm for PeakCut.
Scope: `web/index.html` + `web/feat/*.js` — leftover em dashes, TODO/FIXME, placeholder
text, console.log/debug lines, dead code the page never calls, dead handlers, dead hooks,
keyboard-shortcut drift, route cross-check. Server spot-checked live at http://127.0.0.1:8798.
No browser was used (lead owns the browser during the audit); all checks ran with grep,
file reads, two offline scan scripts, and curl.

## Verdict

**Clean bill. Zero findings.** Every category in the brief came back empty; every
apparent hit was investigated and resolved as an intentional, documented pattern
(details below, so the next auditor does not re-chase them).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| — | — | No findings. All checks below passed; apparent hits were verified intentional. | — | — |

## Owned files

- `web/index.html` (whole-file cross-cutting sweep)
- `web/feat/*.js` — 84 feature files + `web/feat/_example.js` template (85 files in `web/`)

## Checks run and results

1. **Em/en dash leftovers** — regex `[—–]` (U+2014, U+2013) over `web/feat/*.js` and
   `web/index.html`. Exactly 1 match: `web/index.html:2138`, the posts-table cell
   `` `${p.views ?? "–"}` `` — an en dash used as the deliberate "no views recorded"
   glyph, which follows AGENTS.md's rule that a number must come from somewhere (a
   blank would be dropped, a zero would be a false claim). **Intentional, not a
   leftover.** No em dash (U+2014) appears anywhere in the web layer.
2. **TODO/FIXME markers** — grep `TODO|FIXME|XXX|HACK|TBD` over both targets: 0 matches.
3. **Placeholder text** — grep `lorem|ipsum|Lorem|Your text here|dummy|foobar|PLACEHOLDER`:
   0 matches.
4. **Debug console lines** — grep `console.(log|debug|warn|error|info)`:
   - `web/index.html`: 0 console lines.
   - `web/feat/*.js`: 8 matches, all the same guarded pattern — a `try/catch` whose
     `catch` emits one `console.warn("[PeakCut] …")` so a silently-swallowed failure is
     still reported. Intentional error reporting, not debug leftovers:
     `feat/analytics-export.js:215`, `feat/analytics-retention.js:428`,
     `feat/analytics-table.js:307`, `feat/page-guard.js:76` (duplicate page
     registration warning), `feat/polish-icons.js:239`, `feat/polish-motion.js:56`,
     `feat/review-hooks.js:117`, `feat/review-hooks.js:135`.
5. **Risky evaluators** — grep `eval(|new Function(|document.write(`: 0 matches.
   Also `debugger|console.trace|alert(`: 0 matches.
6. **Template file** — `web/feat/_example.js` (5 lines) registers a demo page and toast.
   `studio/server.py:473-474` builds the `/assets/feat` list excluding underscore-prefixed
   files, so the template never ships to users and the page never loads it. **Intentional
   copy-me template**, not dead weight to delete.
7. **`after` hooks** — 12 registrations across feat files; all use hook names the page
   actually fires (`drawShell`, `drawSettings`, `drawClipDlg`). `web/plugins.js` watches
   only `#jobs/drawJobs`, `#ov/drawOverview`, `#cbody/drawCreator`, `#clipdlg/drawClipDlg`,
   `#sform/drawSettings`, `.topbar/drawShell`. No dead hook, no typo'd hook name.
8. **Dead handlers / broken buttons (forward check)** — every `data-act` used in
   `web/index.html` + `web/feat/*.js` resolves to a real handler:
   - index.html's own delegated listener (`web/index.html:3109-3460`) handles 83 built-in
     acts (`go`, `aimodels`, `aisave`/`aitest`, `trmodels`, `trsave`/`trtest`, `tlschedule`,
     `brandsave`, `menu`, `collapse`, `toggleopts`, `focusurl`, `step`, `tab`, `pickfile`,
     `addmore`, `closedlg`, `openaudio`, `openclip`, `newcreator`, `copy`, `copyall`,
     `histkeep`, `logout`, `pwsave`, `delclip`, `dlall`, `seldl`, `selclear`, `selall`,
     `seldel`, `delcreator`, `delaccount`, `deljob`, `chadd`, `chdel`, `spick`, `chmain`,
     `golive`, `stoplive`, `clipnow`, `resendverify`, `tour`, `settab`, `updhow`, `updlater`,
     `storopen`, `storchange`, `storpick`, `storsave`, `storcancel`, `appsetup`, `copytext`,
     `appsave`, `zsetup`, `zsave`, `zforget`, `zrefresh`, `bell`, `feedback`, `report`,
     `acctmenu`, `bellread`, `ntgo`, `csave`, `cdiscard`, `pause`, `pcancel`/`pretry`,
     `ssave`, `plansave`, `testalert`, `accremove`, `remake`, `noteclip`, `transclip`,
     `rvapprove`/`rvreject`, `rvskip`, `peekclip`, `postnow`/`postqueue`).
   - every custom act used in a feat file has a handler in that file (spot-verified by
     hand: `pchistkeep`→`feat/history.js:243`, `piconsscan`→`feat/polish-icons.js:225`,
     `pckbopen`→`feat/polish-keyboard.js:319`, `pclstor`→`feat/polish-loading.js:95`,
     `pickstyle`→`feat/style-tiles.js:238`, `usgload`→`feat/usage.js:271`).
   - `pcpage` is routed by `web/plugins.js` itself (page plugin).
   - **Trap recorded for the next auditor:** `pcrungo` looks unhandled to a text grep
     because `feat/pill.js:128` creates the button dynamically
     (`el.dataset.act = "pcrungo"`); the handler is alive at `feat/pill.js:154`.
     False positive — do not "fix" it.
   Result: no dead handler, no button that does nothing.
9. **Dead code (backward check)** — offline scan of `web/index.html`'s script:
   145 top-level function/arrow declarations, **0 with no caller**. 113 element ids
   defined; the 26 initially "never targeted by JS" all resolved as false positives of a
   narrow `$("#id")`-only regex — they are read via other helpers: `#o_from` via
   `n("#o_from")` (`web/index.html:1635`), `#addform` via the submit listener
   (`web/index.html:3020`), `#rv_job` via `t.id === "rv_job"` (`web/index.html:3055`),
   `#tl_schbox` via `toolBox("tl_schbox",…)` (`web/index.html:3138`), the `br_*` fields
   via `val("br_…")` (`web/index.html:3181-3184`), `#ed_*` are heading anchors in the
   clip editor, `#brandAspects` via `$$("#brandAspects …)` (`web/index.html:3187`).
   No dead markup, no dead function.
10. **Keyboard shortcuts** — `web/feat/keys.js` (173 lines) checked line by line. Every
    shortcut clicks a button the page already renders (`rvapprove`/`rvreject`/`rvskip`
    inside the cursor card at `feat/keys.js:86-93`, `closedlg` at `feat/keys.js:101` —
    all handled at `web/index.html:3443-3444` and `:3209`), so shortcuts cannot drift
    from real logic. Guards verified: typing targets, `#formdlg` open, any other open
    dialog, the tour root (created at `web/index.html:1047` as `root.id = "tour"` — the
    guard at `feat/keys.js:70` is correct), `e.repeat`, and modifier keys. The file's
    header documents why the review page's own a/x/s keys are left alone (index.html
    wires them before plug-ins load; rebinding would send two decisions per press).
    No shortcut fires while someone types; no double-decision risk.
11. **Route cross-check** — every `/api/…` address the page calls exists in `studio/`.
    `server.py` has ~101 `@app` routes plus ~90 `@router` routes across the `api_*.py`
    modules and 2 `@router.api_route` pairs (`studio/api_memesound.py:198`
    `/api/memesounds/play/{slug}` GET/HEAD, `studio/api_sound.py:121`
    `/api/sounds/{kind}/{mood}` GET/HEAD). Template-heuristic "misses" were all false
    positives (e.g. `/api/upload/${s.id}/${i}` → `server.py:1013` `/api/upload/{upid}/{n}`;
    `/api/jobs/${D.jid}/clips/${D.cid}/render` → `server.py:1081`;
    `/api/live/${d.j}/clip` → `server.py:1382`). Clean.
12. **Live HTTP spot-checks** (curl, http://127.0.0.1:8798) — 200 on `/app`,
    `/app/analytics`, `/app/videos`, `/app/review`, `/healthz`, `/api/overview`,
    `/api/moods`, `/api/learn/state`, `/api/posttime`, `/api/analytics/summary`,
    `/assets/feat`, `/assets/feat/pill.js`; unknown path correctly 404s (fallback works).
    No 404/500 on any real route.
13. **Incidental backend note (not a finding)** — `studio/api_analytics.py:52`
    `` `_TRAFFIC = ("views,estimatedMinutesWatched")` `` — redundant parentheses make it
    a plain string rather than a tuple, but it is passed as a comma-separated metrics
    string to `_ask()` at line 386, so behaviour is correct; style only. Left here so a
    future cleanup does not "fix" it into a tuple and break the metrics string.

## Notes for the fix wave

Nothing to fix. Do not "clean up" the four documented-intentional patterns above
(the en-dash glyph at `web/index.html:2138`, `web/feat/_example.js`, the guarded
`console.warn` catch blocks, and `pcrungo`'s dynamic button) — each is load-bearing
and explained in code.
