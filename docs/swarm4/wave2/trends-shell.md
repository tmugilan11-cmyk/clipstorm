# trends-shell

**What I built.** A fifth tab in the Insights shell, "Trends", sitting between Audience and Traffic.
It draws into `#an_body`, the same box Audience and Traffic use, so the plug-in `analytics-trends`
(another wave 2 slot) fills it through the same render event and needs no change from this file.

Three edits, nothing else in the file moved:

1. `TABS` (now `web/feat/analytics.js:22-24`) gained `{ k: "trends", l: "Trends", i: "chart", p: "body" }`
   as the fourth entry, after Audience and before Traffic. `chart` is one of the 58 icon names, so the
   tab button renders a real glyph through `icon()`, which calls the bare `ic`.
2. `hintFor()` (now `web/feat/analytics.js:74-76`) answers for `trends` with the sentence
   "How these numbers moved over the range on screen." That sentence is what the body panel shows
   above an empty box until a file fills it, so Trends never looks broken while it waits.
3. `switchTab()` (now `web/feat/analytics.js:176-184`) now treats `trends` like the other two body tabs:
   it deletes `#an_body`'s `data-aa` stamp and empties `innerHTML`, then falls through to `head()` and
   `ask()`. `ask()` is unchanged and is what fires `peakcut:render` and calls the `load()` of every
   `analytics-` plug-in. So the trends plug-in gets the same clear-then-render handshake Audience gets,
   and it cannot inherit the previous tab's markup or its "already drawn" stamp.

Ranges, the compare switch, `head()`, `paint()`, `watch()`, `ask()`, `reload()`, the page registration,
the `drawShell` hook and `agree()` are exactly as they were. No request goes out from this file, no
number is drawn here, and `#an_body` stays in the DOM on every tab so a plug-in can find it.

**Files.** `web/feat/analytics.js` only, now 220 lines (was 218: two lines added, three rewritten).
I wrote this report and touched nothing else. I did not create `analytics-trends.js`; that is the
`trends-cards` slot's file.

**What I ran, and what it printed.**

- `node --check web/feat/analytics.js` printed `node ok`; `wc -l` printed `220 web/feat/analytics.js`. Exit 0.
- `python tests/test_feat_files.py` printed `{"files": 28, "checks": 230}` and `All checks passed.`. Exit 0.
  My rows: `ok analytics.js parses`, `ok analytics.js declares one plug-in`, `ok analytics.js is named after
  itself`, `ok analytics.js is the only owner of analytics`, `ok analytics.js does not write into index.html`,
  `ok analytics.js draws only fixed markup`, `ok analytics.js uses no absolute origin`,
  `ok analytics.js invents no clashing id`.
- `python tests/test_menu_pages.py` printed `All checks passed. 133 ok`. Exit 0. My rows include
  `ok analytics has an icon the page knows   chart`, `ok analytics sits under a known heading   Understand`,
  `ok analytics does not shadow a feature file   analytics`, `ok analytics.js draws its page`.
- In the live page at `http://127.0.0.1:8798/app/analytics`, read back from the DOM:
  tabs in order `overview, content, audience, trends, traffic`; the Trends button carries the label
  `Trends` and no icon fallback fired. Clicking it from Audience emptied `#an_body` (a marker paragraph
  I planted beforehand was gone), dropped its `data-aa` stamp, showed the body panel, set
  `aria-selected="true"` on the button and `PeakCutAnalytics.tab()` answered `trends`, with exactly one
  `peakcut:render` event dispatched. Leaving and re-entering dispatched the event again and left the box
  empty both times.
- To prove the plug-in seam without writing another agent's file, I registered a throwaway
  `PeakCut.add("analytics-trends", { load() { … } })` in the page console. Switching to Trends called its
  `load()` and the body it wrote stayed on screen (2 calls across two entries). I then removed the
  throwaway plug-in and cleared the box, so the page is back as I found it.
- The five tabs fit one row at 1216 px with no horizontal scroll (98 px for Trends).
- Ranges and compare still behave after the change: Last 7 days gave
  `{"start":"2026-11-14","end":"2026-11-20","days":7,"label":"Last 7 days"}`; switching compare on gave
  `{"start":"2026-11-07","end":"2026-11-13","days":7}` with the line "Last 7 days, ending 20 Nov 2026,
  compared with the 7 days before"; Lifetime gave the note "Off for Lifetime" with the switch disabled.
  I put the page back to Last 28 days, compare off, Overview.
- Page console stayed empty throughout; no errors from this file.

**What I could not do.** Nothing in my task. The Trends tab shows its sentence and an empty box until
`web/feat/analytics-trends.js` exists; until then a person clicking Trends sees the frame sentence and
nothing under it, which is the same state Audience was in before its file landed. I did not edit
`web/index.html` and did not run the full `python tests/run.py` suite, since I changed no Python.

Skill loaded: frontend-design.
