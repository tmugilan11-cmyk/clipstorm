# Audit — API area: Analytics + Trends routes

Auditor: agent-155 (40-agent QA swarm, audit wave). Date: 2026-11-22.
Binding rules: docs/qa/CONTRACT.md. No browser was used; all probes are curl against
http://127.0.0.1:8798 plus file reads. No dsh_browser_* call was made.

## Files owned

- studio/api_analytics.py (424 lines) — GET /api/analytics/status, /summary, /timeseries,
  /videos, /audience, /traffic, /retention
- studio/api_trends.py (381 lines) — GET /api/trends/status, /searches, /videos, /saved,
  POST /api/trends/saved, DELETE /api/trends/saved

Read-only support reads: studio/ytstats.py (signatures: analytics, videos, _videos, vid_id,
explain at studio/ytstats.py:122-138), studio/posting.py:253-312 (overview shape),
studio/auth.py:57-69 (throttle), studio/config.py:146 (user_dir), studio/server.py router
mounts, web/feat/analytics-retention.js (446 lines), web/feat/analytics-trends.js (393
lines), web/feat/analytics-charts.js (metric usage), tests/test_analytics_api.py,
tests/test_trends_api.py.

## Every check run (live, curl against 127.0.0.1:8798)

Analytics reads (all 200 unless noted):

- GET /api/analytics/status → 200; connected=false, source="peakcut", note names the
  missing connection and where to connect (Connected apps). Shape matches the page.
- GET /api/analytics/summary?days=28&compare=1 → 200; 6 cards, compare=null in local mode.
- GET /api/analytics/summary?days=7&compare=0 and ?days=90&compare=0 → 200; clips=5 in both
  (all clips on this install are younger than 7 days, so not distinguishing on its own).
- GET /api/analytics/summary?days=-5 → 422; ?days=99999 → 422; ?compare=2 → 422 (Pydantic
  bounds ge=0/le=3650, le=1 — clean refusals, not crashes).
- GET /api/analytics/timeseries?metric=views&days=7 → 200; 7 points, unit "views".
- GET /api/analytics/timeseries?metric=views&days=90 → 200; **14 points** for a
  days=90 / start=2026-08-25 claim, first point 2026-11-09 (finding B1).
- GET /api/analytics/timeseries?metric=watch_time&days=7 → 200; values 0,0,0,1,3,0,1 with
  unit "clips" — daily clip counts returned under the watch_time metric name (finding B5).
- GET /api/analytics/timeseries?metric=not_a_metric → 400; "PeakCut does not know that
  metric. Ask for one of: average_view_duration, average_view_percentage, comments, likes,
  shares, subscribers, views, watch_time." — right message, lists the real ones.
- GET /api/analytics/videos?days=7&limit=5 → 200; rows=[], total=0 (this install has no
  posts, so the days-filter gap is code-proven, not live-provable).
- GET /api/analytics/videos?days=28&limit=0 → 422 (ge=1).
- GET /api/analytics/audience?days=28 → 200; empty lists, honest note naming YouTube.
- GET /api/analytics/traffic?days=28 → 200; empty sources, honest note naming YouTube.
- GET /api/analytics/retention?video= → 400 "Paste a YouTube link or a video id."
- GET /api/analytics/retention?video=not-a-youtube-thing → 400, same sentence.
- GET /api/analytics/retention?video=dQw4w9WgXcQ → 400 "Retention comes from YouTube.
  Connect a channel under Connected apps." (no connection; right message).
- GET /api/jobs → 200; real clip id "clip01" in job "20261122-122201-798840cfbf".

Trends reads:

- GET /api/trends/status → 200; {"connected":false,"note":...} — no `source` key
  (finding B9).
- GET /api/trends/searches?days=28&limit=10 → 200; rows=[], source="peakcut", note names
  the missing connection. ?limit=0 → 422.
- GET /api/trends/videos?days=28&limit=10 → 200; rows=[], note names the missing
  connection and says this is not YouTube's trending chart.
- GET /api/trends/saved → 200; terms=[].

Trends save/remove flow (with cleanup, left the list empty):

- POST /api/trends/saved {"term":"qa audit test term"} → 200, saved.
- POST same term as "QA AUDIT TEST TERM" → 200; deduped case-insensitively, moved to top.
- POST JSON array body → 400 "Send a JSON object, like {\"term\": \"how to clip a stream\"}."
- POST blank term ({"term":"   "}) → 400 "Type a search term first, then save it."
- POST text/plain body "plain text not json" → 400 "Type a search term first, then save
  it." (finding B10 — the body could not be read, the message says to type a term).
- DELETE /api/trends/saved?term=qa%20audit%20test%20term → 200, list empty again.
- DELETE /api/trends/saved (no term) → 400 "Name the search term to remove."
- DELETE /api/trends/saved?term=never-existed-term → 200 no-op (documented behavior).

Code-level checks:

- All ytstats helpers called by both files exist with matching signatures
  (ytstats.analytics, ytstats.videos, ytstats._videos, ytstats.vid_id, ytstats.explain).
- posting.overview() shape: rows carry `creator_name` (studio/posting.py:275), and the
  daily graph is hard-capped at 14 days (studio/posting.py:277:
  `days = [_day(time.time() - 86400 * i) for i in range(13, -1, -1)]`).
- auth.throttle counts requests in a sliding window (studio/auth.py:57-69), which makes
  the trends-vs-analytics throttle difference real (finding B8).
- Frontend consumers verified: analytics-trends.js never calls /api/trends/status and
  handles fail/empty/loading per block; analytics-retention.js has loading/empty/error
  states and retry buttons, and requires an 11-character YouTube id
  (web/feat/analytics-retention.js:96-103); analytics-charts.js requests
  metric=estimatedMinutesWatched first and falls back to watch_time
  (web/feat/analytics-charts.js:58, 206-210).
- Test coverage read: tests/test_analytics_api.py and tests/test_trends_api.py cover the
  no-connection and refused-token paths well; none of them cover the 14-day local cap
  (days=90), the account_name field, the audience swallow-all note, the non-views local
  fallback, or the net-subscribers label (the gaps behind B1-B6).

No 500, no crash, no 404, and no wrong-metric refusal was found. Every invalid input
answered with a clean 400/422 and a sentence.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | studio/api_analytics.py:120-130 with studio/posting.py:277 | The local (no-YouTube) fallback covers only the last 14 days whatever window was asked; the response still echoes the full window, so wide presets show 14-day numbers labelled as 90-day/365-day/lifetime | Measured: `GET /api/analytics/timeseries?metric=views&days=90` → `{"days":90,"start":"2026-08-25","end":"2026-11-22"}` with **14 rows**, first point "2026-11-09". Code: `_own` sums `posting.overview()["daily"]`, which is at most 14 entries | When `days` exceeds what the daily graph holds, clamp `start` to the first day with data and add a note sentence ("PeakCut's own records cover the last 14 days; connect a channel for longer ranges") |
| important | studio/api_analytics.py:289 vs studio/posting.py:275 | The videos local branch reads `p.get("account_name")`, a field overview rows never carry (they carry `creator_name`), so the account column is always "" | `"account": p.get("account_name") or ""` at studio/api_analytics.py:289; overview builds `"creator_name": names.get(p["creator"], "")` at studio/posting.py:275 | Read `p.get("creator_name")` |
| important | studio/api_analytics.py:280-292 | The videos local branch ignores `days` entirely: rows come from all posts (queue + last 15 done) with no date filter while the response echoes the requested start/end/days | The loop `for p in o.get("posts") or []` has no date test; the same return claims `"days": days, "start": start, "end": end`. Not live-provable on this install (0 posts) | Filter rows by the post's date inside the window, or say in the note that the local list is not date bound |
| important | studio/api_analytics.py:334-369 | The audience route swallows every sub-query failure (`except: pass` at lines 344, 349, 356, 366) and line 368 unconditionally sets the success note; with a token whose every query fails the page gets source "youtube", empty lists, and a note that says the numbers are YouTube's | studio/api_analytics.py:340-367 (four try/except pass), studio/api_analytics.py:368 `out["note"] = "YouTube's own numbers. Hours are in your channel's own time zone."` — set whether or not anything arrived | Track whether any query succeeded; when none did, answer with the failure sentence (ytstats.explain(e)) and keep source honest instead of the success note |
| important | studio/api_analytics.py:251-256 | The timeseries local fallback answers daily **clip counts** for every metric except views: metric=watch_time/likes/subscribers/… returns clip counts under the requested metric name, so the Watch time chart plots clips | Measured: `GET /api/analytics/timeseries?metric=watch_time&days=7` → values 0,0,0,1,3,0,1 (the clips made those days), `"metric":"watch_time"`, `"unit":"clips"`. Line 252: `"value": d.get("views") if name == "views" else d.get("clips")`. The charts feature requests estimatedMinutesWatched first and falls back to watch_time (web/feat/analytics-charts.js:58, 206-210) | When the local data cannot answer the metric, return empty rows and a note that says the metric needs a YouTube connection — never clip counts under another metric's name |
| important | studio/api_analytics.py:210-211 (same computation at 228) | The "Subscribers gained" card value is `subscribersGained - subscribersLost` (net) while the label says "gained"; when subscribersLost > 0 the card understates gains | `"value": int(_num(r.get("subscribersGained")) - _num(r.get("subscribersLost")))` next to `"label": "Subscribers gained"` | Label it "Subscribers (net)", or report subscribersGained alone |
| important | studio/api_analytics.py:260, 296, 419 vs 200 | timeseries, videos and retention surface a YouTube failure as `HTTPException(400, str(e))` — Google's raw response text — while summary uses `ytstats.explain(e)`, the words the owner can act on; one failure class, two different messages | studio/api_analytics.py:260, 296, 419 (`raise HTTPException(400, str(e))`); studio/api_analytics.py:200 uses `ytstats.explain(e)`; the helper exists at studio/ytstats.py:122-138 | Use `ytstats.explain(e)` in all four routes |
| minor | studio/api_trends.py:78, 195, 223, 273, 324, 332, 368 | Trends routes spend the rate limit on every request, including cache hits — the exact thing studio/api_analytics.py:81-101 says must not happen ("Asking for a number we already hold costs nothing, so it must count for nothing") | `_throttle(u.id)` at the top of every trends route; trends `_cached` (line 78) takes no uid and never throttles; analytics `_cached` throttles only on a rebuild (studio/api_analytics.py:81-101). auth.throttle counts requests (studio/auth.py:57-69) | Pass uid into trends `_cached` and throttle only on a cache miss, as analytics does |
| minor | studio/api_trends.py:198-213 vs studio/api_analytics.py:149-173 | `GET /api/trends/status` omits the `source` key its sibling analytics status sends; a consumer keying on source gets nothing | Measured: trends status → `{"connected":false,"note":...}`; analytics status → `{"connected":...,"source":"peakcut","scope":...,"ranges":...,"note":...}`. The page does not read it today | Add `"source"` to the trends status answer |
| minor | studio/api_trends.py:334-342 | A body that cannot be read as JSON is answered "Type a search term first, then save it." — the person did send something; the message never says the body was unreadable | Measured: POST text/plain "plain text not json" → 400 "Type a search term first, then save it."; the `except` at 336-337 folds the JSON error into body={} and the blank-term branch answers | When `request.json()` raises, answer "That body could not be read as JSON. Send a JSON object, like {\"term\": \"...\"}." |

## Usability findings

| where | what | fix |
|---|---|---|
| Insights page wide presets (Last 90 days / 365 days / Lifetime) in local mode | The numbers behind them cover only 14 days and nothing on screen says so; a chart draws 14 points across a 90-day axis with no explanation (measured above) | Add the note sentence from finding B1 and clamp the chart's date labels to the days that have data |
| Trends tab, "Breakout videos" block (title drawn by web/feat/analytics-trends.js:232; route studio/api_trends.py:265-314) | The title says "breakout", but the route answers this channel's own videos ranked by views; the route's note explains it, the title does not. A beginner may expect YouTube's public trending chart | Rename the block to "Your videos this range", or lead the block with the route's note before the rows |
| Retention picker in local mode (web/feat/analytics-retention.js:96-103, 205; route studio/api_analytics.py:271-324) | The picker needs 11-character YouTube ids; the videos route's local branch answers PeakCut post ids, so the picker is empty and the page's empty sentence ("No videos in this range yet") can read false once posts exist | In the local branch, derive the YouTube id from the post URL when there is one, and have the route's note say the picker needs a connected channel |

## Notes for the fix wave

- One owner per file: fixes to studio/api_analytics.py belong to whoever owns it in the fix
  wave; the two usability fixes that touch web/feat/*.js belong to those files' owners.
- Both test files pass today for the paths they cover; B1, B2, B3, B4, B5 and the
  net-subscribers label have no test — add one each when fixing (a days=90 timeseries
  check that counts rows is the cheapest for B1).
- Colours untouched; no `!important`, no shadows introduced; this audit wrote no code.
