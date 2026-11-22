# analytics-traffic

## What I built

The Traffic tab of the Analytics page. It fills `#an_body` with the places the views came from.

- A horizontal bar list, one row per source, sorted by views, biggest at the top.
- Every row shows the name, a bar, the views, the watch time and the percentage.
- The bar width is the percentage. The top row is drawn in the brand orange, the rest in the pale brand line.
- Under the list, one sentence: the biggest source, its share, and what that source means for the next clip.
- Plain names for the YouTube source ids, so `shorts_feed` reads "Shorts feed" and `yt_search` reads
  "YouTube search". All eight named sources are covered, and an unknown one prints as sent.
- Watch time arrives in minutes, hours or seconds and is shown with its unit. Over an hour it reads in hours,
  and the exact minute count is in the tooltip.
- A percentage is accepted as a fraction or as a percent: the column has to add up to about 100, so the sum
  says which was meant. Sources sent without a percentage get one worked out from views.
- The date range sits in a pill beside the heading, taken from the shell, or from the answer if the shell
  has not said.

The tab guard is the part that matters most. Only one of the Audience and Traffic tabs may draw. This file
asks `window.PeakCutAnalytics.tab()` and returns before touching the DOM unless the answer is "traffic". It
asks again after the request comes back, so a click away mid-request writes nothing. The Audience tab has its
own file and its own bar for that.

Three states, each a sentence rather than a console line:

- Busy: "Reading the traffic sources..." while the request is out, drawn with the frame already in place.
- Empty: "No traffic sources in this range yet. A channel with at least one published clip fills this list,
  and Connected apps shows whether one is connected."
- Failure: the reason the server gave, in the page, then "Reload the page to try again."
- If the route says no channel is connected, that is said first, with a link to Connected apps.

## The file I own

`web/feat/analytics-traffic.js`, 179 lines. One plug-in, `analytics-traffic`. I touched no other file.
`web/index.html` is unchanged, and I did not edit any other agent's file.

Style comes from the page's own tokens and classes: `set-sec`, `set-body`, `help`, `pill`. Only the bar list
itself is new CSS, and it uses the existing colours, so it does not start a second design language. No shadows.
Hover is not used at all.

## The commands I ran and what they printed

```
node --check web/feat/analytics-traffic.js
JS OK
wc -l web/feat/analytics-traffic.js
179 web/feat/analytics-traffic.js
```

```
python tests/test_feat_files.py
{"files": 21, "checks": 174}
All checks passed.
```

```
python tests/test_menu_pages.py
All checks passed. 25 ok
```

I also ran the file under a stub of the page, with a fake `PeakCut`, `esc` and `document`, to prove the
drawing itself and not just the syntax:

- On the Traffic tab it drew three bars, sorted by views, first name "Browse features", and the sentence
  read "Browse features brought 41 percent of your views, so the title and the thumbnail are what people see
  first."
- On another tab it changed nothing: the body was byte for byte the same afterwards.
- A source name carrying `<img onerror>` came out escaped, never as markup.
- Minutes, hours and seconds all converted: 3.5 h, 10 min, 40 percent.
- Empty, no channel, and failure each rendered one plain sentence.

## What I could not do

- `GET /api/analytics/traffic` does not exist yet. `docs/swarm4/MASTER-PLAN.md` puts it in wave 2, so right
  now the page shows the failure sentence with the server's own reason. Nothing in this file needs to change
  when the route lands, as long as it returns a list under `sources`, or under `traffic`, `rows`, `items` or
  `data`, with `views`, a watch time, and a share.
- I did not run the page against a live server: there is no route to answer it yet, and the contract says not
  to restart the test server. The stub run above is the evidence I have.
- The test list has no separate check for this file's tab guard. `tests/test_feat_files.py` proves it parses,
  owns its one plug-in, escapes what it draws, and clashes with no id, but the "only your tab may draw" rule
  is checked by reading and by the stub run, not by a test.

Skill loaded: `frontend-design`.
