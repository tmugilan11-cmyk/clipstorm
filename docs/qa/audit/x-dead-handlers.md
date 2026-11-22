# Audit: x-dead-handlers (cross-cutting: handlers, buttons, plugin slugs)

Auditor: agent-163 (subagent of lead), 40-agent QA swarm.
Scope: every `data-act=` emitted anywhere in the app has a handler; every button does
something; every `PeakCut.add` slug matches its file name. Plus broken controls,
console-risky code, missing states, and usability where the cross-cutting sweep saw them.

## Files owned (swept, not owned singly)

- `web/plugins.js` (the dispatcher: `P.add`, `P.page`, `wireActs`, `P.loadFiles`)
- all 76 files under `web/feat/*.js`
- `web/index.html` (the big `data-act` listener and all static markup)
- route existence for every `/app` page and `/api` call the feat files make

## How dispatch works (read first)

- `web/plugins.js:25` `P.add(name, def)` registers a feature; merging keeps late
  registrations working.
- `web/plugins.js:150-169` `wireActs()`: one document-level click listener finds the
  closest `[data-act]`, skips clicks already handled by `index.html`
  (`b.dataset.pcDone === "1"`), treats `pcpage` specially (`P.openPage(d.v)`), then
  loops the registration order for the first plugin whose `act[act]` exists.
- `web/index.html:3108-3463` is the built-in listener for every `data-act` that
  `index.html` itself emits (82 distinct acts, all listed in the check below).
- Plugin act keys use distinct prefixes (`aed-`, `alb-`, `str-`, `pc*`, `la*`, ...),
  so no emitted act matches two handlers and no double-fire was found.

## Every check run

1. **Slug vs file name.** Grepped every `PeakCut.add(` (and the `PC.add` alias) in
   `web/feat/*.js`: all 76 served files register exactly one plugin whose slug equals
   the file stem. `web/feat/day.js:174` registers via `PC.add("day", ...)` where
   `const PC = window.PeakCut` - it counts. `web/feat/_example.js` is not listed in
   `/assets/feat` (unserved by design, not a finding). Page files registered:
   `menu-pages.js` (brand, transcribe, tools, apps, ai, storage, account),
   `streamer-mode.js` ("streamer"), `audio-page.js` ("audio"), `analytics.js`,
   `audio-edit.js` (hidden page), `creators.js`, `formats.js`, `help.js`,
   `learn.js` ("improve"), `pictures.js`, `schedule.js`, `usage.js` ("ai-usage").
2. **Emitted act union.** Swept `data-act=` across `web/feat/*.js` and
   `web/index.html`. 103 static emissions in `index.html` (plus `openpics` at
   `web/index.html:2779`, `histkeep` at `:2951`) and 99 in feat files. One earlier
   feat-wide grep silently under-reported (74 hits, missing `live.js` and
   `autopilot.js`); a fresh sweep with a plain `data-act=` pattern gave the full 99
   and the union below was cross-checked per file. `pill.js:128` sets
   `el.dataset.act = "pcrungo"` directly - the only dataset-based emission.
3. **Handler coverage.** Every emitted act has a handler:
   - `index.html` acts: all covered by the big listener at `:3108-3463`
     (go, aimodels, aisave, aitest, trmodels, tlschedule, trsave, trtest, brandsave,
     menu, collapse, toggleopts, focusurl, step, tab, pickfile, addmore, closedlg,
     openaudio, openclip, newcreator, copy, copyall, histkeep, logout, pwsave,
     delclip, dlall, seldl, selclear, selall, seldel, delcreator, delaccount, deljob,
     chadd, chdel, spick, chmain, golive, stoplive, clipnow, resendverify, tour,
     settab, updhow, updlater, storopen, storchange, storpick, storsave, storcancel,
     appsetup, copytext, appsave, zsetup, zsave, zforget, zrefresh, bell, feedback,
     report, acctmenu, bellread, ntgo, csave, cdiscard, pause, pcancel, pretry, ssave,
     plansave, testalert, accremove, remake, noteclip, transclip, rvapprove, rvreject,
     rvskip, peekclip, postnow, postqueue, openpics).
   - `audio-edit.js` emissions (224 aed-ask, 225 aed-save, 226 aed-mix, 228
     aed-preview, 242 aed-find, 421 aed-hear, 422 aed-take, 444 aed-add) all in the
     map at `:752-775`.
   - `audio-page.js` (176 alb-cat, 192/193 alb-view, 216 alb-search, 318/367/395
     alb-play, 320/368 alb-like, 322/370 alb-mark, 327 alb-forget, 328/396 alb-keep)
     all in the map at `:551-579`.
   - `autopilot.js` (62/67/68 pcauto_*) map `:383-386`. `creators.js` (210/272
     creators_reload) map `:293`; `newcreator` and `go` are built-ins.
   - `formats.js` (306 fmtplay, 307 fmtuse, 481 fmtreload; 480 `pcpage` brand is a
     built-in) map `:426-460`. `grid.js` (175 pcgridrefresh) map `:182-190`, disables
     while running. `history.js` (127 pchistkeep) map `:243`. `icons-extra.js` (157
     iconsx-run) map `:163-174`.
   - `learn-arms.js` (147 lastart, 148 lacancel, 182 lastop, 196 laopen, 197
     lareload) map `:346-352`. `learn-report.js` (117 lrepopen) map `:179-185`.
     `learn.js` (238 lrnundone, 258 lrnrun, 259 lrndry) map `:366-369`.
   - `live.js` (146 pclive_check, 147 pclive_remove, 328 pclive_look, 340 pclive_add)
     map `:367-380`. `log.js` (87 joblog) map `:102-113`. `peek.js` (82 peektake)
     map `:226`. `pictures.js` (121 pics_back, 139 pics_center, 140 pics_reset, 156
     pics_nudgedown, 157 pics_drop, 160 pics_retry, 176 pics_save) map `:571-586`.
   - `polish-empty.js` dynamic `data-act="${act}"` at `:43` is sanitized (only
     `[A-Za-z0-9_-]` kept, `:41`); `:80 peemptyfocus` has handler `:86`.
     `polish-errors.js` (154 pcretry) map ~`:300-322`, disables while awaiting and
     removes the line on success. `polish-icons.js` (218 piconsscan) map `:223-241`.
     `polish-keyboard.js` (316 pckbopen) map `:318-319` plus its own click listener on
     `[data-pckb]` at `:301-306`. `polish-loading.js` (91 pclstor) map `:94-112`.
   - `schedule.js` (150/152 scharm, 184/213 schcopy, 312 schredraw) map `:266-280`;
     `schcopy` guards empty text and clipboard refusal. `stats.js` (164 pcstatsread)
     map `:276` with loading dedupe `:284`. `streamer-mode.js` (289 str_savehooks, 318
     str_make, 339/585 str_mode, 462 str_clip, 463 str_stop, 623 str_rec) map
     `:674-707`. `style-tiles.js` (186 pickstyle) map `:236-253`. `usage.js` (288
     usgload) map `:271`. `pill.js` `pcrungo` map `:153-167` with a `/app/videos`
     fallback.
   - `day.js` has no act map; it wires `.day-go` click, `.day-who` change and Enter
     directly (`:102-106`). Covered.
4. **Buttons that do nothing.** Swept all `<button` in `index.html` (119) and every
   feat-emitted button: each carries `data-act`, `type="submit"` in a form, or a
   direct listener (`.pick-opt` and `.pick-new` at `web/index.html:1589` are covered
   by the picker's own listener; `day.js` rows as above). No dead button found.
5. **Routes.** curl against http://127.0.0.1:8798 (all exit 0): `/` (303),
   `/app`, `/app/videos`, `/app/audio`, `/app/improve`, `/app/schedule`,
   `/app/pictures`, `/app/formats`, `/app/creators`, `/app/analytics`,
   `/app/ai-usage`, `/app/help`, `/app/settings`, `/app/settings/apps`,
   `/app/nosuchpage` (the catch-all `@app.get("/app/{rest:path}")` at
   `studio/server.py:438` serves the shell by design, so no 404), `/assets/feat`,
   `/api/sync`, `/api/memesounds/trending`. No 404 and no 500 anywhere.
6. **API routes exist.** Cross-checked all 185 `/api` references in feat files
   against 103 `@app.*` routes in `studio/server.py` and 90 `@router.*` routes in
   `studio/api_*.py`: every one resolves
   (analytics, trends, memesounds, jobs/clips sounds+words+history+igcaption+overlay+
   peek+preview/heading, autopilot, brand, brandai, preview, jobs, formats,
   captions/styles, style, overview, accounts, creators, igcaption/looks, learn,
   hunt, moods, storage, posttime, usage, stats/video, status, live, overlay-template).
7. **Contrast (measured, not looked at).** Palette in `web/index.html:19-21`
   (`--bg:#0A0A0A`, `--card:#111111`, `--text:#F5F5F5`, `--dim:#A3A3A3`,
   `--faint:#7C7C7C`, `--brand:#FF8B33`, `--brand-ink:#160D05`,
   `--brand-soft:#2A1B10`, `--brand-deep:#FFB27A`). `web/feat/polish-contrast.js:29`
   lifts `--faint` to `#A0948C` inside `#main, dialog` (7.24:1 per its header).
   Measured pairs on the live page: `.btn.primary` ink on `--brand` about 8.2:1;
   `--brand-deep` on `--card` about 10.7:1; `--dim` on `--card` about 7.5:1;
   `--faint` outside dialogs 4.74:1 on `--bg` and 4.53:1 on `--card`. No pair below
   3:1.
8. **Overflow / width.** `analytics-table.js:18` sets `.ant-t{min-width:960px}` - the
   table is wrapped in `<div class="scroll">` (`analytics-table.js:156`) and
   `.scroll{overflow-x:auto}` is defined at `web/index.html:619`, so no horizontal
   overflow; the suspicion was checked and disproven. `.aa-map` (min-width:520px)
   sits inside `.aa-scroll{overflow-x:auto}`. `.pics-canvas` is `width:405px` with
   `max-width:100%` (`pictures.js:48`).
9. **Console risk.** `audio-page.js:407-439` `bars()` guards every `.catch` chain and
   try/catch. `pill.js:172` `setInterval(1200)` paint is try/catch at both levels.
   `learn-arms.js:355` `setInterval(tick, 700)` is wrapped in try/catch and `tick()`
   (`:327-333`) early-returns on every missing node. `schedule.js` clipboard calls
   are guarded. Nothing risky found.
10. **Labels a beginner reads.** Read stats.js, polish-keyboard.js, schedule.js,
    learn.js, audio-page.js labels: key fields carry "Kept in this tab only. Never
    saved."; the keyboard card explains "Press ? anywhere"; "Read the numbers" has a
    hint sibling. Two small copy issues below.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| minor | web/feat/audio-edit.js:769 | Dead handler registration: act map key `"aed-keep"` exists but no `data-act="aed-keep"` is emitted anywhere in `web/` (76 feat files + index.html). The editor's remove button is `aed-take` (`:422`); `keep` is the audio-page naming (`alb-keep`, audio-page.js:328). | Map key `"aed-keep"(btn){` at audio-edit.js:769; grep `data-act="aed-keep"` across `web/**/*.js` and `web/index.html` returns 0 emissions. | Delete the `"aed-keep"` key from the act map, or rename it to match an intended button if one was planned. |
| minor | web/feat/polish-empty.js:39-47 | Dead helper: `P.empty({act, ...})` builds markup with a dynamic `data-act="${act}"` (`:43`), but no feature ever calls `P.empty`, so the helper, its `act` parameter and the `:86` handler branch never run. | grep `P.empty` across `web/feat/*.js` finds only the definition at polish-empty.js:39; no caller passes `{act:...}`. | Remove the helper, or wire it into a real empty state so the act it accepts is reachable. |
| minor (usability) | web/feat/analytics-audience.js:26, web/feat/audio-page.js:44 and :82, web/feat/history.js:34, web/feat/keys.js:18, web/feat/pictures.js:89 | Six quiet labels are set at 10px, below a comfortable reading size for a beginner (contrast itself passes: they use `--faint`, 7.24:1 inside `#main`). | `.aa-h` (analytics-audience.js:26), `.alb-cat b` (audio-page.js:44), `.alb-wave.empty` (audio-page.js:82), `.pchist .pk` (history.js:34), `.pckeys .lead` (keys.js:18), `.pics-thumb b` (pictures.js:89) all declare `font-size:10px`; 40 declarations in the 10-11px range across `web/feat`. | Raise the smallest quiet labels to 11-12px. |
| minor (usability) | web/feat/schedule.js:213 | Button copy "Copy the tick command" is jargon: a beginner must decode what "tick" means before the button makes sense. The card's note above (`:207-210`) explains the card, not the button. | `<button class="btn sm" type="button" data-act="schcopy" data-t="due">Copy the tick command</button>` at schedule.js:213. | Rename to "Copy the schedule command" (or "Copy the command the schedule runs"). |

Not findings (checked and disproven): `analytics-table.js:18` 960px min-width without a
wrapper (wrapped by `div.scroll`, index.html:619); the `/app/nosuchpage` route
(catch-all serves the shell on purpose, studio/server.py:438); `_example.js` slug
(unserved, not reachable).

## Verdict

The wiring is sound: all 76 feat plugins register one slug matching their file, every
emitted `data-act` resolves to exactly one handler, every button does something, and
no `/app` or `/api` route 404s or 500s. The only defects found are two never-called
handler/helper registrations (dead code, not broken behaviour) and two small copy
polish items.
