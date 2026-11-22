# analytics-retention

Agent 41. Wave 2. A retention curve for one video, in the Content tab of the Insights page.

Skill loaded before any work: **`frontend-design`**. It was the one skill from the offered list that matched this job, because the whole task is one drawn figure inside an existing page: what the eye reads first, how much of the frame the line may take, and how to keep the caption and the hover box from competing with the curve. The parts I leaned on were its advice to hold one visual language per surface and to let a chart carry a title, an axis word and nothing else, which is why the card reuses the page's own `.card` and `.help` classes instead of introducing a second look.

## What I built

`web/feat/analytics-retention.js`, one new feature file, 446 lines, 21763 bytes.

It registers exactly one plug-in:

```
P.add("analytics-retention", { label: "Retention curve", load() { look(); } });
```

Because the Insights shell calls `load()` on every plug-in whose name starts with `analytics-`, this card is redrawn on every range change and every tab switch without the shell knowing it exists.

### Where it sits

The card mounts itself as a sibling of `#an_table` inside `[data-an-panel="content"]`, placed straight after the table when the table is a direct child of the panel, and at the end of the panel otherwise:

```
<div class="an-ret card" data-ar="root">
  <div class="card-head">
    <div><div class="rttl"><svg .../> <h2>How far people watched</h2></div>
      <p class="help">One video, from its first second to its last. The list is the same videos the table above is showing.</p></div>
    <label class="rpick"><span>Video</span><select data-ar="pick" aria-label="Video to draw the retention curve for">...</select></label>
  </div>
  <div data-ar="body">...</div>
</div>
```

`analytics-table.js` was not edited and is not read for state. It rewrites the whole inside of `#an_table` on every draw, so a card placed inside that box would be wiped. Placing it next to the box survives those rewrites, and the mount function looks the panel up again on every draw rather than holding an element, because the shell replaces the panel's contents on a tab change.

### The picker, and where the ids come from

The task said the picker is built from the video ids already in `#an_table`. They are not there. I read `analytics-table.js` looking for one and then grepped for it:

```
grep -n "video_id\|dataset.video\|data-video" web/feat/analytics-table.js   # no output
```

The table draws each row as a thumbnail, a title and numbers, and keeps its rows in a private `box.__ant` object with fields `{title, thumb, short, views, watch, avd, avp, imp, ctr, likes, comments, shares, subs}`. No id reaches the DOM and no id is exposed. Since that file is owned by another agent and must not be edited, the picker takes its ids from the same route the table itself reads, `GET /api/analytics/videos`, whose rows do carry `id`.

To stay in step with the table rather than beside it, the file reads the titles the table is currently showing (`#an_table .ant-name`) and uses them twice: to filter the route's ids down to the videos on screen, and to order the picker the way the table is sorted. A filter typed into the table's own search box therefore changes the picker too. This happens on every draw, not only when the list arrives, because the table re-sorts and re-filters without telling anyone. The whole list is kept in memory, so clearing the table's filter brings the hidden videos back into the picker without another request. If the table has not drawn yet, or has no title on screen at all, all videos are offered. A pick already made is never dropped by a filter, so the curve on screen cannot disappear because someone typed in the search box.

The range comes from the shell, not from a second control. The videos route takes `days`, not from and to, so `winKey()` turns `window.PeakCutAnalytics.start`/`.end` into a day count (clamped to 1..3650, default 28) and uses that as the cache key. With no shell present it falls back to 28.

### The curve

`GET /api/analytics/retention?video=<id>` answers `{vid, points:[{at, watching}], note}` where both numbers are already percentages 0 to 100. The card draws:

- one `<polyline class="rline" points="...">`, which is the curve, is the only line drawn for data, and is built from the points sorted by `at`;
- one `<path class="rarea">` filled at 6 percent opacity, the same shape closed to the baseline, for weight;
- y grid lines and labels at 0, 25, 50, 75 and 100 percent, all from the fixed `TICKS` list, so the y axis is always 0 to 100 percent and never rescales itself;
- x labels at 0, 25, 50, 75 and 100 percent of the way through the video, captioned "Position through the video";
- the word "Still watching" at the top left, the axis's own name;
- `role="img"` and an aria-label naming the first and last point, for a screen reader;
- a hover layer: a dashed vertical cursor, a ring dot on the line, and a floating box.

The hover box is positioned with `getBoundingClientRect` maths scaled by `svgWidth / 640`, clamped inside the card, and hidden on pointer leave. Arrow keys move it too: Left and Right step one point, Home and End jump to the first and last, Escape hides it, and the wrapper is focusable so a keyboard can reach it at all.

The box names a real second when the video list sent a length:

```
2:00 into the video
Still watching      55.5%
Through the video   50%
```

and falls back to the share of the video when it did not:

```
50% into the video
Still watching      61%
```

### Sentences instead of blanks

- No row in range: `Pick a video to see how far people watched.` followed by `No videos in this range yet, so the picker is empty.` and a disabled picker.
- Rows but nothing picked: `Pick a video to see how far people watched.`
- Picked, fewer than two points: `This video has no retention curve to draw yet.` (one sentence, no axes, no empty frame).
- List route failed: `Could not read the list of videos. <the server's own words> Try again` with a working button.
- Curve route failed: `Could not read the retention curve for this video. <the server's own words> Try again` with a working button.

Every one of those strings is written with `esc()` around the server's part. Nothing from the server reaches `innerHTML` unescaped: titles, ids and the route's `note` all go through `esc()`.

Below the curve sits one `.rnote` that says what the picture does not: that the second in the box is the share of the video just read and came from the length the video list sent (or that no length was sent, so the box names the share instead), and that the curve covers every day YouTube holds for this video while the response names no dates, so no date range is claimed for it. That last sentence exists because the retention route takes only `video`; it has no from and to, and inventing one would have been a number the server never sent.

## Files

- `web/feat/analytics-retention.js` (new, the only source file I wrote)
- `docs/swarm4/wave2/analytics-retention.md` (this report)

I did not touch `web/index.html`, `web/feat/analytics.js`, `web/feat/analytics-table.js`, the server, or any other agent's file.

## What I ran, and its literal output

### Gate 1, the file parses

```
$ node --check web/feat/analytics-retention.js
NODE-CHECK OK
```

Printed nothing on its own; exit code 0.

### Gate 2, the feature-file contract

```
$ python tests/test_feat_files.py
ok   analytics-retention.js parses
ok   analytics-retention.js declares one plug-in
ok   analytics-retention.js is named after itself
ok   analytics-retention.js is the only owner of analytics-retention
ok   analytics-retention.js does not write into index.html
ok   analytics-retention.js escapes what it draws
ok   analytics-retention.js uses no absolute origin
ok   analytics-retention.js invents no clashing id
{"files": 37, "checks": 302}
All checks passed.
```

Re-run after every edit to the file, including the last one, with the same ending: `{"files": 37, "checks": 302}` / `All checks passed.`

### Gate 3, the menu-page contract

```
$ python tests/test_menu_pages.py
ok   analytics.js draws its page
ok   learn.js draws its page
ok   menu-pages.js draws its page

All checks passed. 142 ok
```

No page registration was added by me; this gate is run because the contract lists it and because the Insights page must still pass with one more feature file loaded.

### The loader serves the new file

```
$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["analytics-audience.js","analytics-charts.js","analytics-compare.js","analytics-empty.js","analytics-export.js","analytics-help.js","analytics-kpi.js","analytics-realtime.js","analytics-retention.js", ...]}
```

`analytics-retention.js` is in the list. The server reads the folder live, so no restart was needed and none was made.

### The two routes, by hand

```
$ curl -s -w '%{http_code}\n' 'http://127.0.0.1:8798/api/analytics/retention?video='
400
{"detail":"Paste a YouTube link or a video id."}

$ curl -s -w '%{http_code}\n' 'http://127.0.0.1:8798/api/analytics/retention?video=dQw4w9WgXcQ'
400
{"detail":"Retention comes from YouTube. Connect a channel under Connected apps."}

$ curl -s 'http://127.0.0.1:8798/api/analytics/videos?days=28&limit=5'
{"source":"peakcut","days":28,"start":"2026-10-23","end":"2026-11-19","rows":[],"total":0,
 "note":"PeakCut's own posts. Watch time and the rest come from YouTube."}
```

This instance has no YouTube channel connected, so the live retention route answers 400 with a sentence. That is the honest state of the machine, not a fault in the file, and it is why the failure path matters here as much as the happy path.

### What the browser showed, at http://127.0.0.1:8798/app/analytics

The card mounted in the Content panel in the right place:

```
kids: ["an-hint","an_table","set-sec ast","an-ret card"]
```

The empty state, with the real server and no videos in range:

```
body: "Pick a video to see how far people watched.\n\nNo videos in this range yet, so the picker is empty."
selDisabled: true
opts: [" :: Pick a video"]
```

The picker, with the videos route stubbed to return two rows so there was something to pick:

```
opts: [" :: Pick a video", "dQw4w9WgXcQ :: A first video", "abcDEFghi12 :: A second video"]
selDisabled: false
```

The curve, after picking the first video (stubbed points, real draw path):

```
linePts: "46.0,26.0 103.8,58.4 190.5,82.8 335.0,92.7 479.5,118.7 624.0,143.0"
area:    "M 46.0 176.0 L 46.0 26.0 L 103.8 58.4 L 190.5 82.8 L 335.0 92.7 L 479.5 118.7 L 624.0 143.0 ..."
label:   "Retention curve for A real video: 6 points, from 100 percent watching at 0 percent through the video,
          to 22 percent watching at 100 percent through."
yTicks:  ["0%","25%","50%","75%","100%"]   (and the same five again on the x axis)
```

The hover box over the 50 percent point of a 4:00 video:

```
tip:       "2:00 into the video | Still watching | 55.5% | Through the video | 50%"
tipOn:     true
dot:       ["335.0","92.7"]
cursorOn:  true, cursorX "335.0"
tipBox:    ["612px","165px"]
```

Keyboard, same curve: `ArrowRight` gave `0:00 into the video | Still watching | 100% | Through the video | 0%`, `End` gave `4:00 into the video | Still watching | 22% | Through the video | 100%`, `Escape` turned `tipOn` false.

The no-length variant, for a row whose `secs` is null:

```
tip:  "50% into the video | Still watching | 61%"
note: "How much of the video people watched. The video list did not send a length for this video,
       so the box names the share of the video instead of a second. The curve covers every day YouTube
       holds for this video; the response does not name those dates, so none are shown here."
```

A video with no points:

```
body:    "This video has no retention curve to draw yet."
hasSvg:  false
```

The real failure path, real route, real 400:

```
body:      "Could not read the retention curve for this video. Retention comes from YouTube.
            Connect a channel under Connected apps. Try again"
hasRetry:  true
retryText: "Try again"
hasSvg:    false
```

Pressing Try again, or changing the range in the shell, both send the request again. Changing the shell to Last 90 days sent `/api/analytics/videos?days=90&limit=200` and redrew the card:

```
seen: ["/api/analytics/timeseries?metric=views&days=90&...", "... /api/analytics/videos?days=90",
       "/api/analytics/videos?days=90&limit=200"]
```

The picker follows the table when the table is filtered or re-sorted. With two videos in the route's answer and the table simulated showing only the second, the picker offered only that one; with both titles back, both returned; with no titles on screen at all, the full list came back. All three from the live page after the Arrange refactor:

```
filtered:   ["Pick a video","Zebra video"]
both:       ["Pick a video","Alpha video","Zebra video"]
none:       ["Pick a video","Zebra video","Alpha video"]
```

The same three checks before the refactor showed `filtered` still carrying both videos, which is the bug that refactor fixed: the order and the filter were applied only when the list arrived, so a table that re-sorted afterwards left the picker stale.

A screenshot of the card in place, with the curve and the hover box open, is at `C:\Users\Asus\Downloads\retention-final.png`. It shows the card under the table, the line falling from 100 percent to 22 percent, the dashed cursor and the box reading `2:00 into the video / Still watching 55.5% / Through the video 50%`.

## Three bugs I hit and fixed

The first version drew nothing in a browser tab that was in the background. `document.hidden` was true, so `requestAnimationFrame` never fired (`rafFired: 0` after 900 ms) and the card never mounted. Since a background tab is a normal state for this page, the tail now tries a frame and also sets a 250 ms timer, and whichever runs first draws once:

```
try { requestAnimationFrame(draw); } catch (err) { /* older engine: the timer below still draws */ }
setTimeout(() => { if (queued) draw(); }, 250);
```

`node --check` and both Python gates were re-run after that edit and after the empty-state edit below.

A second, smaller fix: the no-videos-in-range branch used to print only `No videos in this range yet, so there is nothing to draw here.`, which pushed the required empty-state sentence off the screen exactly when the screen was empty. It now leads with `Pick a video to see how far people watched.` and puts the range sentence underneath.

A third, found late: the order and the filter were applied once, when the list of videos arrived, so a table that re-sorted or re-filtered afterwards left the picker stale. `merge()` was split into `dedupe()` (which reads the route's rows once) and `arrange()` (which is called on every paint), and the unused rule that emptied the pick after a failed list read was simplified. The live three-step check in the section above is what caught it and what confirms the fix.

## What the card looks like

One card, the page's own `.card` with its `.card-head`, under the table and above the Shorts block. Left of the header: a small chart icon, the title `How far people watched`, and one `.help` line saying the list is the same videos the table shows. Right of the header: the picker, labelled `Video`. Below: the drawing area with a hairline border, the word `Still watching` at the top left inside the frame, the y labels down the left at 0, 25, 50, 75 and 100 percent, the x labels under the baseline, and the caption `Position through the video` centred beneath them. The line is the brand colour, 2.2px, with a 6 percent wash under it. Under the frame, one faint line of `.rnote` explaining what the picture does not claim.

The colours are all from the page's own variables (`--brand-deep` for the line, `--line` for the grid, `--faint` for the labels, `--dim` for the tooltip text, `--bad-soft` and `--bad` for the error row) and the line is drawn with `currentColor` so a theme change moves it without editing this file. No shadows, and the only hover changes are the colour of the dotted reticle and the opacity of the box, which matches the house rule in `AGENTS.md`.

## What I could not do

- **I could not see a real retention curve from this server.** There is no YouTube channel connected here, so `/api/analytics/retention` answers 400 for every id, and `/api/analytics/videos` answers `source: "peakcut"` with an empty `rows`. The drawn points in the checks above came from a stubbed response fed through the real draw path, so the polyline, the axes, the hover box and the keyboard were all exercised, but no number on that figure came from YouTube. With a channel connected the file needs no change; it reads `points` and draws. It has not been seen against real data, and I am saying so rather than implying otherwise.
- **The picker cannot read ids out of `#an_table`**, because that table draws none. It reads them from the route the table reads and keeps the titles and the order in step with the table's own DOM. If someone later teaches `analytics-table.js` to put `data-video` on its rows, a future wave could read the ids straight from there and drop the second request; I did not do that because that file is another agent's.
- No real browser at a narrow width. The CSS has a `max-width:700px` rule that makes the picker full width, and the card is inside the page's own responsive column, but I did not screenshot a phone-sized window.
