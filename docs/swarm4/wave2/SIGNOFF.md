# Signoff: Insights page, wave 2

Skill loaded: `webapp-testing`.

Page tested: `http://127.0.0.1:8798/app/analytics`, in the shared browser, at
2,048 px wide, signed in as `stream_sniper_369` with no YouTube channel connected.

## Verdict

The page is usable. All five tabs draw, all five date ranges work, Compare toggles
and reports the correct previous period. Nothing threw or logged a console error in
any pass. Two defects are worth fixing before this is called finished, and both are
listed under "What is wrong" below. Neither one blocks reading the page, because in
both cases the page says in plain words what is missing instead of showing a wrong
number.

## Tabs

Measured on a fresh load with the range at Last 28 days. "Nodes" is the number of
elements inside the box that the tab fills, counted with `querySelectorAll('*').length`.

| Tab | Label read from the button | Panel drew | Box filled | Child elements | Nodes | Console error |
|---|---|---|---|---|---|---|
| Overview | "Overview" | yes | `#an_kpi` + `#an_charts` | 2 + 1 | 69 + 31 | none |
| Content | "Content" | yes | `#an_table` | 1 | 18 | none |
| Audience | "Audience" | yes | `#an_body` | 4 | 19 | none |
| Trends | "Trends" | yes | `#an_body` | 1 | 20 | none |
| Traffic | "Traffic" | yes | `#an_body` | 1 | 7 | none |

The panel wrapping each box has these element counts: Overview 5, Content 4,
Audience 2, Trends 2, Traffic 2.

`aria-selected` was `"true"` on exactly the clicked button on every pass. The
`hidden` attribute moved to the right panel each time. The heading under the tab bar
changed to match: Audience showed "Who is watching this channel.", Trends showed
"How these numbers moved over the range on screen.", Traffic showed "Where the views
came from.", Overview and Content carry their own line inside the panel instead.

What each tab actually said:

- Overview: six cards, all showing a dash with the words "PeakCut's own records.
  Connect a channel". The watch time chart drew a real line from 0 to 2 over 14 days.
  The views chart showed "No views in this range yet."
- Content: "0 videos" and "Every number covers Oct 24, 2026 to Nov 20, 2026." then
  "No videos in this range yet. Publish".
- Audience: 4 children, opening with "Viewer types, countries and hours come from
  YouTube. Connect a channel to see them."
- Trends: 20 nodes, opening with "Showing 24 Oct 2026 to 20 Nov 2026. The page is set
  to Last 28 days." then "Top searches".
- Traffic: 7 nodes, "Traffic sources" and "Oct 24 to Nov 20" and "Where the views came
  from, biggest source first."

## Date ranges

Each range was set through the select and the change event was dispatched, then the
page was given 1.8 s to ask and draw.

| Value | Header line | Range label on the first KPI card | `#an_kpi` nodes | `#an_charts` nodes | Chart SVGs | Compare enabled |
|---|---|---|---|---|---|---|
| 7 | Last 7 days, ending 20 Nov 2026 | Nov 14 to Nov 20 | 69 | 30 | 1 | yes |
| 28 | Last 28 days, ending 20 Nov 2026 | Oct 24 to Nov 20 | 69 | 31 | 1 | yes |
| 90 | Last 90 days, ending 20 Nov 2026 | Aug 23 to Nov 20 | 69 | 31 | 1 | yes |
| 365 | Last 365 days, ending 20 Nov 2026 | **Nov 21 to Nov 20** | 69 | 31 | 1 | yes |
| life | Lifetime, up to 20 Nov 2026 | **Nov 23 to Nov 20** | 69 | 31 | 1 | no |

The requests matched each choice: `days=7`, `days=28`, `days=90`, `days=365` and
`days=3650` with `start=2005-01-01`. The server capped days at 3650 itself and
answered `start: "2016-11-23"` for the Lifetime call. Every one of those requests
returned 200.

## Compare

Ticked at Last 28 days. The checkbox went from unchecked to checked.

- The note under the label changed from "Off" to **"26 Sept 2026 to 23 Oct 2026"**.
  That is the correct 28 days before Oct 24 to Nov 20. I checked the arithmetic and
  it holds.
- The header line became "Last 28 days, ending 20 Nov 2026, compared with the 28 days
  before".
- `#an_kpi` went from 69 to 82 nodes. Six `.akcmp` rows appeared. All six read
  "Not sent for the 28 days before" after a dash, and all six `.pill` elements read
  "–". That is correct and honest: the server sent `compare: null`, so there is no
  previous number to show. The page did not invent one.
- Turning Compare on at Lifetime is refused by the control itself: the checkbox is
  `disabled` and the note reads "Off for Lifetime". That is the right call.
- `#an_charts` broke. See the first defect.

## What is wrong

### 1. The two charts empty out when Compare is ticked

Reproduced three times from a clean reload.

| Moment | `#an_charts` nodes | SVGs | What it says |
|---|---|---|---|
| Fresh load, Compare off | 31 | 1 | Views chart plus a drawn watch time line |
| Compare on, +600 ms | 0 | 0 | nothing |
| Compare on, +1,400 ms | 0 | 0 | nothing |
| Compare on, +2,600 ms | 7 | 1 | "The charts are empty. No daily views or watch time arrived for this range." |

The cause is in `peakcut/web/feat/analytics-charts.js`, in `chosen()` around line 70.
It calls `obj(A.range)` and `obj(A.compare)` directly. On this page both of those are
**functions**, not values, so `obj()` returns `null` for each. The compare dates are
never added to the query string, so the request this file makes is identical before
and after the tick. The shell clears `#an_charts` on reload, the file decides the
query has not changed and skips refetching, and `analytics-empty.js` then correctly
decides the box is empty and writes its line into it.

`analytics-compare.js` already does this correctly, at line 93:
`const cmp = object(val(A.compare));` with `val` unwrapping functions. The charts
file needs the same unwrap. There is a second, smaller bug in the same call: when
`obj(A.range)` returns null it falls back to `A`, and `A.days` is the number 7994 at
Lifetime, so the query string ends up with `days=7994` while the server caps it at
3650.

The measured difference, computed in the live page:

```
query the file builds now:   &&days=28&start=2026-10-24&end=2026-11-20
query it should build:       &days=28&start=2026-10-24&end=2026-11-20&compare_start=2026-09-26&compare_end=2026-10-23
```

Note the leading `&&` in the first line, which is the null range object showing through.

The file that is supposed to fill this box is `peakcut/web/feat/analytics-charts.js`.

### 2. The 365 day and Lifetime KPI range labels read backwards

At 365 days the card says "Nov 21 to Nov 20". At Lifetime it says "Nov 23 to Nov 20".
A range whose start comes after its end reads as a mistake even though the numbers
under it are correct. Both are formatted by `range()` in
`peakcut/web/feat/analytics-kpi.js` at line 80, which takes the start and end straight
off the server answer. The server is what sends them: for the 365 day call it answers
`start: "2025-11-21"`, and for Lifetime `start: "2016-11-23"`. The formatter in that
file prints day and month with no year, so a start in a previous year looks like it
comes after the end.

Two separate things are going on. The missing year is a display bug in
`analytics-kpi.js`. The Lifetime start of 2016-11-23 is the server's own floor, from
`_window()` in `studio/api_analytics.py`, and is right for PeakCut's own records, but
the page asks for 2005 and is quietly given 2016 without being told. That mismatch
lives between `analytics.js` and the route.

### 3. One request is refused with a 400 on every range

`GET /api/analytics/timeseries?metric=estimatedMinutesWatched` returns **400** every
time, with this body:

```
{"detail":"PeakCut does not know that metric. Ask for one of: average_view_duration,
average_view_percentage, comments, likes, shares, subscribers, views, watch_time."}
```

The charts file tries `metric=estimatedMinutesWatched` first and only falls back to
`metric=watch_time` after the refusal, at `analytics-charts.js` line 206 through 210.
The fallback works, the chart draws, and nothing is visible to the reader. It still
costs a wasted request and a 400 on every load. The one line causing it is line 58,
where the Watch time chart declares `metric: "estimatedMinutesWatched"`. The route at
`studio/api_analytics.py` line 240 expects `watch_time`.

This is the only non 200 response the page produced. There were no console errors at
any point: I installed a listener on `error`, `unhandledrejection`, `console.error` and
`console.warn` before the first click and it recorded an empty list across all five
tabs, all five ranges and both states of Compare. The browser console tool also
reported no lines.

## Is it usable

Yes. A person can open Insights, pick a range, read six key numbers with their date
range stated, read a content table, read audience, trends and traffic, and understand
in every case why a number is a dash. No blank box, no invented figure, no console
error, no unhandled failure.

It is not correct yet. Ticking Compare silently deletes the charts, and two range
labels read backwards. Both are one line fixes in files that other agents own, so I
have not touched them.

## Files

- `peakcut/docs/swarm4/wave2/SIGNOFF.md`, this report. The only file I wrote.

I changed no feature file. The two defects above are in
`peakcut/web/feat/analytics-charts.js` and `peakcut/web/feat/analytics-kpi.js`, which
belong to other agents.

## Commands run and their literal output

```
$ cd peakcut && node --check web/feat/analytics.js && echo "JS OK"
JS OK

$ cd peakcut && node --check web/feat/analytics-charts.js && echo "JS OK"
JS OK

$ cd peakcut && python tests/test_feat_files.py
...
ok   style-tiles.js invents no clashing id
ok   loader keeps the documented folder
{"files": 37, "checks": 302}
All checks passed.
```

Browser side, all through the shared browser at 2,048 px. The page reports 38
registered features, and all 14 `analytics-*` files are in `window.PeakCut._order`:

```
analytics-charts, analytics-audience, analytics-compare, analytics-help,
analytics-empty, analytics-export, analytics-kpi, analytics-retention,
analytics-realtime, analytics-revenue, analytics-table, analytics-shorts,
analytics-traffic, analytics, analytics-trends
```

## What I could not do

- I could not test the page with a YouTube channel connected, because no channel is
  connected on this server. Every number is therefore a dash, and the "real number"
  paths in all five tabs are unexercised. The shells, the empty states, the range
  plumbing and the error paths are all covered above.
- I could not test a narrow viewport. The page declares a 640 px breakpoint in
  `analytics.js` at line 17, and I left it untested rather than claim it works.
- I did not run `tests/test_menu_pages.py`, because that gate belongs to the agents
  who own the page registration and my task is to observe the page, not to change it.
