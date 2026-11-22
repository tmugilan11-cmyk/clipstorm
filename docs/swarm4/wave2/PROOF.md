# Wave 2 proof

Ran on 2026-11-20 06:28:59 from `peakcut/`, against `http://127.0.0.1:8798`.

Nothing in this file was retyped. Each block is the file the command wrote, printed back
unchanged, so the text below is what the command actually printed.

The server was **already running** when this pass started, so it was not restarted, and it was
not stopped at the end either. Port 8798 was in use before the first command and is still in use
after the last one. The process is python, PID 29352, started 05:48:18.

## Result of each gate

| # | Command | Result |
|---|---|---|
| 1 | `python tests/test_feat_files.py` | PASS |
| 2 | `python tests/test_menu_pages.py` | PASS |
| 3 | `python tests/test_insights_pages.py` | PASS |
| 4 | `python tests/test_trends_api.py` | PASS |
| 5 | `python tests/test_analytics_api.py` | PASS |
| 6 | `python -c "import studio.server"` | PASS |
| 7 | `node --check` on every `web/feat/*.js` (38 files) | PASS |
| 8 | `curl -s http://127.0.0.1:8798/healthz` | PASS |
| 9 | `curl` of each `/api/analytics/*` and `/api/trends/*` route (13 routes) | PASS |
| 10 | `curl` of the two write routes on `/api/trends/saved` | PASS |

Two things were not PASS in the literal sense, and both are correct behaviour rather than a fault.
They are called out where they appear: `GET /api/analytics/retention` answers 400 twice on purpose,
because it needs a video id and a connected channel. A 400 with a sentence is that route working.

## 1. `python tests/test_feat_files.py`  PASS

Exit code 0. 302 checks over 37 feature files.

```
ok   plugins.js is there
ok   plugins.js parses
ok   index.html loads the loader
ok   index.html is otherwise untouched by features
ok   there is at least one feature file
ok   analytics-audience.js parses
ok   analytics-audience.js declares one plug-in
ok   analytics-audience.js is named after itself
ok   analytics-audience.js is the only owner of analytics-audience
ok   analytics-audience.js does not write into index.html
ok   analytics-audience.js escapes what it draws
ok   analytics-audience.js uses no absolute origin
ok   analytics-audience.js invents no clashing id
ok   analytics-charts.js parses
ok   analytics-charts.js declares one plug-in
ok   analytics-charts.js is named after itself
ok   analytics-charts.js is the only owner of analytics-charts
ok   analytics-charts.js does not write into index.html
ok   analytics-charts.js escapes what it draws
ok   analytics-charts.js uses no absolute origin
ok   analytics-charts.js invents no clashing id
ok   analytics-compare.js parses
ok   analytics-compare.js declares one plug-in
ok   analytics-compare.js is named after itself
ok   analytics-compare.js is the only owner of analytics-compare
ok   analytics-compare.js does not write into index.html
ok   analytics-compare.js escapes what it draws
ok   analytics-compare.js uses no absolute origin
ok   analytics-compare.js invents no clashing id
ok   analytics-empty.js parses
ok   analytics-empty.js declares one plug-in
ok   analytics-empty.js is named after itself
ok   analytics-empty.js is the only owner of analytics-empty
ok   analytics-empty.js does not write into index.html
ok   analytics-empty.js draws only fixed markup
ok   analytics-empty.js uses no absolute origin
ok   analytics-empty.js invents no clashing id
ok   analytics-export.js parses
ok   analytics-export.js declares one plug-in
ok   analytics-export.js is named after itself
ok   analytics-export.js is the only owner of analytics-export
ok   analytics-export.js does not write into index.html
ok   analytics-export.js escapes what it draws
ok   analytics-export.js uses no absolute origin
ok   analytics-export.js invents no clashing id
ok   analytics-help.js parses
ok   analytics-help.js declares one plug-in
ok   analytics-help.js is named after itself
ok   analytics-help.js is the only owner of analytics-help
ok   analytics-help.js does not write into index.html
ok   analytics-help.js draws no markup
ok   analytics-help.js uses no absolute origin
ok   analytics-help.js invents no clashing id
ok   analytics-kpi.js parses
ok   analytics-kpi.js declares one plug-in
ok   analytics-kpi.js is named after itself
ok   analytics-kpi.js is the only owner of analytics-kpi
ok   analytics-kpi.js does not write into index.html
ok   analytics-kpi.js draws only fixed markup
ok   analytics-kpi.js uses no absolute origin
ok   analytics-kpi.js invents no clashing id
ok   analytics-realtime.js parses
ok   analytics-realtime.js declares one plug-in
ok   analytics-realtime.js is named after itself
ok   analytics-realtime.js is the only owner of analytics-realtime
ok   analytics-realtime.js does not write into index.html
ok   analytics-realtime.js draws only fixed markup
ok   analytics-realtime.js uses no absolute origin
ok   analytics-realtime.js invents no clashing id
ok   analytics-retention.js parses
ok   analytics-retention.js declares one plug-in
ok   analytics-retention.js is named after itself
ok   analytics-retention.js is the only owner of analytics-retention
ok   analytics-retention.js does not write into index.html
ok   analytics-retention.js escapes what it draws
ok   analytics-retention.js uses no absolute origin
ok   analytics-retention.js invents no clashing id
ok   analytics-revenue.js parses
ok   analytics-revenue.js declares one plug-in
ok   analytics-revenue.js is named after itself
ok   analytics-revenue.js is the only owner of analytics-revenue
ok   analytics-revenue.js does not write into index.html
ok   analytics-revenue.js draws only fixed markup
ok   analytics-revenue.js uses no absolute origin
ok   analytics-revenue.js invents no clashing id
ok   analytics-shorts.js parses
ok   analytics-shorts.js declares one plug-in
ok   analytics-shorts.js is named after itself
ok   analytics-shorts.js is the only owner of analytics-shorts
ok   analytics-shorts.js does not write into index.html
ok   analytics-shorts.js draws only fixed markup
ok   analytics-shorts.js uses no absolute origin
ok   analytics-shorts.js invents no clashing id
ok   analytics-table.js parses
ok   analytics-table.js declares one plug-in
ok   analytics-table.js is named after itself
ok   analytics-table.js is the only owner of analytics-table
ok   analytics-table.js does not write into index.html
ok   analytics-table.js escapes what it draws
ok   analytics-table.js uses no absolute origin
ok   analytics-table.js invents no clashing id
ok   analytics-traffic.js parses
ok   analytics-traffic.js declares one plug-in
ok   analytics-traffic.js is named after itself
ok   analytics-traffic.js is the only owner of analytics-traffic
ok   analytics-traffic.js does not write into index.html
ok   analytics-traffic.js draws only fixed markup
ok   analytics-traffic.js uses no absolute origin
ok   analytics-traffic.js invents no clashing id
ok   analytics-trends.js parses
ok   analytics-trends.js declares one plug-in
ok   analytics-trends.js is named after itself
ok   analytics-trends.js is the only owner of analytics-trends
ok   analytics-trends.js does not write into index.html
ok   analytics-trends.js draws only fixed markup
ok   analytics-trends.js uses no absolute origin
ok   analytics-trends.js invents no clashing id
ok   analytics.js parses
ok   analytics.js declares one plug-in
ok   analytics.js is named after itself
ok   analytics.js is the only owner of analytics
ok   analytics.js does not write into index.html
ok   analytics.js draws only fixed markup
ok   analytics.js uses no absolute origin
ok   analytics.js invents no clashing id
ok   autopilot.js parses
ok   autopilot.js declares one plug-in
ok   autopilot.js is named after itself
ok   autopilot.js is the only owner of autopilot
ok   autopilot.js does not write into index.html
ok   autopilot.js escapes what it draws
ok   autopilot.js uses no absolute origin
ok   autopilot.js invents no clashing id
ok   day.js parses
ok   day.js declares one plug-in
ok   day.js is named after itself
ok   day.js is the only owner of day
ok   day.js does not write into index.html
ok   day.js draws only fixed markup
ok   day.js uses no absolute origin
ok   day.js invents no clashing id
ok   filters.js parses
ok   filters.js declares one plug-in
ok   filters.js is named after itself
ok   filters.js is the only owner of filters
ok   filters.js does not write into index.html
ok   filters.js draws only fixed markup
ok   filters.js uses no absolute origin
ok   filters.js invents no clashing id
ok   grid.js parses
ok   grid.js declares one plug-in
ok   grid.js is named after itself
ok   grid.js is the only owner of grid
ok   grid.js does not write into index.html
ok   grid.js draws only fixed markup
ok   grid.js uses no absolute origin
ok   grid.js invents no clashing id
ok   heard.js parses
ok   heard.js declares one plug-in
ok   heard.js is named after itself
ok   heard.js is the only owner of heard
ok   heard.js does not write into index.html
ok   heard.js draws only fixed markup
ok   heard.js uses no absolute origin
ok   heard.js invents no clashing id
ok   history.js parses
ok   history.js declares one plug-in
ok   history.js is named after itself
ok   history.js is the only owner of history
ok   history.js does not write into index.html
ok   history.js draws only fixed markup
ok   history.js uses no absolute origin
ok   history.js invents no clashing id
ok   keys.js parses
ok   keys.js declares one plug-in
ok   keys.js is named after itself
ok   keys.js is the only owner of keys
ok   keys.js does not write into index.html
ok   keys.js draws only fixed markup
ok   keys.js uses no absolute origin
ok   keys.js invents no clashing id
ok   learn.js parses
ok   learn.js declares one plug-in
ok   learn.js is named after itself
ok   learn.js is the only owner of learn
ok   learn.js does not write into index.html
ok   learn.js draws only fixed markup
ok   learn.js uses no absolute origin
ok   learn.js invents no clashing id
ok   log.js parses
ok   log.js declares one plug-in
ok   log.js is named after itself
ok   log.js is the only owner of log
ok   log.js does not write into index.html
ok   log.js escapes what it draws
ok   log.js uses no absolute origin
ok   log.js invents no clashing id
ok   menu-icons.js parses
ok   menu-icons.js declares one plug-in
ok   menu-icons.js is named after itself
ok   menu-icons.js is the only owner of menu-icons
ok   menu-icons.js does not write into index.html
ok   menu-icons.js draws no markup
ok   menu-icons.js uses no absolute origin
ok   menu-icons.js invents no clashing id
ok   menu-pages.js parses
ok   menu-pages.js declares one plug-in
ok   menu-pages.js is named after itself
ok   menu-pages.js is the only owner of menu-pages
ok   menu-pages.js does not write into index.html
ok   menu-pages.js escapes what it draws
ok   menu-pages.js uses no absolute origin
ok   menu-pages.js invents no clashing id
ok   menu.js parses
ok   menu.js declares one plug-in
ok   menu.js is named after itself
ok   menu.js is the only owner of menu
ok   menu.js does not write into index.html
ok   menu.js draws no markup
ok   menu.js uses no absolute origin
ok   menu.js invents no clashing id
ok   mood.js parses
ok   mood.js declares one plug-in
ok   mood.js is named after itself
ok   mood.js is the only owner of mood
ok   mood.js does not write into index.html
ok   mood.js draws only fixed markup
ok   mood.js uses no absolute origin
ok   mood.js invents no clashing id
ok   nav-responsive.js parses
ok   nav-responsive.js declares one plug-in
ok   nav-responsive.js is named after itself
ok   nav-responsive.js is the only owner of nav-responsive
ok   nav-responsive.js does not write into index.html
ok   nav-responsive.js draws no markup
ok   nav-responsive.js uses no absolute origin
ok   nav-responsive.js invents no clashing id
ok   nav-search.js parses
ok   nav-search.js declares one plug-in
ok   nav-search.js is named after itself
ok   nav-search.js is the only owner of nav-search
ok   nav-search.js does not write into index.html
ok   nav-search.js draws only fixed markup
ok   nav-search.js uses no absolute origin
ok   nav-search.js invents no clashing id
ok   page-guard.js parses
ok   page-guard.js declares one plug-in
ok   page-guard.js is named after itself
ok   page-guard.js is the only owner of page-guard
ok   page-guard.js does not write into index.html
ok   page-guard.js draws no markup
ok   page-guard.js uses no absolute origin
ok   page-guard.js invents no clashing id
ok   peek.js parses
ok   peek.js declares one plug-in
ok   peek.js is named after itself
ok   peek.js is the only owner of peek
ok   peek.js does not write into index.html
ok   peek.js draws only fixed markup
ok   peek.js uses no absolute origin
ok   peek.js invents no clashing id
ok   pill.js parses
ok   pill.js declares one plug-in
ok   pill.js is named after itself
ok   pill.js is the only owner of pill
ok   pill.js does not write into index.html
ok   pill.js draws only fixed markup
ok   pill.js uses no absolute origin
ok   pill.js invents no clashing id
ok   settings-explain.js parses
ok   settings-explain.js declares one plug-in
ok   settings-explain.js is named after itself
ok   settings-explain.js is the only owner of settings-explain
ok   settings-explain.js does not write into index.html
ok   settings-explain.js draws no markup
ok   settings-explain.js uses no absolute origin
ok   settings-explain.js invents no clashing id
ok   stage.js parses
ok   stage.js declares one plug-in
ok   stage.js is named after itself
ok   stage.js is the only owner of stage
ok   stage.js does not write into index.html
ok   stage.js draws only fixed markup
ok   stage.js uses no absolute origin
ok   stage.js invents no clashing id
ok   stats.js parses
ok   stats.js declares one plug-in
ok   stats.js is named after itself
ok   stats.js is the only owner of stats
ok   stats.js does not write into index.html
ok   stats.js draws only fixed markup
ok   stats.js uses no absolute origin
ok   stats.js invents no clashing id
ok   style-tiles.js parses
ok   style-tiles.js declares one plug-in
ok   style-tiles.js is named after itself
ok   style-tiles.js is the only owner of style-tiles
ok   style-tiles.js does not write into index.html
ok   style-tiles.js draws only fixed markup
ok   style-tiles.js uses no absolute origin
ok   style-tiles.js invents no clashing id
ok   loader keeps the documented folder
{"files": 37, "checks": 302}
All checks passed.
```

## 2. `python tests/test_menu_pages.py`  PASS

Exit code 0.

```
ok   there is at least one feature file   37 files
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
ok   analytics.js parses
ok   autopilot.js parses
ok   day.js parses
ok   filters.js parses
ok   grid.js parses
ok   heard.js parses
ok   history.js parses
ok   keys.js parses
ok   learn.js parses
ok   log.js parses
ok   menu-icons.js parses
ok   menu-pages.js parses
ok   menu.js parses
ok   mood.js parses
ok   nav-responsive.js parses
ok   nav-search.js parses
ok   page-guard.js parses
ok   peek.js parses
ok   pill.js parses
ok   settings-explain.js parses
ok   stage.js parses
ok   stats.js parses
ok   style-tiles.js parses
ok   at least one page is registered   9 pages
ok   analytics says what to call it
ok   analytics says where it lives
ok   analytics has a one-line tip
ok   analytics has a group
ok   analytics has an icon the page knows   chart
ok   improve says what to call it
ok   improve says where it lives
ok   improve has a one-line tip
ok   improve has a group
ok   improve has an icon the page knows   bolt
ok   brand says what to call it
ok   brand says where it lives
ok   brand has a one-line tip
ok   brand has a group
ok   brand has an icon the page knows   palette
ok   transcribe says what to call it
ok   transcribe says where it lives
ok   transcribe has a one-line tip
ok   transcribe has a group
ok   transcribe has an icon the page knows   microphone
ok   tools says what to call it
ok   tools says where it lives
ok   tools has a one-line tip
ok   tools has a group
ok   tools has an icon the page knows   wand
ok   apps says what to call it
ok   apps says where it lives
ok   apps has a one-line tip
ok   apps has a group
ok   apps has an icon the page knows   plug
ok   ai says what to call it
ok   ai says where it lives
ok   ai has a one-line tip
ok   ai has a group
ok   ai has an icon the page knows   bolt
ok   storage says what to call it
ok   storage says where it lives
ok   storage has a one-line tip
ok   storage has a group
ok   storage has an icon the page knows   folder
ok   account says what to call it
ok   account says where it lives
ok   account has a one-line tip
ok   account has a group
ok   account has an icon the page knows   user
ok   no two pages share an address
ok   no two pages share a name
ok   analytics does not take a built-in address   analytics
ok   improve does not take a built-in address   improve
ok   brand does not take a built-in address   brand
ok   transcribe does not take a built-in address   transcribe
ok   tools does not take a built-in address   tools
ok   apps does not take a built-in address   apps
ok   ai does not take a built-in address   ai
ok   storage does not take a built-in address   storage
ok   account does not take a built-in address   account
ok   analytics sits under a known heading   Understand
ok   improve sits under a known heading   Make
ok   brand sits under a known heading   Make
ok   transcribe sits under a known heading   Understand
ok   tools sits under a known heading   Set up
ok   apps sits under a known heading   Set up
ok   ai sits under a known heading   Set up
ok   storage sits under a known heading   Set up
ok   account sits under a known heading   Set up
ok   analytics does not shadow a feature file   analytics
ok   improve does not shadow a feature file   improve
ok   brand does not shadow a feature file   brand
ok   transcribe does not shadow a feature file   transcribe
ok   tools does not shadow a feature file   tools
ok   apps does not shadow a feature file   apps
ok   ai does not shadow a feature file   ai
ok   storage does not shadow a feature file   storage
ok   account does not shadow a feature file   account
ok   brand is a page
ok   brand has a tip long enough to say something
ok   transcribe is a page
ok   transcribe has a tip long enough to say something
ok   tools is a page
ok   tools has a tip long enough to say something
ok   apps is a page
ok   apps has a tip long enough to say something
ok   analytics has a label a menu row fits
ok   improve has a label a menu row fits
ok   brand has a label a menu row fits
ok   transcribe has a label a menu row fits
ok   tools has a label a menu row fits
ok   apps has a label a menu row fits
ok   ai has a label a menu row fits
ok   storage has a label a menu row fits
ok   account has a label a menu row fits
ok   analytics has a label of its own
ok   improve has a label of its own
ok   brand has a label of its own
ok   transcribe has a label of its own
ok   tools has a label of its own
ok   apps has a label of its own
ok   ai has a label of its own
ok   storage has a label of its own
ok   account has a label of its own
ok   analytics.js draws its page
ok   learn.js draws its page
ok   menu-pages.js draws its page

All checks passed. 142 ok
```

## 3. `python tests/test_insights_pages.py`  PASS

Exit code 0.

```
ok   studio files say what routes they answer   134 routes
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
ok   analytics-charts.js declares one plug-in   found ['analytics-charts']
ok   analytics-charts.js is named after itself
ok   analytics-charts.js is the only owner of its name
ok   analytics-compare.js declares one plug-in   found ['analytics-compare']
ok   analytics-compare.js is named after itself
ok   analytics-compare.js is the only owner of its name
ok   analytics-empty.js declares one plug-in   found ['analytics-empty']
ok   analytics-empty.js is named after itself
ok   analytics-empty.js is the only owner of its name
ok   analytics-export.js declares one plug-in   found ['analytics-export']
ok   analytics-export.js is named after itself
ok   analytics-export.js is the only owner of its name
ok   analytics-help.js declares one plug-in   found ['analytics-help']
ok   analytics-help.js is named after itself
ok   analytics-help.js is the only owner of its name
ok   analytics-kpi.js declares one plug-in   found ['analytics-kpi']
ok   analytics-kpi.js is named after itself
ok   analytics-kpi.js is the only owner of its name
ok   analytics-realtime.js declares one plug-in   found ['analytics-realtime']
ok   analytics-realtime.js is named after itself
ok   analytics-realtime.js is the only owner of its name
ok   analytics-retention.js declares one plug-in   found ['analytics-retention']
ok   analytics-retention.js is named after itself
ok   analytics-retention.js is the only owner of its name
ok   analytics-revenue.js declares one plug-in   found ['analytics-revenue']
ok   analytics-revenue.js is named after itself
ok   analytics-revenue.js is the only owner of its name
ok   analytics-shorts.js declares one plug-in   found ['analytics-shorts']
ok   analytics-shorts.js is named after itself
ok   analytics-shorts.js is the only owner of its name
ok   analytics-table.js declares one plug-in   found ['analytics-table']
ok   analytics-table.js is named after itself
ok   analytics-table.js is the only owner of its name
ok   analytics-traffic.js declares one plug-in   found ['analytics-traffic']
ok   analytics-traffic.js is named after itself
ok   analytics-traffic.js is the only owner of its name
ok   analytics-trends.js declares one plug-in   found ['analytics-trends']
ok   analytics-trends.js is named after itself
ok   analytics-trends.js is the only owner of its name
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

## 4. `python tests/test_trends_api.py`  PASS

Exit code 0.

```
ok   test_every_route_answers
ok   test_no_connection_is_an_empty_list_and_a_note
ok   test_a_saved_term_comes_back
ok   test_a_blank_term_is_refused
ok   test_a_saved_term_can_be_deleted
ok   test_a_junk_trends_file_still_answers
ok   test_a_range_past_the_cap_is_refused
ok   test_google_refusing_a_connected_account_is_not_a_500

All checks passed. 8 ok
```

## 5. `python tests/test_analytics_api.py`  PASS

Exit code 0.

```
ok   the status route answers   200
ok   the status route says where the numbers came from
ok   with nothing connected it says so in a sentence   No YouTube account is connected, so these are PeakCut's own numbers: clips made, posts sent, and the views PeakCut already tracks. Connect a channel under Connected apps to see YouTube's own analytics.
ok   it offers the real date ranges
ok   the summary answers with no connection   200
ok   the summary has cards   list
ok   every card has a key, a label, a value and a unit   {'key': 'clips', 'label': 'Clips made', 'value': 0, 'unit': 'clips'}
ok   the summary names its dates
ok   it says which source it used   peakcut
ok   the timeseries answers with no connection   200
ok   the timeseries has one point per day   14
ok   every point is a day and a number
ok   an unknown metric is refused, not guessed   400
ok   ...and the refusal lists the real ones   PeakCut does not know that metric. Ask for one of: average_view_duration, average_view_percentage, comments, likes, shares, subscribers, views, watch_time.
ok   /api/analytics/videos answers with no connection   200
ok   /api/analytics/videos carries a list under rows   list
ok   /api/analytics/audience answers with no connection   200
ok   /api/analytics/audience carries a list under countries   list
ok   /api/analytics/traffic answers with no connection   200
ok   /api/analytics/traffic carries a list under sources   list
ok   retention refuses a link it cannot read   400
ok   an empty token is the no-connection path, not an error   200
ok   a refused token answers 400, not 500   400
ok   /api/analytics/status is reachable on the real app   200
ok   /api/analytics/summary is reachable on the real app   200
ok   /api/analytics/timeseries is reachable on the real app   200
ok   /api/analytics/videos is reachable on the real app   200
ok   /api/analytics/audience is reachable on the real app   200
ok   /api/analytics/traffic is reachable on the real app   200

All checks passed. 29 ok
```

## 6. `python -c "import studio.server"`  PASS

Exit code 0, and it printed nothing, which is what a clean import does.

```

(no output above this line was printed by the command)
```

## 7. `node --check` on every `web/feat/*.js`  PASS

38 files, 0 failed, exit code 0.

```
=== node --check on every web/feat/*.js ===
ok   node --check web/feat/_example.js
ok   node --check web/feat/analytics-audience.js
ok   node --check web/feat/analytics-charts.js
ok   node --check web/feat/analytics-compare.js
ok   node --check web/feat/analytics-empty.js
ok   node --check web/feat/analytics-export.js
ok   node --check web/feat/analytics-help.js
ok   node --check web/feat/analytics-kpi.js
ok   node --check web/feat/analytics-realtime.js
ok   node --check web/feat/analytics-retention.js
ok   node --check web/feat/analytics-revenue.js
ok   node --check web/feat/analytics-shorts.js
ok   node --check web/feat/analytics-table.js
ok   node --check web/feat/analytics-traffic.js
ok   node --check web/feat/analytics-trends.js
ok   node --check web/feat/analytics.js
ok   node --check web/feat/autopilot.js
ok   node --check web/feat/day.js
ok   node --check web/feat/filters.js
ok   node --check web/feat/grid.js
ok   node --check web/feat/heard.js
ok   node --check web/feat/history.js
ok   node --check web/feat/keys.js
ok   node --check web/feat/learn.js
ok   node --check web/feat/log.js
ok   node --check web/feat/menu-icons.js
ok   node --check web/feat/menu-pages.js
ok   node --check web/feat/menu.js
ok   node --check web/feat/mood.js
ok   node --check web/feat/nav-responsive.js
ok   node --check web/feat/nav-search.js
ok   node --check web/feat/page-guard.js
ok   node --check web/feat/peek.js
ok   node --check web/feat/pill.js
ok   node --check web/feat/settings-explain.js
ok   node --check web/feat/stage.js
ok   node --check web/feat/stats.js
ok   node --check web/feat/style-tiles.js

checked 38 files, 0 failed
```

## 8 and 9. `curl` of `/healthz` and of every analytics and trends route  PASS

What each route answers is below. Rows that say 400 are the retention guard, explained under the block.

The routes were run by `.pctest/proof2/prove.sh`, which is in the workspace if someone wants to
run the same list again. Every route that `studio/api_analytics.py` and `studio/api_trends.py`
declare is in this list; there are 13 of them and all 13 appear.

```
=== healthz ===
GET /healthz  -> {"ok":true}  [http 200]

=== analytics routes ===
/api/analytics/status                          200  {"connected":false,"source":"peakcut","scope":false,"ranges":{"7":"Last 7 days","28":"Last 28 days","90":"Last 90 days","365":"Last 365 days","0":"Lif
/api/analytics/summary                         200  {"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20","cards":[{"key":"clips","label":"Clips made","value":3,"unit":"clips"},{"key":"p
/api/analytics/summary?days=7                  200  {"source":"peakcut","days":7,"start":"2026-11-14","end":"2026-11-20","cards":[{"key":"clips","label":"Clips made","value":3,"unit":"clips"},{"key":"po
/api/analytics/summary?days=90                 200  {"source":"peakcut","days":90,"start":"2026-08-23","end":"2026-11-20","cards":[{"key":"clips","label":"Clips made","value":3,"unit":"clips"},{"key":"p
/api/analytics/summary?days=365                200  {"source":"peakcut","days":365,"start":"2025-11-21","end":"2026-11-20","cards":[{"key":"clips","label":"Clips made","value":3,"unit":"clips"},{"key":"
/api/analytics/summary?days=0                  200  {"source":"peakcut","days":0,"start":"2016-11-23","end":"2026-11-20","cards":[{"key":"clips","label":"Clips made","value":3,"unit":"clips"},{"key":"po
/api/analytics/timeseries                      200  {"source":"peakcut","metric":"views","days":28,"start":"2026-10-24","end":"2026-11-20","rows":[{"day":"2026-11-07","value":0},{"day":"2026-11-08","val
/api/analytics/timeseries?metric=watch_time    200  {"source":"peakcut","metric":"watch_time","days":28,"start":"2026-10-24","end":"2026-11-20","rows":[{"day":"2026-11-07","value":0},{"day":"2026-11-08"
/api/analytics/videos                          200  {"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20","rows":[],"total":0,"note":"PeakCut's own posts. Watch time and the rest come fr
/api/analytics/videos?days=90                  200  {"source":"peakcut","days":90,"start":"2026-08-23","end":"2026-11-20","rows":[],"total":0,"note":"PeakCut's own posts. Watch time and the rest come fr
/api/analytics/audience                        200  {"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20","returning":null,"countries":[],"hours":[],"note":"Viewer types, countries and h
/api/analytics/traffic                         200  {"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20","sources":[],"note":"Traffic sources come from YouTube. Connect a channel to see
/api/analytics/retention                       400  {"detail":"Paste a YouTube link or a video id."}
/api/analytics/retention?video=dQw4w9WgXcQ     400  {"detail":"Retention comes from YouTube. Connect a channel under Connected apps."}

=== trends routes ===
/api/trends/status                             200  {"connected":false,"note":"No YouTube account is connected, so PeakCut cannot read what people typed to find your videos. Connect a channel under Conn
/api/trends/searches                           200  {"rows":[],"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20","note":"No YouTube account is connected, so PeakCut cannot read what p
/api/trends/searches?days=7                    200  {"rows":[],"source":"peakcut","days":7,"start":"2026-11-14","end":"2026-11-20","note":"No YouTube account is connected, so PeakCut cannot read what pe
/api/trends/searches?days=90                   200  {"rows":[],"source":"peakcut","days":90,"start":"2026-08-23","end":"2026-11-20","note":"No YouTube account is connected, so PeakCut cannot read what p
/api/trends/videos                             200  {"rows":[],"days":28,"start":"2026-10-24","end":"2026-11-20","note":"No YouTube account is connected, so PeakCut cannot read which videos gained views
/api/trends/saved                              200  {"terms":[]}

=== bounds a page passes on purpose ===
/api/analytics/summary?days=9999               422  {"detail":[{"type":"less_than_equal","loc":["query","days"],"msg":"Input should be less than or equal to 3650","input":"9999","ctx":{"le":3650}}]}
/api/trends/videos?days=9999                   422  {"detail":[{"type":"less_than_equal","loc":["query","days"],"msg":"Input should be less than or equal to 3650","input":"9999","ctx":{"le":3650}}]}

=== trends saved: the two write routes (adds a term, then removes it) ===
POST   /api/trends/saved {"term":"proof term"}  -> {"terms":["proof term"]}  [http 200]
GET    /api/trends/saved                        -> {"terms":["proof term"]}  [http 200]
DELETE /api/trends/saved?term=proof term        -> {"terms":[]}  [http 200]
GET    /api/trends/saved                        -> {"terms":[]}  [http 200]
POST   /api/trends/saved {"term":"  "} a blank  -> {"detail":"Type a search term first, then save it."}  [http 400]

=== served feature files ===
GET /assets/feat -> 37 files: analytics-audience.js, analytics-charts.js, analytics-compare.js, analytics-empty.js ...
```

## What the two 400s mean

`GET /api/analytics/retention` is the one route that cannot answer without an argument.

- Called with no `video`, it answers 400 with `{"detail":"Paste a YouTube link or a video id."}`.
  That is the route refusing an empty request with a sentence a person can act on.
- Called with a video id but no channel connected, it answers 400 with
  `{"detail":"Retention comes from YouTube. Connect a channel under Connected apps."}`.

Both are deliberate guards in `studio/api_analytics.py`, not crashes. `tests/test_analytics_api.py`
covers them and passed. So the route is recorded as working.

The 422s are the same story for the date range: `days=9999` is above the cap of 3650, and the
route says so instead of quietly serving a different range.

## The two write routes

`POST` and `DELETE` on `/api/trends/saved` were run against the real data folder. The file they
write is `data/users/u_local/trends.json`. It held `{"terms": []}` before the pass. It was backed
up first, the pass added one term and removed it again, and the file was then compared with the
backup. This is the comparison, printed as the shell wrote it:

```
$ diff .pctest/proof2/trends.backup.json data/users/u_local/trends.json
[diff exit=0]
```

A diff that prints nothing but that exit line means the two files are the same. So the file is
byte for byte what it was before, and nothing was left behind.

## The page itself

The page was loaded in a browser at `/app/analytics` to check that the files are not only valid
JavaScript but actually run.

- `window.PeakCut._order` listed all 37 features, including every `analytics-*` file.
- The Overview, Content, Audience, Trends and Traffic tabs each drew text; each is a real tab with
  role="tab" and each rendered content after being clicked.
- Changing the range select from 28 to 7 redrew the page and it read
  `Showing 14 Nov 2026 to 20 Nov 2026. The page is set to Last 7 days.`
- The Trends tab called `/api/trends/searches`, `/api/trends/videos` and `/api/trends/saved`, and
  every one of those fetches came back 200.
- The console stayed empty through all of that. No script error, no warning.

With no channel connected the page says so in words on each card rather than showing a zero, which
is the rule in the contract: a number it did not receive is shown as a dash with a sentence.

## What could not be done

- The retention curve could not be seen with real points, because that needs a YouTube account
  connected. The route's guard was proved instead, which is all this machine can prove.
- Every analytics number on this machine is PeakCut's own, because no channel is connected. The
  YouTube figures were not exercised beyond their refusal paths.

