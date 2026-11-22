# analytics-kpi

What I built: `web/feat/analytics-kpi.js`. It fills `#an_kpi` inside the Analytics page with six number
cards in one row: Views, Watch time, Impressions, Click-through rate, Average view duration,
Subscribers gained. Each card shows the label, the number, the unit, a change pill, and the date range
under the number. It reads `/api/analytics/summary` with the range and compare values that
`window.PeakCutAnalytics` hands over, and never draws a number the route did not send.

The file I own: `web/feat/analytics-kpi.js` (180 lines). I did not touch any other file, including
`web/index.html`.

What I ran and what it printed:
- `node --check web/feat/analytics-kpi.js` prints `JS OK`.
- `python tests/test_feat_files.py` prints `{"files": 27, "checks": 222}` then `All checks passed.`
- `python tests/test_menu_pages.py` prints `All checks passed. 91 ok`
- I also ran the file against four faked answers (full, partial, comparison off, request throws) and
  against the live route, which answers 200 with `"source":"peakcut"`.

Things worth knowing, in plain words.

1. The live route already existed, so I read it instead of guessing. `GET /api/analytics/summary`
   takes `days` and `compare` and answers with a list of cards, a start, an end, and the previous
   period. It does not read `start` or `end`: when I asked for 24 Oct to 20 Nov it answered
   23 Oct to 19 Nov, which is 28 days back from today. My card range line therefore prints the dates
   the route actually used, not the dates I asked for. A card that showed the asked range over a
   different set of numbers would be a lie.

2. Without a connected channel the route answers `"source":"peakcut"` with PeakCut's own counters, and
   its `views` card is labelled "Views PeakCut tracked". That is not YouTube views. So when the source
   is `peakcut` I draw six dashes and show the route's own sentence with a link to Connected apps. I do
   not print PeakCut's counter in the Views card.

3. The route has no impressions and no click-through rate at all. It carries views, watch_time,
   average_view_duration, average_view_percentage, subscribers and engagement. So Impressions and
   Click-through rate will show a dash and the line "Not in this answer yet: Impressions,
   Click-through rate." until someone adds those keys to the route. That is the honest state, but it
   means two of the six cards cannot fill from the current route. Adding `impressions` and `ctr` to
   `studio/api_analytics.py` is a one small change for whoever owns that file. I did not make it,
   because it is not my file.

4. `window.PeakCutAnalytics` exposes `range` and `compare` as getter functions, not as objects. My
   first version read them as objects and quietly asked for no particular range. It now calls them.

5. When the comparison toggle is off, the route sends no previous cards, so every change pill shows a
   dash. I do not compute a percentage from a period the user turned off.

6. The container `#an_kpi` belongs to `analytics.js`, which another agent owns. My file registers
   `PeakCut.add("analytics-kpi", ...)` with a `load`, and also starts one `MutationObserver` on `#view`
   so the band fills when the page is first drawn without a reload. The shell calls `load()` again on
   a range change, and my file skips a redraw when the address has not changed.

Skill: `frontend-design`.

What I could not do: fill Impressions and Click-through rate, because the route does not send them.
