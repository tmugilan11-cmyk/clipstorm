# docs-menu-pages

Skill loaded before any other tool call: `writing-for-agents`.

## What I built

`peakcut/docs/MENU.md` - the per-row menu reference. 363 lines, 21113 bytes, 23 sections, 19 of them
one per rail row.

One thing to know first: this filesystem is case-insensitive, so `docs/MENU.md` and the old
`docs/menu.md` are the same file. Writing the deliverable replaced the older, partly stale menu doc
instead of sitting next to it. I carried over what was still true (how a row is ordered, where the
moved settings went, what stays in Settings, the browser-console check) and corrected what had gone
stale: the old file warned that Analytics and Transcription both claimed order 20, and Transcription
is now 25.

The file is organised as:

- `How a row gets its place` - `drawShell()` at `web/index.html:1293`, `PeakCut.page`, the heading
  ranks in `web/feat/menu.js:16`, the tie-break to load order, and the one-line console check
  `PeakCut.pageRows().map(r => [r.group, r.nav, "/app/" + r.path])`.
- `The rows at a glance` - one table, all 19 rows, with heading, address, order, the wave that added
  the row, and the file that draws it.
- One section per row, in rail order: Home, All videos, Review, Brand, Creators, Improve, Clip
  formats, Sounds, Live, Insights, Transcription, Tools, Connected apps, Schedule, AI, Usage,
  Storage, Account, Help. Each has two plain sentences saying what the page is for, then `Drawn by`,
  `Reads` (the exact routes) and `Not yet`.
- `Where the moved settings went` - the four former Settings tabs and their new addresses.
- `What is still missing` - the five gaps found while writing, listed once.

The seven rows this wave added are all documented: Creators, Live, Schedule, Help, Usage, Clip
formats and Sounds.

## Routes it reads

The document names routes; it does not call them. Every route written into it exists. I checked
them with a script rather than by eye:

```python
# collect every /api/... /oauth/... /media/... string in docs/menu.md, normalise {x} and <x> to {},
# then look each one up in the decorators of studio/*.py, keeping the HTTP method
MISSING: []
97 method-tagged routes checked
```

The first, path-only pass reported one miss, `/media/bed_`. That was not a route claim: it is the
`<audio>` address `web/feat/sounds.js:131` builds by string concatenation, and the parser cut it at
the underscore. The document says plainly that this address has no route behind it today, which is
the point of that paragraph. The second pass matches method and path together, which is what caught
`DELETE /api/trends/saved?term=` being written as a path id on my first draft.

Families covered, and where each was confirmed:

- Home: `/api/overview`, `/api/jobs`, `/api/status`, `/api/preview`, `/api/upload`,
  `/api/upload/start`, `PUT /api/upload/{id}/{n}`, `POST /api/upload/{id}/finish`
  (`studio/server.py:1582, 802, 623, 815, 866, 945, 989, 1013`).
- All videos: `/api/sync` (`studio/server.py:790`), `/api/overview`, `/api/jobs` as the fallback,
  plus the row actions `PATCH /api/jobs/{jid}/clips/{cid}`, `POST /api/bulk/delete`,
  `GET /api/clips.zip?ids=`, `POST /api/jobs/{jid}/peek`.
- Review: `/api/jobs`, `/api/jobs/{jid}/review` (`studio/api_review.py:89`), and the decision
  `PATCH /api/jobs/{jid}/clips/{cid}` (`studio/api_review.py:98`).
- Brand: `GET`/`PUT /api/brand` (`studio/api_brand.py:42`), `/api/captions/styles`
  (`studio/api_style.py:44`), `/api/style/preview` (`studio/api_style.py:182`). `POST
  /api/brand/reset` (`76`) and `GET /api/brand/themes` (`83`) exist and nothing in `web/` calls
  them; the document says so instead of implying they are wired.
- Creators: `/api/creators`, `/api/overview`, `/api/accounts` in one `Promise.all`
  (creators.js:227-229) and the avatar at `/api/creators/{cid}/avatar` (creators.js:100), all
  served by `studio/server.py:1291,1582,1601,1278`.
- Improve: `/api/learn/{state,run,undo,cost,signals,arms}`
  (`studio/api_learn.py:57,72,103,188,224,239`).
- Clip formats: `/api/formats`, `/api/captions/styles`, `/api/style/preview`
  (`studio/api_style.py:73,44,182`).
- Sounds: `/api/moods`, `POST /api/moods/prime` (`studio/api_sound.py:55,96`).
- Live: `/api/hunt/live`, `/api/hunt/watching`, `POST /api/hunt/watch`,
  `POST /api/hunt/unwatch` (`studio/api_preview.py:121,134,143,157`).
- Insights: `/api/analytics/{status,summary,timeseries,videos,audience,traffic,retention}`
  (`studio/api_analytics.py:149,176,237,271,327,374,402`) and
  `/api/trends/{status,searches,videos,saved}` (`studio/api_trends.py:189,218,265,320,328,364`).
  `DELETE /api/trends/saved` takes the term in the query string, not a path id - I had that wrong on
  the first pass and the route check caught it.
- Schedule: `/api/autopilot/{spec,preview,install,remove}` (`studio/api_auto.py:97,117,135,161`)
  and `/api/schedule/preview` (`studio/api_preview.py:173`).
- Usage: `/api/usage` (`studio/server.py:1374`).
- Transcription, Tools, Connected apps, AI, Storage, Account: the Settings forms the pages reuse -
  `/api/transcribe` plus `/models` and `/test` (`studio/server.py:1472,1528,1547`), `/api/rules`
  (`studio/api_preview.py:46`), `/api/stats/video`
  (`studio/api_stats.py:71`), `/api/stats/channel` (`87`, no caller in `web/`), `/api/apps` and `/api/accounts`
  (`studio/server.py:1714,1601,1606`), `/api/zernio` (`1730`), `/oauth/{platform}/start` and
  `/callback` (`1620,1630`), `/api/ai` (`1385`), `/api/storage` (`1671`) with `/open`, `/pick` and
  `PUT` (`1678,1691,1700`), `/api/status`, `/api/auth/password`, `/api/auth/logout`,
  `/api/account/delete` (`623, 586, 573, 1136`).

## What it cannot do yet

- **It cannot settle the Brand/Creators tie.** Both register group `Make` at order 10
  (`web/feat/menu-pages.js:130` and `web/feat/creators.js:256`), so `menu.js` falls through to load
  order and the two rows can swap between reloads. The fix is one digit in a file I do not own, so
  the document names the wobble rather than describing an order that is not stable.
- **It cannot document a form that only lives in `web/index.html`.** The moved pages draw
  `drawSettingTab(tab, box)`; the document points at that function by line instead of copying the
  fields, because a copy goes stale the first time the form changes.
- **The Sounds gap is a server change, not a doc change.** `web/feat/sounds.js:131` plays
  `/media/<mood>.wav`, and `studio/server.py:1152` only serves `[\w\-]+\.(mp4|jpg)` out of one job's
  folder, so the preview address has no route behind it. Recorded on the Sounds row.
- **The Live gap is a missing caller.** `POST /api/live/{jid}/clip` and `/stop` exist in `studio/`,
  and nothing in `web/feat/live.js` calls them, so a watched channel can be listed and opened but not
  cut. Recorded under Live `Not yet`.
- **Two headings print nothing.** `Connect` (40) and `Account` (60) are declared in
  `web/feat/menu.js:16` and no page uses either today. `Look and sound` (30) is in the same
  position; the document explains the numbering so the empty heading is not a surprise.
- **The doc can drift from the rail.** It says so in its own words and points at the console line,
  because the running page is the truth and the file is a snapshot.

## Two things found in files I do not own

While checking where each row's text comes from I read `web/feat/creators.js` and
`web/feat/style-tiles.js`. Both contain an em dash, which the contract for this wave forbids
(grep for the em dash character, U+2014, under `web/feat/`):

- `web/feat/creators.js:267-268` and `web/feat/creators.js:275` - visible page copy on the Creators
  page, so this one reaches a person.
- `web/feat/creators.js:5` and `web/feat/style-tiles.js:161` - comments only.

I have not touched either file. Whoever owns Creators should replace the three visible ones with a
colon or a pair of commas; the two in comments are harmless but should go for consistency.

## Commands I ran

```
cd peakcut

python tests/test_feat_files.py
  -> {"files": 47, "checks": 382}
     All checks passed.
     exit code 0

grep -c <em dash U+2014> docs/menu.md
  -> 0                 (no em dash anywhere; ASCII hyphen only)

wc -l -c docs/menu.md
  -> 363 21113

grep -c '^## ' docs/menu.md
  -> 23                (19 row sections plus 4 framing sections)

python - <<'PY' ... route check over studio/ ...   (method-aware pass)
  -> MISSING: []
     97 method-tagged routes checked, each against
     @(app|router|bp).(get|post|put|delete|patch) in studio/*.py
```

`node --check` does not apply: the deliverable is Markdown, not a feature file, so there is no
JavaScript to parse. `python tests/test_feat_files.py` still passes because nothing under
`web/feat/` was touched.

## Files I touched

- `peakcut/docs/MENU.md` (rewrote `peakcut/docs/menu.md` in place; same file on this
  case-insensitive filesystem).
- `peakcut/docs/swarm4/wave4/docs-menu-pages.md` (this report).

Nothing under `web/`, `studio/` or another agent's report was edited.
