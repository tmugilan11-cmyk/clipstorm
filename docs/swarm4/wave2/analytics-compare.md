# analytics-compare

Agent 45. Wave 2. Adds one line under each key number on the Insights page, but only while the Compare box is ticked.

Skill loaded before any work: **`frontend-design`**. It was the offered skill that matched a job which is mostly about where one small line goes and how it behaves on a narrow card. Its guidance on working inside an existing design system rather than importing a new one is what I followed: the line uses only the tokens and type sizes the page already has.

## What I built

`web/feat/analytics-compare.js`, one new feature file, 246 lines, 12049 bytes.

It registers exactly one plug-in:

```
P.add("analytics-compare", {
  label: "The change since the period before",
  load() { fill(); }
});
```

**The line.** Under each of the six key number cards it adds one line: an arrow, then words, for example `Up 12 percent on the 28 days before`. Up is green (`var(--good)`), down is red (`var(--bad)`), no change and anything unread are the faint colour the range line above already uses.

**The sentence.** Once under the whole row it adds one sentence saying which days it compared against, and what a dash means: `The previous period was Sep 26 to Oct 23. A dash means there is nothing to compare yet.`

**Where the numbers come from.** The file reads `/api/analytics/summary?days=<n>&compare=1` itself, with `compare=1`, which is the shape that carries a `compare` block with the previous window's cards. It never reads another file's copy and never caches a figure across a range change.

**How a line finds its card.** The key number row carries no key of its own in the DOM, so a line matches a card by the label the card shows. `keysFor()` lowercases the card's own label and returns the server names that label stands for: `views` for Views, `watch_time` for Watch time, `impressions`, `ctr` for Click-through rate, `average_view_duration`, and `subscribers`. A label it does not recognise returns nothing, and that card gets a dash with a sentence rather than a number guessed from position. That is the honest reading of "match cards by their key" for a row that publishes no keys.

**Nothing at all when compare is off.** `where()` asks `window.PeakCutAnalytics.compare()`, which the shell answers with null while the box is unticked or the range is Lifetime. In that case every line and the sentence are removed, so the row is exactly as the key number file drew it. No placeholder, no greyed-out text.

**The rounding is the pill's rounding.** The key number file already draws a percentage pill on each card. To keep the two from disagreeing, the line uses the same rule that file uses: a whole number from 10 up, one decimal below 10. So `1.7%` on the pill is `Up 1.7 percent` on the line, and `12%` is `Up 12 percent`, never `12.0`.

**No invented numbers.** If a card's value or its previous value did not arrive, the line is `– Not sent for the 28 days before`. If the request itself failed, it is `– Not read` and the sentence gives the server's own words. Zero against zero is `No change`, and zero against something is `Up from zero`, because a percentage of zero cannot be taken and saying Infinity would be a lie.

**It follows the row instead of owning it.** The key number file repaints `#an_kpi` on its own schedule and may replace the whole row. This file watches `#view` with a MutationObserver, coalesced at 80 ms, and also listens for the shell's `peakcut:render` event. Before each read it compares the figures standing above it; when they are the same figures for the same range and the lines are already there, it does nothing and reads nothing.

## Files

- `web/feat/analytics-compare.js` (new, the only file I wrote besides this report)
- `docs/swarm4/wave2/analytics-compare.md` (this report)

I did not touch `web/index.html`, `web/feat/analytics-kpi.js`, `web/feat/analytics.js`, the server, or any other agent's file.

## What I ran, and the literal output

All three contract gates, from the `peakcut/` directory.

```
$ node --check web/feat/analytics-compare.js
NODE OK
```

```
$ python tests/test_feat_files.py
ok   analytics-compare.js parses
ok   analytics-compare.js declares one plug-in
ok   analytics-compare.js is named after itself
ok   analytics-compare.js is the only owner of analytics-compare
ok   analytics-compare.js does not write into index.html
ok   analytics-compare.js escapes what it draws
ok   analytics-compare.js uses no absolute origin
ok   analytics-compare.js invents no clashing id
...
{"files": 37, "checks": 302}
All checks passed.
```

```
$ python tests/test_menu_pages.py
All checks passed. 142 ok
```

I also drove the real page in a browser against the live server at 127.0.0.1:8798.

**Compare off, on a fresh load.** Zero lines, zero sentences, the row untouched:

```
{"cmp":true,"checked":false,"cards":6,"lines":0,"note":0,
 "range":{"start":"2026-10-24","end":"2026-11-20","days":28,"label":"Last 28 days"},"compare":null}
```

**Compare ticked, real PeakCut records, no channel connected.** The route answers `"compare":null`, so every card shows a dash and the sentence names the dates:

```
{"n":6,"texts":["– Not sent for the 28 days before", "...same for all six"],
 "note":"The previous period was Sep 26 to Oct 23. A dash means there is nothing to compare yet."}
```

**Compare ticked, with the route temporarily answered by a YouTube-shaped body** (`window.PeakCut.api` was wrapped for the duration, then restored):

```
{"pill":["12%","1.7%","–","–","0%","–"],
 "nums":["51,000","1,200.5","–","–","0:34","–"],
 "lines":["Up 12 percent on the 28 days before",
          "Up 1.7 percent on the 28 days before",
          "– Not sent for the 28 days before",
          "– Not sent for the 28 days before",
          "No change on the 28 days before",
          "– Not sent for the 28 days before"],
 "note":"The previous period was Sep 26 to Oct 23. A dash means the server did not send that card for the 28 days before."}
```

The pill and the line agree on every card, which is the point of sharing the rounding rule.

**A fall and a rise from zero:**

```
[{"t":"Down 30 percent on the 28 days before","c":"akcmp down","col":"rgb(211, 52, 63)"},
 {"t":"Up from zero on the 28 days before","c":"akcmp up","col":"rgb(15, 138, 87)"}]
```

Colours read from the live page: good `rgb(15, 138, 87)`, bad `rgb(211, 52, 63)`, faint `rgb(160, 148, 140)`.

**Every read failing** (the route made to throw `Bad Gateway`):

```
{"lines":["– Not read","– Not read","– Not read","– Not read","– Not read","– Not read"],
 "note":"The previous period could not be read. Bad Gateway. Reload this page to try again."}
```

**Lifetime.** The box is disabled by the shell, and this file draws nothing:

```
{"lines":0,"note":0,"disabled":true,"checked":true,"range":"life"}
```

**Requests.** One read for the key row and one for this file per load or range change, and zero on a repaint of the same figures:

```
{"after1":3,"after2":3,
 "paths":["S?start=2026-10-24&end=2026-11-20&days=28&compare=1",
          "S?start=2026-10-24&end=2026-11-20&days=28&compare=1",
          "S?days=28&compare=1"]}
```

(The two identical lines are the key row's own read and this file's read, which ask the same question in different words. Before I added a two second stand-off on repeat asks of the same address, a repaint cost a third read.)

**Layout at three widths.** Nothing is clipped and the page never scrolls sideways; a narrow card wraps the line instead of cutting it:

```
[{"w":900,"n":6,"h":[33,33,33,33,33,33],"clipped":0,"pageOver":0},
 {"w":700,"n":6,"h":[50,50,50,50,50,50],"clipped":0,"pageOver":0},
 {"w":520,"n":6,"h":[83,83,83,83,83,83],"clipped":0,"pageOver":0}]
```

**Tab round trip** (Overview to Content and back): the lines travel with the Overview panel and come back, six of them, one sentence, nothing stray:

```
{"before":6,"during":6,"after":6,"note":1}
```

**House style scan of the file:**

```
lines 246 bytes 12049
em dash 0 en dash 1 bang 32   (all 32 are code: !box, !cards, !==, !!(...))
marketing []                  window.ic False
nonascii ['–']                http []
```

The one en dash is the dash the card itself shows for "nothing arrived". No exclamation mark appears in any sentence. No em dash anywhere.

No console lines were logged during any of this.

## What I could not do, and what a reviewer should know

**I could not see a real connected channel.** PeakCut on this machine has no YouTube token, so the route always answers `"compare":null`. Every percentage I checked came from a body I supplied in place of the route's answer, shaped from `studio/api_analytics.py` (`compare` holding `start`, `end` and `cards` keyed by the server's own names). The dash path, the error path and the off path were all exercised against the real server. The maths path was exercised against that body only, so a reviewer with a connected channel should tick Compare once and confirm the line reads the same way as the pill.

**Two of the six cards will usually show a dash on a real channel.** The key row's own six cards are Views, Watch time, Impressions, Click-through rate, Average view duration and Subscribers gained, while the summary route sends views, watch_time, average_view_duration, average_view_percentage, subscribers and engagement. Impressions and Click-through rate have no name in the compare block unless the route grows one, and `average_view_percentage` and `engagement` have no matching card. The file says `– Not sent for the 28 days before` for those rather than borrowing another card's number. If the route later sends impressions and ctr, they are already listed in `CARDS` and will fill in with no change here.

**A card the file does not recognise gets a dash.** If another agent renames a card's label, `keysFor()` stops matching it. That is deliberate, since a number placed under the wrong card is worse than a dash, but it does mean the labels in `CARDS` are a coupling worth keeping in mind.

**The sentence sits above the key row's own note.** That file already writes one sentence under the row (`PeakCut's own records. Connect a YouTube channel for views, watch time and click-through rate.`). Mine is inserted directly after the grid, so the order on screen is the row, then my sentence, then its note. Both read as separate sentences and I did not suppress the other file's, since it is not mine to remove.

**The two second stand-off is a small compromise.** Repeat asks of the same address within two seconds reuse the last answer instead of reading again, which is what stops a repaint of the row from becoming a request. A range change builds a different address and always reads fresh, and the stand-off is cleared by nothing else, so a stale answer can only be served inside that two second window while the range has not changed.

**The lines are the row's height.** Each line adds about 17 px to its card, so the row is taller with Compare on. The cards are equal height, so they stay level; the effect is simply that the block grows, which is the price of putting a sentence under a number.
