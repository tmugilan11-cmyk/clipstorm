# analytics-shell

**What I built.** The Analytics page frame in `web/feat/analytics.js`. It registers `PeakCut.page("analytics", { nav: "Analytics", icon: "chart", tip: "Views, watch time and what people did with each video", path: "analytics", group: "Understand", order: 20 })`, so Analytics is a row of its own in the left menu under Understand, not a tab inside Settings.

The page draws its whole frame before any request goes out. The title row shows the channel name, a "Last updated" line, and one plain sentence naming the dates on screen ("Last 28 days, ending 20 Nov 2026", plus ", compared with the 28 days before" when compare is on). Under it are four tab buttons, Overview, Content, Audience and Traffic, each with an icon. Under those is a date range select with the real YouTube ranges (Last 7 days, Last 28 days, Last 90 days, Last 365 days, Lifetime) and a compare-to switch. Lifetime turns the switch off and the note says "Off for Lifetime", because there is no earlier period to compare a lifetime against.

Four mount points stay in the page at all times with fixed ids: `#an_kpi` and `#an_charts` on Overview, `#an_table` on Content, `#an_body` on Audience and Traffic. A tab click only shows one panel and hides the rest. No page reload, no route change, no request from my file.

`window.PeakCutAnalytics` exposes `range()` (an object with ISO `start`, `end`, `days` and a `label`), `compare()` (the previous equal-length window, or null when off or Lifetime), `tab()`, `mount(id)` (returns the element for `an_kpi`, `an_charts`, `an_table` or `an_body`, else null) and `reload()`. It also publishes the same values as plain top level fields (`start`, `end`, `days`, `label`, `compare_start`, `compare_end`) because the charts and traffic files read the API as if it were a plain object. That way all five filling files read the same choice without any of them being edited.

After a tab, range or compare change the shell clears the affected boxes and calls the registered `load()` of every `analytics-` file, then fires `peakcut:render`, so the parts repaint for the new dates. A small watcher stamps the "Last updated" time when a box first gets content, and never before.

**File I own.** `web/feat/analytics.js`, 218 lines. I touched nothing else.

**Command and what it printed.**
- `node --check web/feat/analytics.js` printed `node ok`, and `wc -l` printed `218 web/feat/analytics.js`.
- `python tests/test_feat_files.py` printed `{"files": 28, "checks": 230}` and `All checks passed.` (exit 0). My rows all ok: parses, declares one plug-in, is named after itself, is the only owner of `analytics`, does not write into index.html, draws only fixed markup, uses no absolute origin, invents no clashing id.
- `python tests/test_menu_pages.py` printed `All checks passed. 103 ok` (exit 0). My rows include `ok analytics has an icon the page knows chart`, `ok analytics sits under a known heading Understand`, `ok analytics does not take a built-in address`, and `ok analytics.js draws its page`.
- In the live browser at `http://127.0.0.1:8798/app/analytics`, `go("analytics")` drew the header with channel "stream_sniper_369", "Last 28 days, ending 20 Nov 2026" and four tabs. `PeakCutAnalytics.range()` returned `{"start":"2026-10-24","end":"2026-11-20","days":28,"label":"Last 28 days"}`. Switching the select to Last 7 days returned `{"start":"2026-11-14","end":"2026-11-20","days":7,...}`. Lifetime returned `{"start":"2005-01-01","end":"2026-11-20","days":7994,"label":"Lifetime"}` with the compare switch disabled and the note "Off for Lifetime". All four mount points exist on every tab and exactly one panel is visible per tab.

**What I could not do.** No `/api/analytics/*` route existed while I worked, so the four boxes only ever showed their own empty and not-connected sentences. Wave 2 builds the routes and the filling files will use them. Two of the filling files read `window.PeakCutAnalytics.range` as if it were an object, not a function: `web/feat/analytics-traffic.js:58` and `web/feat/analytics-charts.js:64` both do `object(A.range) || A`, so the traffic tab shows the pill "Range not stated" even though the numbers it asks for are correct, because the fallback to the plain fields still works. `web/feat/analytics-kpi.js:90` calls the function properly. I published plain duplicate fields on the API object so this costs nothing but a label. The real fix is one line in each of those two files, and they are not mine to edit.

Skill loaded: frontend-design.
