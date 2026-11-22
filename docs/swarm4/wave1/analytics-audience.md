# analytics-audience

**Built.** `web/feat/analytics-audience.js` fills `#an_body` on the Audience tab with three blocks from one request to `/api/analytics/audience`: returning against new viewers as two bars with counts and percentages; where viewers are as up to eight country rows with a bar and a percentage; when viewers are on as a 7x24 hour by weekday grid in one hue and four steps, with a legend and a sentence naming the busiest slot. Each block has its own empty state and its own failure line, so one bad block cannot empty the page. The code never shows a number it did not receive and prints the range the server reported. Style follows the existing palette, no shadows, colour only on hover.

**File owned.** `web/feat/analytics-audience.js`, 238 lines. No other file touched. `web/index.html` untouched.

**Skill.** `frontend-design`.

**Commands and what they printed.**
- `node --check web/feat/analytics-audience.js` printed nothing, exit 0.
- `python tests/test_feat_files.py` printed `{"files": 25, "checks": 206}` then `All checks passed.`
- `python tests/test_menu_pages.py` printed `All checks passed. 82 ok`.

**Checked against the live server** at `http://127.0.0.1:8798`, not only syntax. The route exists now and answers `{"source":"peakcut","days":28,"start":"2026-10-23","end":"2026-11-19","returning":null,"countries":[],"hours":[],"note":"Viewer types, countries and hours come from YouTube. Connect a channel to see them."}`. That is the empty case, and the page shows the server note plus three empty states. A stand in harness outside the repo fed the file eight shapes: the empty answer, a full answer, a 7x24 matrix, a 24x7 matrix, a flat cell list, a rejected request, junk rows, and a broken row. All rendered. The broken row failed only its own block. The rejected request put a failure line in each block and kept all three sections. Two bugs were found and fixed this way: the range reader missed the flat `start`/`end` fields the route actually sends, and an array of rows was mistaken for the flat cell list, so both matrix shapes drew nothing.

**Two things worth telling the lead.**
- The route reads `days`, not `start` and `end`. `?days=7` answers 7 days; `?start=…&end=…` is ignored. This file asks with `days` taken from `window.PeakCutAnalytics.range`, so the numbers match the range on screen.
- `web/feat/analytics-traffic.js` writes the same `#an_body` box for the Traffic tab. This file now asks `window.PeakCutAnalytics.tab()` and paints only when the answer is `audience`, and paints nothing when no shell is present. If the shell belongs to another agent, it must expose `tab()` and `range` on `window.PeakCutAnalytics`, which `analytics-traffic.js` already assumes.

**Not done.** Nothing left in scope. The file was given `#an_body` and no page shell, so it also refreshes itself when the shell redraws and when the box appears later. The remaining gap is data: until a channel is connected the route sends empty lists, so on this machine all three blocks show their empty states by design.
