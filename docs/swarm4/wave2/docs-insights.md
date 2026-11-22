# docs-insights

A written guide to the Insights menu row, for a person who has never opened the page. It is documentation only:
no route, no feature file and no `web/index.html` change.

Skill loaded: `fastapi-patterns`. It shaped the reading of `studio/api_analytics.py`, in particular the query
bounds (`ge`, `le`), the `source` switch between the PeakCut branch and the YouTube branch, the per-block
try/except in the audience route, and the difference between a route that returns 400/422 and one that returns an
empty-but-successful answer.

## What was built

One new markdown file, `docs/INSIGHTS.md`, 111 lines, 899 words, pure ASCII. It answers, in this order:

- What the row is. Insights sits under **Understand**, opens at `/app/analytics`, and has five tabs: Overview,
  Content, Audience, Trends, Traffic.
- Where the numbers come from. Every answer carries `source`. `youtube` means YouTube's own Analytics numbers;
  `peakcut` means PeakCut's own records or an empty answer with a sentence naming what is missing. A number that
  did not arrive is a dash with a sentence, never a zero.
- What the date ranges mean. A table for 7 / 28 (default) / 90 / 365 / Lifetime (from 1 January 2005), the
  Compare checkbox and the header wording it produces, then the two-minute cache and the 120-per-minute 429.
- What each tab shows, with the real metric ids: `views`, `estimatedMinutesWatched`, `averageViewDuration`,
  `averageViewPercentage`, `subscribersGained`, `subscribersLost`, `likes`, `comments`, `shares`; dimensions
  `day`, `video`, `country`, `day,hour`, `insightTrafficSourceDetail` (filtered to
  `insightTrafficSourceType==YT_SEARCH`), `insightTrafficSourceType`; retention on `elapsedVideoTimeRatio` with
  `audienceWatchRatio` and `relativeRetentionPerformance`.
- Which numbers need a connected channel and which PeakCut can answer alone, as two lists.
- How to connect a channel, in four steps, including the three scopes and why the third one matters.
- Three limits of this build, each stated as a symptom the reader will actually see.

Every claim was read out of the file that implements it. The two places where the code and the obvious
assumption disagreed are written into the doc rather than smoothed over:

1. Without a channel the six key numbers do **not** show PeakCut's own counters. The route sends them
   (`studio/api_analytics.py:181-190`), but `web/feat/analytics-kpi.js:107` only reads `b.cards` when the
   answer's source is not `peakcut`, so all six cards draw a dash plus the "Connect a channel" sentence. The doc says
   exactly that.
2. Lifetime does not work on the key numbers. The shell builds a span from 1 January 2005
   (`web/feat/analytics.js:44-46`), which is about 8000 days, and every route taking `days` is capped at 3650
   (`le=3650`), so the request is rejected and the cards stay dashed.

## Files

- `docs/INSIGHTS.md` (new). The deliverable.
- `docs/swarm4/wave2/docs-insights.md` (new, this report).

Nothing else was written. `web/index.html` was not edited, no server file was changed, and no other agent's file
was touched.

## What I ran

Markdown has no `node --check` step, so the two repository gates are the whole check:

```
$ cd peakcut && python tests/test_feat_files.py
...
{"files": 37, "checks": 302}
All checks passed.
EXIT=0
```

```
$ cd peakcut && python tests/test_menu_pages.py
...
All checks passed. 142 ok
EXIT=0
```

Word count and the style rules, measured on the file itself:

```
$ wc -w docs/INSIGHTS.md
899 docs/INSIGHTS.md

$ python -c "t=open('docs/INSIGHTS.md',encoding='utf-8').read(); ..."
bytes 5790 words 899 nonascii 0
em/en dash 0 0
exclam 0
spaced hyphen 0
```

So: under the 900 word cap, no non-ASCII character at all, no em dash, no en dash, no exclamation mark, no
spaced hyphen. Icons are irrelevant here (the doc contains no markup and no feature code), and the doc names no
icon.

The counts in the gates move between runs because other wave-2 agents are adding files at the same time.

Facts were checked against the running server at `http://127.0.0.1:8798` before being written, on this instance
which has no channel connected:

```
GET /api/analytics/summary?days=28                     200  six PeakCut cards, source peakcut
GET /api/analytics/summary?days=7994                   422  "Input should be less than or equal to 3650"
GET /api/analytics/summary?days=3650&compare=1         200
GET /api/analytics/traffic?start=2005-01-01&end=...    200  echoes days:28, start:2026-10-23, end:2026-11-19
GET /api/analytics/videos?from=2005-01-01&to=...       200  echoes days:28
GET /api/analytics/retention?video=                   400  "Paste a YouTube link or a video id."
GET /api/trends/searches?days=0                        200
```

The traffic and videos echoes are why the last bullet under "Limits of this build" exists: the Content table and
the Traffic tab send dates, the routes read a day count instead, so both answer a 28 day window whatever the
header says.

## Anything I could not do

- I could not verify the connected-channel path end to end. No YouTube channel is connected on this instance, so
  the six YouTube cards, retention, countries, hours, search terms and traffic sources were all read from source
  and from the route's own no-connection branches, not from a live successful answer. The doc describes what the
  code sends in that state, and every sentence about it is traceable to `studio/api_analytics.py` or
  `studio/api_trends.py`.
- `docs/menu.md` line 20 still lists four tabs for Analytics. It is stale now that Trends exists, but it is not my
  file, so I left it alone and noted the discrepancy here instead.
- One wording inconsistency in the code, not fixed and not mine: `web/feat/analytics-empty.js` links
  `/app/apps` while the other five files link `/app/settings/apps`. Both routes reach a real Connected apps
  screen, so the doc uses `/app/settings/apps` and the reader is not misled either way.
