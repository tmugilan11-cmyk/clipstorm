# analytics-revenue

A revenue card for the Overview tab of Insights. It reads `/api/analytics/summary`, which already exists, and
adds no server route.

## What was built

One file, one plug-in: `analytics-revenue`. On load it finds the Overview panel drawn by `web/feat/analytics.js`,
appends one `<section class="arv" data-arv role="group">` at the end of that panel, and fills it from the same
`/api/analytics/summary?...` address the rest of the tab reads. The range comes from `window.PeakCutAnalytics`,
so the card follows the date picker and the compare toggle with everyone else.

Reading it:

- Every key in the answer is walked at any depth, including inside `cards: [{key, value}]`, and a key is a revenue
  figure only when its lowercased letters spell `revenue`, `estimatedrevenue`, `rpm` or `cpm`, optionally followed
  by a three-letter ending or one of amount/total/value/estimate/estimated/gross/net/money/earned/earnings.
  So `revenue`, `estimatedRevenue`, `rpm` and `cpm_total` are read, and `revenue_change`, `revenue_percent`,
  `rpm_bucket` and `revenue_model` are not: a percentage is not an amount.
- `compare` is read on its own, and a change pill appears only when both this period and the previous one sent a
  revenue figure, so no percentage is worked out from an empty base.
- The currency comes from `currency`, `currencyCode` or `revenueCurrency` when one of them holds three letters. It
  formats as `$128.44`, or as a plain number when no currency was stated.
- RPM and CPM are labelled "per 1,000 views".

When no revenue key arrives, the card is one sentence with no figures at all:

> Revenue needs a YouTube Partner Program channel, so there is nothing to show for this range yet.

There is no zero anywhere in that state. A zero only appears when the server literally sent `0`, and then it
prints as `$0.00` with its currency. When some of the three arrive and some do not, the ones that are missing show
a dash, the words "not sent", and one line saying a dash means the summary did not send that number rather than
that it was zero. If the request itself fails, the card says so in plain words and repeats the server's reason.

It never edits markup another file owns: the card is appended, and the panel's own boxes (`an_kpi`, `an_charts`,
`an_table`, `an_body`) are left alone. It invents no `id` at all, so it cannot clash with the frozen page or with
another agent's file.

## Files

- `web/feat/analytics-revenue.js` (new, 218 lines). The only file I wrote in the app.
- `docs/swarm4/wave2/analytics-revenue.md` (new, this report).

Nothing else was touched. `web/index.html` was not edited, and no server file was changed.

## What I ran

Gates:

```
$ node --check web/feat/analytics-revenue.js
node --check: OK          (no output from node; exit code 0)

$ python tests/test_feat_files.py
ok   analytics-revenue.js parses
ok   analytics-revenue.js declares one plug-in
ok   analytics-revenue.js is named after itself
ok   analytics-revenue.js is the only owner of analytics-revenue
ok   analytics-revenue.js does not write into index.html
ok   analytics-revenue.js draws only fixed markup
ok   analytics-revenue.js uses no absolute origin
ok   analytics-revenue.js invents no clashing id
{"files": 37, "checks": 302}
All checks passed.

$ python tests/test_menu_pages.py
All checks passed. 142 ok
```

The `files` and `checks` counts move between runs because other wave-2 agents are adding files at the same time.
My own eight lines pass on every run.

Live server:

```
$ curl -s http://127.0.0.1:8798/assets/feat | grep analytics
[... 'analytics-export.js', 'analytics-kpi.js', 'analytics-realtime.js', 'analytics-revenue.js', ...]

$ curl -s -o /dev/null -w "%{http_code} %{size_download}\n" http://127.0.0.1:8798/assets/feat/analytics-revenue.js
200 12766

$ curl -s "http://127.0.0.1:8798/api/analytics/summary?days=28"
200 ['source', 'days', 'start', 'end', 'cards', 'compare', 'note']
```

That last line is the reason the quiet state is the one you see today: the route sends no revenue key on this
server, in either the PeakCut branch or the YouTube branch.

In the real page (Chromium, `http://127.0.0.1:8798/app/analytics`, Overview tab), with the real server:

```
{"cards":1,"text":"Revenue\nOct 23 to Nov 19\n\nRevenue needs a YouTube Partner Program channel,
 so there is nothing to show for this range yet.","numbers":0,"cells":0}
```

One card, one sentence, zero numbers, and `querySelectorAll('[data-arv]').length === 1` after a reload, after
switching to Content and back, and after changing the range from 28 days to 7 (the range line followed to
"Nov 13 to Nov 19" and the signature became `...&days=7`). It does not duplicate itself.

Then I replaced `window.PeakCut.api` for the summary address only with a canned YouTube-shaped answer, forced a
reload of the card, and read the real DOM. The screenshot is
`C:\Users\Asus\Downloads\analytics-revenue.png`:

```
Revenue   Oct 23 to Nov 19   28%
Revenue  $128.44  USD
RPM      $3.13    per 1,000 views
CPM      –        not sent

Not in this answer yet: CPM. A dash means the summary did not send that number, not that it was zero.
```

Measured on that card: 1216x178 px, number 22px weight 600 in `rgb(42, 26, 18)`, a 1px `rgb(238, 232, 228)`
border, so it sits on the existing palette with no shadow. The stub was then dropped by reloading the page.

I also ran the file headless in node against a fake DOM and eight server answers. Two worth quoting:

```
=== no revenue keys at all (the live server today) ===
Revenue 23 Oct to 19 Nov Revenue needs a YouTube Partner Program channel, so there is nothing to show
for this range yet.

=== revenue nested in a card list, with currency ===
Revenue 23 Oct to 19 Nov 28% Revenue $128.44 USD RPM $3.13 per 1,000 views CPM - not sent
Not in this answer yet: CPM. A dash means the summary did not send that number, not that it was zero.

=== a sent zero is a real zero, an absent key is not ===
Revenue 23 Oct to 19 Nov Revenue GBP 0.00 RPM - not sent CPM - not sent

=== the summary could not be read ===
Revenue 23 Oct to 19 Nov The summary could not be read. Network is down. Reload this page to try again.
```

The last case matters because it actually happened by itself: for a few minutes the running server's rate limiter
refused the analytics calls and the card said, on the real page, "The summary could not be read. That is a lot of
analytics calls at once. Give it a moment. Reload this page to try again." It then went back to the quiet state
once the limiter cleared.

## Anything I could not do

- I could not see the card with real revenue numbers, because this server sends none. The `$128.44` above came
  from a canned answer installed in the page for one measurement, not from `/api/analytics/summary`. If a later
  wave adds revenue to that route, this card picks it up with no change, but nobody has watched it happen against
  a real YouTube Partner Program channel.
- The card is placed at the end of the Overview panel. If another agent later wants it higher up, that is a
  change to this one file: the panel is found by `[data-an-panel="overview"]`, so position is decided by where
  `append` puts it.
- Nothing about this card is in a menu, and no server route was added, so `tests/test_menu_pages.py` covers it
  only by confirming the page it lives on still draws.
