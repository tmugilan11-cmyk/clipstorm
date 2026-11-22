# Cross-cutting routes audit — x-routes-live

Auditor: agent-159 (cross-cutting, 40-agent swarm). Server: http://127.0.0.1:8798 (live, real data).
Method: grep + file reads + curl only (no browser; the lead owns visual checks during this audit).
Binding rule set: `docs/qa/CONTRACT.md` (severity ladder, evidence rules, no-browser rule).

## Files owned (cross-cutting — every route referenced by web/feat/*.js)

185 `/api/` references across all 76 files in `web/feat/*.js`. Every referenced route was checked against
`studio/*.py` decorators. No referenced route is missing from the server.

Key consumers and their routes (spot map, file:line):

| Feat file | Routes it calls |
|---|---|
| `web/feat/analytics-*.js` (9 files) | `/api/analytics/{audience,timeseries,summary,videos,retention,traffic}` |
| `web/feat/analytics-trends.js` | GET/POST/DELETE `/api/trends/{searches,videos,saved}` |
| `web/feat/audio-edit.js`, `audio-page.js`, `meme-timeline.js`, `sounds.js` | `/api/jobs/{j}/clips/{c}/sounds*`, `/api/memesounds/*`, `/api/sounds/{kind}/{key}`, `/api/moods*` |
| `web/feat/autopilot.js`, `schedule.js` | `/api/autopilot/{spec,preview,install,remove}`, `/api/schedule/{round,preview}` |
| `web/feat/learn*.js` (6 files) | `/api/learn/{state,run,undo,arms,report,hooks,signals,cost}` |
| `web/feat/pictures.js`, `pictures-dialog.js` | `/api/overlays*`, `.../overlay*`, `.../overlay-template` |
| `web/feat/day.js`, `streamer-mode.js` | `/api/preview?url=`, POST `/api/jobs`, `/api/creators/{cid}/live`, `/api/live/{jid}/*` |
| `web/feat/history.js` | GET + PATCH `.../history` |
| `web/feat/creators.js` | `/api/creators`, `.../avatar`, `/api/overview`, `/api/accounts` |
| `web/feat/brand-ai.js`, `formats.js`, `streamer-mode.js` | POST `/api/brandai/suggest`, GET+PUT `/api/brand` |
| `web/feat/live-heading.js`, `igcaption.js`, `peek.js`, `log.js` | per-clip preview/igcaption/peek/log reads |
| `web/feat/post-time.js`, `clean-forecast.js`, `review-hooks.js`, `stats.js`, `usage.js`, `polish-loading.js`, `grid.js`, `mood.js`, `live.js` | `/api/posttime`, `.../words`, `/api/learn/hooks`, `/api/stats/*`, `/api/usage`, `/api/storage`, `/api/overview`, `/api/moods`, `/api/hunt/*` |

## Checks run

1. **Route map.** Grep of every `/api/` string in `web/feat/*.js`; each matched against `@router`/`@app`
   decorators including `api_route()` registrations (the plain decorator grep misses `api_route()` — both
   false alarms from earlier passes resolved: `/api/memesounds/play/{slug}` at `studio/api_memesound.py:198`,
   `/api/sounds/{kind}/{mood}` at `studio/api_sound.py:121`, both GET/HEAD).
2. **Live GET sweep.** ~40 routes curled with realistic params: `/api/status`, `/api/sync`, `/api/jobs`,
   `/api/overview`, `/api/accounts`, `/api/creators`, `/api/brand`, `/api/brand/themes`, `/api/moods`,
   `/api/usage`, `/api/storage`, `/api/formats`, `/api/captions/styles`, `/api/overlays`,
   `/api/overlays/templates`, `/api/memesounds/{library,trending,for,search}`, `/api/learn/*` (6),
   `/api/analytics/*` (6), `/api/trends/*` (4), `/api/autopilot/{spec,preview}`, `/api/schedule/*` (2),
   `/api/posttime`, `/api/hunt/{watching,live}`, `/api/rules`, `/api/igcaption/looks`,
   `/api/notifications`, `/api/public` — all 200 with well-formed bodies.
3. **Per-clip reads** on the real job `20261122-122201-798840cfbf` / `clip01`: `sounds`, `history`,
   `igcaption`, `words`, `overlay`, `overlay/preview?base=true`, `preview/heading?hook=`, `peek/{cid}`,
   `review` — all 200 (heading preview 126 KB jpeg, overlay preview 106 KB, peek 18 KB).
4. **404 probes** on ten nonexistent ids: `/api/jobs/nonexistent`, `clips/nonexistent/{sounds,igcaption}`,
   `/api/memesounds/play/nonexistent-slug`, `/api/sounds/meme/nonexistent-mood`,
   `/api/overlays/image/nonexistent.png`, `/api/creators/nonexistent/avatar`,
   POST `/api/creators/nonexistent/live`, POST `/api/live/nonexistent/stop`,
   POST `/api/jobs/nonexistent/clips/clip01/sounds/hear`, `/api/sounds/music/fail` (no beds built) —
   every one a clean 404 with a plain-language body ("That job is not here.", "No such creator.",
   "This recording has already ended.", "There is no music bed called fail.").
5. **Validation probes.** `days=0` → 200 (valid), `days=3651` → 422 (limit 3650, matches the comment in
   `web/feat/analytics-table.js:69`); `?style=nonexistent` → 400 listing valid looks; empty/invalid bodies →
   400 with actionable copy ("Send a list of sounds in \"cues\", even when it is empty.",
   "Type a search term first, then save it.", "No such layout.", "Name the search term to remove.").
6. **Mutation probes** (real data protected — validation probes and reversible pairs only):
   - `/api/trends/saved` add `{"term":"qa-audit-probe"}` → 200, DELETE `?term=` → 200 (list back to `[]`).
   - `/api/memesounds/keep` `{"slug":"chicken-on-tree-screaming-53890"}` → 200 (downloaded to shelf),
     DELETE `/api/memesounds/library/{slug}` → 200 (shelf back to the original four).
   - `/api/hunt/watch` `{"platform":"youtube","ident":"@veritasium"}` → 200 (ident normalised to
     `veritasium`), `/api/hunt/unwatch` → 200 `removed:true`.
   - `/api/overlays/templates` create + delete (see findings).
   - Refusal probes: `/api/autopilot/install` and `/remove` with `{"confirm":false}` → both 400
     "Nothing was changed on this machine. Sending \"confirm\": true is w…" (strict-boolean confirm works).
   - `PUT /api/jobs/{J}/overlay-template {"template":"nonexistent"}` → 400 "No such layout."
   - `PATCH .../history` (no body) → 422 (frontend always sends `{keep}`, `web/feat/history.js:230`).
   - `PUT .../sounds {"cues":"bad"}` → 400 with the cues sentence.
   - POST `/api/brandai/suggest {"about":"a chess channel"}` → 200 (one real AI call; the service answered).
   - `/api/moods/prime` — NOT exercised live (heavy local render, throttle 6/300); the control is
     read-verified in `web/feat/sounds.js:307-334` (disabled guard, progress note, error copy).
7. **Frontend reads in depth** (14 files): `pictures.js`, `analytics-trends.js`, `audio-edit.js`, `learn.js`,
   `autopilot.js`, `sounds.js`, `day.js`, `history.js`, `log.js`, `peek.js`, `post-time.js`,
   `analytics-audience.js`, `audio-page.js` (probes + reads), `meme-timeline.js` (probes + reads).
8. **Risk sweep.** 130 `innerHTML =` sites across `web/feat/*.js` — every one builds markup through `esc()`
   (`web/ascii.js:116` escapes `&<>"'`) or the shared `put()` path; zero `eval(`, `document.write`,
   `new Function(`. `web/plugins.js` escapes plug-in names/tips (`plugins.js:94,102`).
9. **Contrast/viewport.** Not re-measured: `web/feat/polish-contrast.js` carries its measured ratios in the
   file header (#A0948C: 7.24 on `--bg`, 6.86 on `--muted`, 5.68 on `--brand-soft`) and
   `docs/TEXT-PASS.md` records the sweep (0 low-contrast, 0 clipped-text nodes). A live re-measure needs the
   browser the lead owns.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | `studio/api_overlay.py:130` | `PUT /api/overlays/templates` answers **500 Internal Server Error** to an empty or malformed JSON body: `body = await request.json()` has no try/except, so the `JSONDecodeError` escapes as an unhandled exception. Every sibling JSON handler catches this exact case: `studio/api_brand.py:58-61` (ValueError → 400 "That brand could not be read."), `studio/api_trends.py:333-337` (empty body → graceful sentence), `studio/api_memesound.py` `_json()` helper (empty body on `/keep` → 400 "Which sound?"). | Live curl, twice: `curl -X PUT -H 'Content-Type: application/json' http://127.0.0.1:8798/api/overlays/templates` → `500 Internal Server Error` (m00128 probe + root-cause check). With a valid body the same route returns 200. | Wrap line 130 in `try/except ValueError` and raise `HTTPException(400, "Send the layout as an object.")`, reusing the copy already at line 132. |
| minor | `studio/api_overlay.py:133-137` | The same route accepts an **empty `items` list** and stores a layout that draws nothing: it refuses non-empty-but-invalid lists ("None of those pictures are on the shelf…") but `{"items":[]}` passes through and returns 200 with `{"template":{"items":[]}}`. Not reachable from the UI — `web/feat/pictures.js:589` guards ("There is nothing to save yet. Add a picture first."). | Live curl: `PUT /api/overlays/templates {"id":"","name":"qa-audit-probe","items":[]}` → `200 {"ok":true,"template":{"id":"tdb58d0","items":[]}}`; probe template deleted immediately after. | Treat a missing/empty `items` the same as the existing refusal, or document the empty layout as an intentional no-op. |

No other bug found. No 404 among referenced routes; no dead handler found in the files read in depth; no
console-risky markup; every read file carries loading, empty and error states.

## Usability findings

None. Checked against the contract's usability bar across every file read in depth:

- **Copy** is plain language throughout, errors included: "Type a search term first, then save it."
  (`studio/api_trends.py:342`), "Give the layout a name first." (`web/feat/pictures.js:588`),
  "That is what it would change. Nothing was changed." (`web/feat/learn.js:326`),
  "That link is live right now. Add the creator and press Start recording to clip a stream."
  (`web/feat/day.js:154`).
- **States**: loading ("Reading the posting record…" `post-time.js:33`), empty ("This video has no log
  written for it." `log.js:36`), error with a recovery hint (`sounds.js:290-291`) all present.
- **Destructive controls** confirm before acting: autopilot's two-step arm with an 8-second timeout and a
  dialog-helper fallback (`web/feat/autopilot.js:176-207`), day.js's `confirm2` before a ten-clip job
  (`day.js:159`).
- **Buttons** have disabled guards and re-enable on failure (`analytics-trends.js:344,353`,
  `history.js:225-227`, `learn.js:311`).

## Audit-harness note (lesson, not a product bug)

The first mutation batch was run through a bash helper whose unquoted `${3:+-d "$3"}` expansion word-split
the curl arguments, so curl treated the JSON body as a URL and the requests went out **bodyless**. That
produced three false 400s (`/api/trends/saved`, `/api/memesounds/keep`, `PUT /api/brand`) — each retested
with a properly quoted curl and works (`200`). It also made the `/api/learn/run` probe arrive bodyless, so
it ran one real 28-day round: `GET /api/learn/state` confirms it changed nothing
(`"applied":[],"changes":[],"effect":"Nothing was changed…"`), and the follow-up `undo` restored the same
settings. No lasting side effect: templates 0, saved terms `[]`, style `beast`, the brand document exactly
its 28 schema keys (the legacy `captions_always` key that vanished is read by zero code and `studio/brand.py:22-23`
drops unknown keys on save by design). Lesson: quote every curl `-d` expansion; a 400 on a
hand-built body is a harness bug until the handler proves otherwise.

## Verdict

The live API surface is in good shape: every route the front end references exists, 404s and validation
errors speak plain language, refusals are strict where it matters (autopilot confirm), and the one real
defect is a missing `try/except` on one JSON read — a one-line fix.
