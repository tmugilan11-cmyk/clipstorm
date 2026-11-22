# analytics-realtime: the "Right now" card

Skill loaded before any writing: `frontend-design`.

## What it does

A card at the top of the Insights Overview tab, under the KPI strip and above the charts. It
answers one question: how many views came in over the last 24 hours.

- Headline number, then the sentence **Views in the last 24 hours**. That sentence only ever
  appears when the server actually sent a count for today.
- A line under it naming where the number came from and the day it covers, for example
  `PeakCut's own records, for Nov 20, checked 05:19 AM`.
- When the server sent no count for today, the card shows a dash and a sentence saying so, plus
  whatever note the route sent. It never shows a zero it did not receive, because zero and
  "nothing arrived" look identical in a card.
- When a request fails, the failure is a sentence in the card and the last good number stays on
  screen rather than turning into a dash.
- When the day turns over while the page is open, the count kept from yesterday stops being
  presented as today's. The card says the day turned over and fills in on its next check.

Refresh: one timer at 61 seconds. The floor inside `fill()` is 60 seconds, so a range change, a
tab switch, or a manual redraw inside that minute asks the server nothing. Nothing is asked at all
while `document.hidden` is true, and nothing is asked while the card sits on a panel that is not
the one on screen. The timer is cleared as soon as the card leaves the document, and put back if a
redraw brings it back.

## The one judgement call

The brief says to call `/api/analytics/summary?days=7` and show the newest day's views. That route
does not carry a per-day number. Its shape is:

```json
{"source":"peakcut","days":7,"start":"2026-11-13","end":"2026-11-19",
 "cards":[{"key":"views","label":"Views PeakCut tracked","value":0,"unit":"views"}, ...],
 "compare":null,"note":"..."}
```

There is no `today`, no `last_24`, no row per day. The only route that answers with a value per day
is `/api/analytics/timeseries?metric=views&days=7`, whose `rows` end at the newest day.

So the card calls both. The summary comes first, because the brief asks for it, and it supplies the
`source` and `note` the card prints. The timeseries supplies the number. Rule 6 says never a number
you did not receive, and rule 5 says a shared number belongs in the server route: inventing a
"today" field on the client from the summary's `end` would have been exactly that invention.

The second judgement: which day counts as today. `_window()` in `peakcut/studio/api_analytics.py`
stamps `end` with `datetime.now(timezone.utc).date()`, while `posting._day` builds each `day` string
with `time.strftime("%Y-%m-%d", time.localtime(t))`. On this machine (UTC 2026-11-19 23:21, local
+0530) the window said `end` 2026-11-19 while the newest row said 2026-11-20. Comparing the row to
`end` would have hidden the number permanently east of UTC. The first draft of this file compared
against `end` with a day of slack, and a test proved that let a stale day still print "Views in the
last 24 hours", so that version was wrong in the other direction. The rule now is the reader's own
clock: a row is today only when its day equals the reader's local date. The words "last 24 hours"
belong to whoever is reading the page.

## Exact files

- `peakcut/web/feat/analytics-realtime.js`, new, 200 lines. The only file written in the app.
- `peakcut/docs/swarm4/wave2/analytics-realtime.md`, this report.

Nothing else was touched. `peakcut/web/index.html` was not edited.

The card makes its own node. The shell in `peakcut/web/feat/analytics.js` owns four boxes
(`an_kpi`, `an_charts`, `an_table`, `an_body`) and the Overview panel holds only the first two, so
this file creates `div.annow` and inserts it after `#an_kpi`, inside
`[data-an-panel="overview"]`. It writes into no box the shell owns. Its CSS arrives through
`P.css("analytics-realtime", ...)` and every class is prefixed `.annow`.

## What I ran

Gates, from `peakcut/`:

```
$ node --check web/feat/analytics-realtime.js
node ok

$ python tests/test_feat_files.py
ok   loader keeps the documented folder
{"files": 37, "checks": 302}
All checks passed.

$ python tests/test_menu_pages.py
All checks passed. 142 ok
```

Style checks on the file:

```
em dash: 0 | en dash: 0 | emoji: False
adds: ['analytics-realtime']
window.ic/esc: False False
icons: ['clock']
lines: 200
```

The file uses exactly one `esc(`-guarded `innerHTML` write (through `put`, with an assignment
fallback), one icon (`clock`, a real name from the 58), and no other icon. `esc`, `ic` and `put`
are called as bare identifiers.

A throwaway harness at the workspace root (`rt-harness.js`, not a deliverable, deleted once the
checks below passed) ran the real file in `node:vm` against a fake DOM, with the live JSON from
both routes saved beside it. Its final run:

```
pass one plug-in, named after itself | ["analytics-realtime"]
pass card made inside the Overview panel
pass card sits right after #an_kpi | index 1
pass asked the summary first | /api/analytics/summary?days=7
pass asked the timeseries too | /api/analytics/timeseries?metric=views&days=7
pass one timer, no faster than 60 seconds | 61000
pass shows the number with its unit | value=0 unit=views
pass says "Views in the last 24 hours"
pass names the day it covers | for 20 Nov
pass a range change inside 60 seconds does not ask again | 2 -> 2
pass a hidden tab never asks | 2 -> 2
pass a card on another tab does not ask | 2 -> 2
pass the timer stops when the card leaves the page | timers 0
pass a redraw puts the card back
pass asked again once the minute passed | 2 -> 4
pass no sentence about the last 24 hours without a number
pass shows a dash instead of a number | value=–
pass says what it needs in a sentence
pass a fresh number is shown | value=0 unit=views | Views in the last 24 hours
pass the day after, a kept number stops being called today's
pass the day after, the card shows a dash again | value=–
pass the day after, nothing extra was asked | 6 -> 6
pass a failure is a sentence | Today's views could not be read. The request failed.
pass a failure keeps the last good number
ALL PASS
```

Live checks in the browser at http://127.0.0.1:8798/app/analytics, after a real reload:

```
{"card":true,"panel":"overview","index":2,
 "text":"Right now 0views Views in the last 24 hours PeakCut's own records, for Nov 20, checked 05:19 AM",
 "cards":1}
```

and the styling, read from the live element:

```
{"radius":"12px","bg":"rgb(255, 255, 255)","shadow":"none","border":"rgb(238, 232, 228)",
 "dotBg":"rgb(15, 138, 87)","dotShadow":"none","numSize":"26px","numColor":"rgb(42, 26, 18)"}
```

That matches the `#an_kpi` tile beside it: white background, 12px radius, and the same border
colour `#EEE8E4`. No shadow, which is also the house rule for the rest of this page.

Two live probes on the running page, wrapping `fetch` and reading the timestamps:

- Tab hidden for 145 seconds: zero `/api/analytics/*` requests.
- Tab forced visible with `document.hidden` overridden and a `visibilitychange` event: the card
  asked at 44 seconds and not again inside the 149 second window. That miss was a real bug: a
  60000 ms interval can fire a millisecond before the 60000 ms floor opens, the floor refuses it,
  and a whole turn is skipped. The timer now runs at `GAP + 1000`, so every turn lands inside the
  floor but past it. This is the `TICK` constant in the file, with a comment saying why.

Deleting the card node and watching the page showed the timer cleared once, the card rebuilt on
the next redraw, and exactly one card on the page afterwards.

## What I could not do

- No real traffic to read. The PeakCut instance has three clips and no YouTube connection, so both
  routes answer `value: 0` and the card prints `0 views`. The zero is the server's own number, not
  a placeholder, and the note under it says PeakCut's records are what is being counted. The path
  that shows a number other than zero has been proven in the harness with the same live JSON shape,
  but not against a channel with views.
- The card cannot show a per-day history or a trend, only the newest day. That is the whole of what
  the two routes support for "right now", and rule 5 rules out asking a second page's route for it.
- I did not add the card to `peakcut/web/index.html` or to `analytics.js`. Both were out of bounds
  for this task, so anyone reading the shell alone will not see the card in the markup: it appears
  at runtime, inside the Overview panel.
