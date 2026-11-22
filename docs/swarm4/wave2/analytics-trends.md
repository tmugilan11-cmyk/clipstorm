# analytics-trends

Agent 38. Wave 2. Fills `#an_body` on the Trends tab of the Insights page.

Skill loaded before any work: **`fastapi-patterns`**. It was the one skill from the offered list that matched the shape of this job, because the page is a reader of FastAPI routes and the hard part is guessing what a route does not send. Its guidance on raising one clear `HTTPException` with a message a person can read is what I leaned on when I decided the page must show the server's own sentence rather than a generic "something went wrong".

## What I built

`web/feat/analytics-trends.js`, one new feature file, 393 lines, 21073 bytes.

It fills `#an_body` with three blocks and registers exactly one plug-in:

```
P.add("analytics-trends", { load() { fill(); } });
```

**Top searches.** One row per term the server sent: the term, a bar sized by that term's own view count against the biggest row on screen, the view count, and the interest word the server computed. Each row carries a Save button, and a row whose term is already in the saved list shows a check mark and the word Saved instead, so the button cannot be pressed twice for the same term.

**Breakout videos.** One row per video: title (a link when the server sent a `url`), the channel, and the view count for the range. The channel cell reads "Channel not sent" when the answer carried no name, rather than leaving a gap that looks like a bug.

**Saved searches.** The kept terms as chips with a remove button on each. The count sits in the block's pill (`2 of 50`). Remove calls the route and repaints from the list the server answered with, so a refused removal puts the chip straight back.

The frame is painted before any request. `fill()` writes the three sections with their headings, their pill, the range sentence and a loading line in each block, sets `aria-busy`, and only then sends the three requests. Each of the three answers repaints on its own, so a slow route never holds the other two back.

The date range comes from the shell. `asked()` reads `window.PeakCutAnalytics.range()` and sends nothing but `days`. There is no second range control anywhere in the file. Lifetime arrives from the shell as about 7994 days, which the routes refuse (`le=3650`), so anything over 3650 is sent as `0`, which is the value both trend routes read as "everything".

A failure is a sentence inside its own block. Each of the three requests is caught separately and paints `The search terms could not be read. <the server's own words> Reload the page to try again.` The other two blocks keep whatever they already had. `whyOf()` prefers `e.detail` over `e.message`, which is where FastAPI puts its `HTTPException` text.

`P.toast` is called on both save paths: `P.toast("Saved " + term + " to your searches.", "ok")` when the write worked, and `P.toast("That search was not saved. " + why + ".", "bad")` when it did not. A refused save also re-enables the button so the person can try again.

Two smaller decisions worth writing down. First, `mine()` compares the shell's tab name to `"trends"` and every draw path checks it, because Audience, Trends and Traffic all write the same `#an_body` and a stale timer from one must not overwrite another. Second, the block's down-state and the range are read again from the live DOM after each `await`, because switching tabs during a request would otherwise paint into a box that is no longer on screen.

## Files

- `web/feat/analytics-trends.js` (new, the only file I wrote besides this report)
- `docs/swarm4/wave2/analytics-trends.md` (this report)

I did not touch `web/index.html`, the shell `web/feat/analytics.js`, the server, or any other agent's file.

## The routes it reads

The Trends backend appeared while I was reading, so the file calls real routes rather than guessing at ones that did not exist. I confirmed each against the live server on 127.0.0.1:8798:

- `GET /api/trends/searches?days=28&limit=25`
- `GET /api/trends/videos?days=28&limit=25`
- `GET /api/trends/saved`
- `POST /api/trends/saved` with `{term}`
- `DELETE /api/trends/saved?term=...`

Live answers I checked by hand:

```
GET /api/trends/searches?days=28&limit=5
{"rows":[],"source":"peakcut","days":28,"start":"2026-10-23","end":"2026-11-19","note":"No YouTube account is connected, ..."}

GET /api/trends/videos?days=28&limit=3
{"rows":[],"days":28,"start":"2026-10-23","end":"2026-11-19","note":"No YouTube account is connected, ..."}

GET /api/trends/saved
{"terms":[]}

POST /api/trends/saved {"term":"gta 6 clip"}
{"terms":["gta 6 clip"]}

DELETE /api/trends/saved?term=gta%206%20clip
{"terms":[]}
```

I cleared the saved list afterwards, so no test data is left in the person's account.

## What I ran, and the literal output

All three contract gates, from the `peakcut/` directory.

```
$ node --check web/feat/analytics-trends.js
exit=0
```

```
$ python tests/test_feat_files.py
ok   analytics-trends.js parses
ok   analytics-trends.js declares one plug-in
ok   analytics-trends.js is named after itself
ok   analytics-trends.js is the only owner of analytics-trends
ok   analytics-trends.js does not write into index.html
ok   analytics-trends.js draws only fixed markup
ok   analytics-trends.js uses no absolute origin
ok   analytics-trends.js invents no clashing id
...
{"files": 37, "checks": 302}
All checks passed.
```

```
$ python tests/test_menu_pages.py
All checks passed. 142 ok
```

I also drove the page in a real browser against the live server.

The file is served: `GET /assets/feat/analytics-trends.js -> 200 21073 bytes`.

On the Trends tab with no channel connected, all three blocks drew:

```
{"sig":"d28|2026-10-24|2026-11-20","sections":["Top searches","Breakout videos","Saved searches"],
 "text":"Showing 24 Oct 2026 to 20 Nov 2026. The page is set to Last 28 days.\n\nTop searches\nLast 28 days\n\n
 The words people typed into YouTube before they found this channel...\n\n
 No YouTube account is connected, so PeakCut cannot read what people typed to find your videos. Connect a channel
 under Connected apps, then this page fills with the real terms.\n\nBreakout videos\n...\n\nSaved searches\n0 of 50\n..."}
```

The range control switched to Lifetime and the page followed it:

```
{"sig":"d0|2005-01-01|2026-11-20","range":"Showing 1 Jan 2005 to 20 Nov 2026. The page is set to Lifetime.",
 "pills":["Lifetime","Lifetime","0 of 50"],"busy":false,"rects":3}
```

The frame is painted before the answers land. With every request held for 2.5 seconds, the DOM right after the range change already had three sections, three loading lines, the range sentence and `aria-busy="true"`:

```
{"immediately":{"loads":3,"empties":0,"sections":["Top searches","Breakout videos","Saved searches"],
 "busy":"true","range":"Showing 21 Nov 2025 to 20 Nov 2026. The page is set to Last 365 days."}}
```

A save that worked, and one that did not:

```
{"toasts":[["ok","Saved peakcut trends to your searches."]],"chips":["peakcut trends"]}
{"toasts":[["bad","That search was not saved. That search term is longer than 120 characters. Save the start of it instead."]],
 "chips":["peakcut trends"]}
```

Every route failing at once leaves three sentences, not a blank page:

```
{"fails":["The search terms could not be read. Simulated network failure Reload the page to try again.",
          "The videos could not be read. Simulated network failure Reload the page to try again.",
          "Your saved searches could not be read. Simulated network failure Reload the page to try again."],
 "empties":0,"loads":0,"busy":false}
```

One route failing leaves the other two filled:

```
{"fails":["The videos could not be read. Only this route is down Reload the page to try again."],
 "empties":["No YouTube account is connected, so PeakCut cannot read what"],
 "sections":["Top searches","Breakout videos","Saved searches"]}
```

The three blocks lay out on sample rows with no horizontal overflow, and a row with no view count shows the dash:

```
{"rows":5,"vids":3,"chips":["gta 6 lore explained","how to clip a stream"],
 "first":"gta 6 lore explained\n18,422 views\nVery high\nSaved",
 "dash":["18,422","6,110","1,204","96","-","20,411","8,802","340"],"over":[]}
{"rowCols":"417.844px 482.156px 96px 84px 88px","rowH":38,"vidCols":"946px 150px 96px",
 "savedPill":"2 of 50","noteShown":true}
```

The tab cycle leaves nothing empty. I went Audience, Trends, Traffic, Trends, Audience, Trends and checked the box each time:

```
[{"via":"aud","wrap":true,"secs":3,"loads":0,"empty":false},
 {"via":"trf","wrap":true,"secs":3,"loads":0,"empty":false},
 {"via":"aud2","wrap":true,"secs":3,"loads":0,"empty":false}]
```

A text scan of the file came back clean on the house style:

```
em dash 0 en dash 0 bang 35   (all 35 are code: !==, &&, ||, if (!, !!(...))
marketing []                  window.ic False
nondash emoji []
```

I logged no console errors during any of this.

## What I could not do, and what a reviewer should know

**The two empty states depend on the server's own note.** With no channel connected, both data blocks show the server's sentence instead of mine, because a note that names the real cause ("Connect a channel under Connected apps") is better than my generic one. Mine only appears when a route answers with an empty list and no note. That is deliberate, but it does mean the empty wording on a connected-but-quiet channel is the server's, not this file's.

**Breakout videos is this channel's own videos, not other creators.** The brief said "other creators: title, channel, views". The backend at `studio/api_trends.py:270` reads `dimensions="video"` for the connected channel and its note says so in as many words: "This is not YouTube's public trending chart: that read needs a YouTube Data API key, and PeakCut does not keep one, so other channels' videos are not shown here." I did not invent a source for other creators. The block renders `channel` whenever the server sends one and says "Channel not sent" when it does not, which is honest for both shapes and needs no change here if the backend later widens.

**No percentage is drawn from an interest word.** The server sends `interest` as a word ("Very high" through "Very low") computed from the term's share of search views. The bar in each row is sized from the term's own `views`, which is a number the server did send, so the picture cannot claim a precision the answer does not carry.

**The row grid is fixed at five columns.** Below 700px it folds to two columns with the bar across the full width, which I checked at 520px wide and found no overflow. Between 700px and roughly 900px the term column gets narrow and long terms ellipsise. I judged that acceptable over a hanging row, but a reviewer who wants the bar hidden on medium widths can say so.

**I did not add a Trends page registration.** `P.page` is the shell's job (`web/feat/analytics.js`), and `tests/test_menu_pages.py` passes with the registration as the shell agent wrote it, so there was nothing for me to add there.

**The test server was not restarted.** It was already serving the file when I checked, because the asset route reads the folder on each request.
