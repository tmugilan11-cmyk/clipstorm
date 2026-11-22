# Insights page guard: `tests/test_insights_pages.py`

## What I built

One file, no test framework, plain asserts in the shape of `tests/test_menu_pages.py`: a
`check(name, good, detail)` that prints one line, `ok` and `bad` lists, and an exit code of 1
when anything fails. It reads files from disk, so it needs no server, no browser and no
database.

It holds the Insights page together while sixteen other agents add plug-ins to it. The page
is one shell (`web/feat/analytics.js`) and a folder of small files (`web/feat/analytics-*.js`),
each filling one box in that shell. The test checks five things about that set.

## What it checks, and why each one is worth a check

1. **Every `analytics-*.js` parses.** `node --check` on each file, since a file with a typo
   breaks the whole page at load time and is easy to miss while four agents edit the folder.
2. **Each file declares exactly one plug-in, and that plug-in is named after the file.**
   The name comes from `PeakCut.add("<name>", ...)`. A name that does not match the file name
   means one agent has quietly taken another agent's slot, and the second registration
   silently wins or is lost.
3. **The Insights page itself is still registered**, as `PeakCut.page("analytics", ...)`, and
   it still keeps the address `analytics`, because the sidebar row and the browser address
   depend on it. It also wants a short menu label.
4. **The Trends tab still exists in `analytics.js`.** The tab list is read out of the `TABS`
   array, the `trends` key is looked for, and the tab must carry a label. A tab with an empty
   label is a blank button in the row.
5. **Every request a plug-in makes lands on a route the server actually answers.** Routes are
   collected from `studio/*.py` with a regex over `@router.get(`, `@router.post(`, `app.get(`
   and `app.post(`. The routers are mounted with no prefix in `studio/server.py`, so a
   decorated path is the path the browser asks for. A plug-in asking for a route that does not
   exist shows an empty box and a failure sentence, which is exactly the kind of thing that is
   hard to notice until a person clicks the tab. Files that ask for nothing are reported as
   such rather than passed silently, so a plug-in that lost its fetch is visible too.
6. **No analytics file hard-codes an origin.** `http://127.0.0.1`, `https://127.0.0.1`,
   `http://localhost` and `https://localhost` are all refused. PeakCut runs on whichever port
   the person chose; a baked origin stops working the moment the port changes.

## Files

- `tests/test_insights_pages.py` (new, 148 lines)

I touched nothing else. `web/index.html` is frozen and untouched.

## What I ran

```
cd peakcut
python tests/test_insights_pages.py
python tests/test_feat_files.py
python tests/test_menu_pages.py
```

Output of the new test, as printed:

```
ok   studio files say what routes they answer   130 routes
ok   the Insights folder has plug-in files   14 files
ok   analytics-audience.js parses
ok   analytics-charts.js parses
ok   analytics-compare.js parses
ok   analytics-empty.js parses
ok   analytics-export.js parses
ok   analytics-help.js parses
ok   analytics-kpi.js parses
ok   analytics-realtime.js parses
ok   analytics-retention.js parses
ok   analytics-revenue.js parses
ok   analytics-shorts.js parses
ok   analytics-table.js parses
ok   analytics-traffic.js parses
ok   analytics-trends.js parses
ok   analytics-audience.js declares one plug-in   found ['analytics-audience']
ok   analytics-audience.js is named after itself
ok   analytics-audience.js is the only owner of its name
   ... one block of three lines per file, 14 files ...
ok   analytics.js is there
ok   the Insights page is registered
ok   the Insights page keeps the analytics address   analytics
ok   the Insights page has a menu label   Insights
ok   analytics.js declares its tabs   overview, content, audience, trends, traffic
ok   the Trends tab exists   tabs are: overview, content, audience, trends, traffic
ok   the Trends tab has a label   Trends
ok   analytics-audience.js fetches only routes this server has   /api/analytics/audience
ok   analytics-charts.js fetches only routes this server has   /api/analytics/timeseries
ok   analytics-compare.js fetches only routes this server has   /api/analytics/summary
ok   analytics-empty.js asks the server for nothing   draws from what is already on the page
ok   analytics-export.js asks the server for nothing   draws from what is already on the page
ok   analytics-help.js asks the server for nothing   draws from what is already on the page
ok   analytics-kpi.js fetches only routes this server has   /api/analytics/summary
ok   analytics-realtime.js fetches only routes this server has   /api/analytics/summary, /api/analytics/timeseries
ok   analytics-retention.js fetches only routes this server has   /api/analytics/retention, /api/analytics/videos
ok   analytics-revenue.js fetches only routes this server has   /api/analytics/summary
ok   analytics-shorts.js fetches only routes this server has   /api/analytics/videos
ok   analytics-table.js fetches only routes this server has   /api/analytics/videos
ok   analytics-traffic.js fetches only routes this server has   /api/analytics/traffic
ok   analytics-trends.js fetches only routes this server has   /api/trends/saved, /api/trends/searches, /api/trends/videos
ok   no Insights file hard-codes an origin   all paths are relative

All checks passed. 80 ok
```

`python tests/test_feat_files.py` still passes: `{"files": 37, "checks": 302}` and
`All checks passed.`

`python tests/test_menu_pages.py` still passes: `All checks passed. 142 ok`

I also ran the new test from a different working directory (`cd /tmp` with an absolute path)
and it passed the same way, because every path is built from the test file's own location.

## Proving the test can fail

A test that always passes is worse than no test, so I copied the tree to a throwaway folder
and broke one thing at a time. Nothing under `peakcut/` was touched.

| What I broke | What the test said |
|---|---|
| a file with a syntax error | `FAIL analytics-wrecked.js parses`, plus the missing plug-in lines |
| a fetch of a route that does not exist | `FAIL analytics-ghost.js fetches only routes this server has   missing: /api/analytics/ghost` |
| a plug-in registered under another file's name | `FAIL analytics-help.js is named after itself   'analytics-helper' is not the file name 'analytics-help'` |
| an absolute `http://127.0.0.1` origin | `FAIL no Insights file hard-codes an origin   analytics-origin.js` |
| the `trends` tab deleted from the shell | `FAIL the Trends tab exists   tabs are: overview, content, audience, traffic` |
| the page path changed to `insights` | `FAIL the Insights page keeps the analytics address   insights` |
| the whole page registration deleted | `FAIL the Insights page is registered   no PeakCut.page("analytics")` |

Each run exited 1. With the tree restored it exits 0.

## Two defects of my own that the first run exposed

I am writing these down because both were silent, and both would have made the test lie about
a passing folder.

1. **A passing line printed a failure message.** `check()` prints its detail on both pass and
   fail, and I passed the detail `"'x' != 'x'"` unconditionally. Every pass in the run printed
   a comparison that looked like a mismatch. Fixed by computing the detail only when the check
   fails.
2. **Reported "asks the server for nothing" for files that do fetch.** My first reader for a
   request path required the closing quote to come straight after the route, so a literal
   carrying its own query string, such as `"/api/analytics/summary?days=7"`, was not seen at
   all. Five files, among them `analytics-trends.js`, were described as asking for nothing
   while they in fact ask for three routes. Fixed by letting the path run to the closing quote
   and dropping the query before the comparison, which is how a route is matched anyway. The
   route table then grew from four fetches to nine, and the Trends plug-in went from "nothing"
   to `/api/trends/saved, /api/trends/searches, /api/trends/videos`.

That second defect matters beyond this file: "no fetch found" reads like a clean result, and
the only reason I caught it was that I knew those files send requests.

## One thing worth knowing about the route matcher

A route written with a placeholder, such as `/api/clips/{cid}`, is matched against one URL
segment, because `re.escape` turns the braces into `\{cid\}` and the pattern accounts for
that. I checked all four cases directly: one segment matches, two segments do not, an exact
route matches, and a near miss does not. No Insights plug-in asks for a placeholder route
today; it is there so the check keeps working when one does.

## Not done, and why

- I did not add the test to `tests/run.py`. That file is not mine to edit, and its own list of
  runs is how the full suite is assembled. Someone holding `tests/run.py` should add one line
  next to the existing feature-file checks:

  ```python
  ("the Insights page and its plug-ins: parse, one name each, real routes", ["tests/test_insights_pages.py"]),
  ```

  The test needs no server, so it can sit beside `tests/test_feat_files.py` and
  `tests/test_menu_pages.py`.
- I did not run `python tests/run.py`, the whole suite. It starts a server and an empty data
  folder, and sixteen other agents are writing into this tree at the same time; a failure
  there would as likely be another agent's half-saved file as mine. The three gates my brief
  named are all green.

## Skill loaded

`python-testing`. It is written for pytest, which this task forbids, so I took its point about
proving a test fails before trusting it and used the house style for everything else.
