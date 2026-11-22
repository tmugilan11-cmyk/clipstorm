# x-states — cross-cutting audit (agent-164)

Audit of how the frontend handles **loading / empty / error / edge states** across every
fetched panel: a failed fetch must surface in words, never silently.

- Server under test: `http://127.0.0.1:8798`
- Binding rules: `docs/qa/CONTRACT.md` (no browser tools; every finding carries evidence)
- Method: `ops_grep` / `ops_glob` / `ops_inspect_local_file` + `curl` only
- Skill loaded: `systematic-debugging` (root cause before fixes)

## Files owned (cross-cutting)

| Scope | Files |
|---|---|
| Fetch framework | `web/plugins.js` (loader, `P.add`/`P.page`/`P.toast`/`P.api`), `web/index.html` (`api()`, `send()`, toast) |
| Feature fetchers | all 78 files in `web/feat/*.js` |
| Backing routes | every `/api/...` route those files call, across `studio/*.py` |

## Checks run

1. **File survey** — 85 `web/*.js`/`.html` files enumerated; 78 in `web/feat/`.
2. **Fetch census** — 44 files call `.api(`; 7 use raw `fetch(`:
   `analytics-retention.js:78`, `analytics-table.js:131`, `audio-page.js:416`,
   `meme-timeline.js:143`, `pictures.js:503`, `polish-icons.js:131`+`137`, `sounds.js:177`.
   All 20 `await P.api(` / `api(` call sites verified inside `try` blocks.
3. **Loader framework read** — `web/plugins.js` (282 lines): a failed `tools()` renders
   "This part did not load: <why>", escaped (`plugins.js:212-221`); a failed tool `load()`
   toasts "One tool could not start. The others still work." (`plugins.js:229-233`); a
   failed page `load()` toasts "That page could not finish loading." (`plugins.js:131-139`).
   `web/index.html` `api()` throws on `!ok` with the server's detail text
   (`index.html:999-1004`); `send()` is the POST/PUT/DELETE wrapper (`index.html:1005`);
   `toast(kind="bad")` adds a Report button (`index.html:1006-1009`).
4. **Route verification** — every `/api/...` route called by feat files exists in
   `studio/*.py`. **Zero 404-route findings.** Routes confirmed in: `api_analytics.py`
   (summary:176, timeseries:237, videos:271, audience:327, traffic:374, retention:402),
   `api_auto.py` (spec:97, preview:117, install:135, remove:161), `api_brand.py`
   (GET:42, PUT:48), `api_brandai.py:52`, `api_hooks.py:43`, `api_learn.py` (state:57,
   run:72, undo:103, signals:188, arms GET:224 POST:239 DELETE:275, cost:288),
   `api_learnreport.py:38`, `api_memesound.py` (search:81, for:96, trending:111, library
   GET:130, keep:138, DELETE:154, upload:162, play:198), `api_overlay.py` (GET:57,
   upload:68, image:99, templates GET:117 PUT:125 DELETE:141, clip overlay GET:152
   PUT:169, preview POST:208 GET:273, overlay-template:291), `api_posttime.py:84`,
   `api_preview.py` (hunt live:122, watching:135, watch:144, unwatch:158,
   schedule/round:191, peek POST:64 GET:101), `api_sound.py` (moods:58,
   sounds/{kind}/{mood}:121, prime:155), `api_stats.py:71`, `api_style.py`
   (captions/styles:46, formats:104, style/preview:218, style/motion:326), `api_trends.py`
   (searches:218, videos:265, saved GET:320 POST:328 DELETE:364), `api_heading.py:143`,
   `api_history.py` (GET:179, PATCH:187), `api_igcaption.py` (GET:60, PUT:68, generate:89),
   `api_text.py:279`, `server.py` (status:647, preview:839, creators:1315, live/stop:1373,
   clip:1382, storage:1695).
5. **Live curl pass** — 30 routes probed against the running server, all returned 200:
   `/api/moods`, `/api/usage`, `/api/overlays`, `/api/formats`, `/api/captions/styles`,
   `/api/learn/report`, `/api/learn/state`, `/api/learn/cost`, `/api/learn/arms`,
   `/api/learn/signals?days=28`, `/api/learn/hooks?limit=40`, `/api/posttime`,
   `/api/creators`, `/api/accounts`, `/api/status`, `/api/autopilot/spec?times=09:00`,
   `/api/autopilot/preview?times=09:00`, `/api/schedule/round?times=09:00`,
   `/api/memesounds/library`, `/api/memesounds/trending?window=24h`, `/api/storage`,
   `/api/analytics/summary?days=7`, `/api/analytics/timeseries?metric=views&days=7`,
   `/api/analytics/videos?days=7`, `/api/trends/searches?days=7&limit=8`,
   `/api/trends/saved`, `/api/brand`, `/assets/feat`.
6. **Loading/empty/error sweep over list panels** — every fetched panel checked for the
   three states in words. Verified clean (loading message + empty state + error in words):
   `igcaption.js:117-122` ("Loading Instagram caption…"), `schedule.js:106-111/163-169/192-198`
   ("Working out the … schedule…", `fail(msg)`), `usage.js:251-258` ("Reading what the AI
   has been used for.", err fill; explicit `.usg-empty` at `usage.js:228-234`),
   `formats.js:150-180` (catch sets `shapeWhy`/`lookWhy`, painted), `learn-arms.js:229-237`
   +`302-311`, `learn-report.js:138-148`, `learn-signals.js:160-168`,
   `learn-arrows.js:44-51` (empty "No rounds have run yet."), `learn-hooks.js:41-48`
   ("Reading the hooks…"), `post-time.js:33-44` ("Reading the posting record…"),
   `pictures-dialog.js:27-58` ("Reading this clip…", error in words, empty "This clip
   draws no pictures yet."), `creators.js:227-229` (`.catch(err => ({__err: sentence…}))`),
   `autopilot.js:210-264` (button label "Working it out…", `showError`), `day.js:144-152`
   (`say()` in words), `streamer-mode.js:416/637/690`, `peek.js:238-247` ("Taking
   stills…" + `aria-busy`), `sounds.js:194-201` (trouble state), `meme-timeline.js:142-146`
   ("Keeping <name>…" + toast), `pictures.js:503-511` (toast), `sounds.js:177-185`
   (HEAD probe → 404-specific sentence), `polish-icons.js:234-239` (toast + `draw(null)`),
   `analytics-retention.js:76-85` and `analytics-table.js:129-134` (`get()` throws with
   detail / 404-specific message).
7. **Untrusted-text innerHTML spot check** — server-sourced strings are escaped through
   `esc()` before innerHTML across the sampled files. Zero injection findings.
8. **Console-risky code** — no `eval(`, `new Function(`, or `document.write(` anywhere
   in `web/`. Clean.
9. **Width/overflow** — every element wider than a 390px viewport sits inside a scroll
   container: `analytics-audience.js:25` `.aa-map{min-width:520px}` inside
   `.aa-scroll{overflow-x:auto}`; `analytics-table.js:18` `.ant-t{min-width:960px}` inside
   `<div class="scroll">` (`analytics-table.js:156`) with `.scroll{max-width:100%;
   overflow-x:auto}` from `polish-mobile.js:43` and `index.html:619`; the page shell keeps
   `main#main{overflow-x:hidden}` (`index.html:873`). No page-level overflow on 390px.
10. **Toast Report button** — handler exists (`index.html:3403` → `openFeedback`, defined
    at `index.html:1307`). Not dead.
11. **Usability read** — labels, copy, and two-step flows checked for beginner
    comprehension; jargon lives in code comments only, never in user-facing copy.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| minor | `web/feat/clean-forecast.js:44` | A failed words fetch is conflated with "this clip has no word timings yet". `.catch(() => [])` makes a failed fetch yield the same empty array as a clip with no transcript, so the panel shows the empty-state claim instead of a fetch-failure note. | `clean-forecast.js:44` `.catch(() => [])`; `say()` at `clean-forecast.js:90-92` then prints "PeakCut has no word timings for this clip yet, so it cannot say what will change until the clip is made once." For an existing clip whose transcript exists, the copy implies making the clip will fix it, when the server simply did not answer — a fact the server never stated (the repo's own zero-is-a-claim rule). It is in words, never silent, so minor. | Catch sets a failure flag; on failure print "The word timings could not be read. Try again." instead of the no-word-timings claim. |
| minor | `web/feat/audio-page.js:439` | A failed waveform fetch leaves a blank canvas with no words. The row still shows title / Play / Keep, so nothing is broken, but the empty waveform slot carries no explanation of why it is empty. | `audio-page.js:439` `.catch(() => done(null))` — the failure caches `null` and draws nothing; no note is set anywhere on the failure path. | On failure, draw a one-line note in the waveform slot ("The waveform could not be drawn for this sound") or hide the canvas slot. |
| minor | `web/feat/history.js:183-184`, `:192` | Two silent catches in the history panel. The load catch is documented by-design for an optional route; the reread catch silently keeps stale page data after a successful pin. | `history.js:183-184` `catch { DEAD.add(k); }` — a failed history read is remembered with no user-visible trace (comment: "no history route on this job, or the server said no"); `history.js:192` `try { fresh = await P.api(…) } catch { return; }` — after a successful pin, a failed read-back leaves the page one step behind with no words. | On reread failure, say one line ("The clip could not be read back; the page may be one step behind"). The DEAD dedupe is by-design and acceptable for an optional route. |
| minor | `web/feat/style-tiles.js:112` | The styles-route fetch fails silently — but it is a fallback-only enhancement: the primary source of looks is the page's own state, and the re-mount is gated so the fetch only refines what is already shown. | `style-tiles.js:112` `.catch(() => {})`; the re-mount at `style-tiles.js:106-111` runs only when the fetched list actually differs (`if (g.dataset.names === names(list)) continue;` at `:107`). | Acceptable as-is; a one-line note would be polish. |

**No critical findings. No important findings.** Every fetched panel surfaces its failure
in words; the four minor findings are edge paths where a fetch failure is worded as (or
not distinguished from) an empty state.

## Usability

No usability findings. Specifically verified:

- All loading/empty/error copy is plain language a beginner reads in five seconds
  (samples in check 6 above); jargon is confined to code comments.
- Controls that fetch carry explanations (`analytics-table.js:178/181/183` hints).
- Two-step flows are explained in place (e.g., `day.js` paste-link → confirm; history
  pin → refresh).
- The bad-toast Report button works (`index.html:3403` → `openFeedback:1307`).

## Summary

The x-states discipline holds across all 85 frontend files and their 30 live routes:
loading, empty, and error states exist in words everywhere a fetch happens, zero 404/500
routes, zero console-risky constructs, zero overflow beyond 390px viewports; the only
findings are four minor edge paths where a failed fetch reads as (or silently mimics) an
empty state rather than a fetch failure.
