# analytics-shorts

Skill loaded before any work: `frontend-design`.

## What I built

A "Shorts" block inside the Insights page, Content tab. It lists the videos in the current range
that run 60 seconds or less, most views first, and it says out loud what "viewed versus swiped
away" means when the server sends those numbers. When the server does not send them, it says so
in one sentence and stays a plain count. No number appears that the server did not send.

Where it sits: the block is a `<section class="set-sec ast">` inserted as the next sibling after
`#an_table`, inside the Content panel (`[data-an-panel="content"]`). `analytics-table.js` is not
touched and does not know this file exists. Nothing is written into `#an_table`.

Why it asks the route itself instead of reading the table: `analytics-table.js` normalises each
row and drops the length (`seconds`) while doing it. Length is the only thing that makes a Short a
Short, so the block calls `/api/analytics/videos` again with the same range the shell has on
screen. That is one extra small request per range, cached per range.

## The rule it applies

- Short means `0 < seconds <= 60`. Exactly 60 counts. 61 does not. A length of 0 or below is not a
  length and the row is counted as "length missing", not as a Short.
- `seconds` is read as a number, or as a `mm:ss` / `h:mm:ss` string, and the field name is looked for
  under `seconds`, `duration_seconds`, `length_seconds`, `duration`, `length`.
- Viewed and swiped away are looked for per row (`viewed` / `stayed` / `swiped_away` / `dismissed`
  and friends) and as a whole-range object (`shorts`, `split`, `viewed_vs_swiped`). A whole-range
  object wins over a sum of rows. A percentage is taken as-is unless it is 1 or below, which is a
  share and is multiplied by 100. A sum of viewed and swiped is turned into its own percentage.
- The one sentence, when the numbers are there:
  "YouTube counts a Short as viewed when someone stays with it and as swiped away when they move
  on: 63,400 of 71,100 looks stayed and 7,700 swiped away."
- The one sentence, when they are not:
  "The server did not send the viewed versus swiped away numbers, so this is a plain count of
  Shorts."

## Every branch it can draw

1. Reading. "Reading the videos..." with `aria-busy`.
2. No videos in the range. A sentence naming the range and offering a wider one.
3. Videos sent but no length on any of them. Names the count and says length comes from YouTube,
   with a link to Connected apps. This is the branch that renders on this install.
4. Shorts found. Count sentence, up to 10 rows, then the one sentence about viewed versus swiped.
5. A dash legend, only when some row is missing its views.
6. Failure. "The Shorts could not be counted. <reason>. Reload the page to try again."

## Files

- `peakcut/web/feat/analytics-shorts.js` (new, 272 lines). The only file I wrote in the app.
- `peakcut/docs/swarm4/wave2/analytics-shorts.md` (this report, new).

Nothing else was edited. `peakcut/web/index.html`, `peakcut/web/feat/analytics.js`,
`peakcut/web/feat/analytics-table.js` and every other agent's file are untouched.

## What I ran, and the literal output

Syntax check:

```
$ node --check web/feat/analytics-shorts.js
exit=0
```

The first run of that same command failed, on the line that reads a length:

```
peakcut/web/feat/analytics-shorts.js:88
      for (const k of DUR) { const try = secs(o[k]); if (try !== null) { sec = try; break; } }
                                   ^^^
SyntaxError: Unexpected token 'try'
```

`try` is a reserved word and cannot be a variable name. It is now `len`.

The feature-file gate:

```
$ python tests/test_feat_files.py
ok   analytics-shorts.js parses
ok   analytics-shorts.js declares one plug-in
ok   analytics-shorts.js is named after itself
ok   analytics-shorts.js is the only owner of analytics-shorts
ok   analytics-shorts.js does not write into index.html
ok   analytics-shorts.js draws only fixed markup
ok   analytics-shorts.js uses no absolute origin
ok   analytics-shorts.js invents no clashing id
{"files": 37, "checks": 302}
All checks passed.
```

The menu-page gate, run once as a courtesy because the count had changed:

```
$ python tests/test_menu_pages.py
All checks passed. 140 ok
```

The server was already running at `http://127.0.0.1:8798`; I did not restart it. It serves the new
file without a restart:

```
$ curl -s http://127.0.0.1:8798/assets/feat | grep -i shorts
"analytics-shorts.js"
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/assets/feat/analytics-shorts.js
200
```

## Checked in the real browser, on the real page

The page was driven with the browser tool against `http://127.0.0.1:8798/app/analytics`, reading
the block back out of the DOM and, for the branches that need numbers this server does not send,
by temporarily replacing `PeakCut.api` with a fake that returns a known answer. The fake was
restored after each check and the page reloaded, so the shipped behaviour is the real route again.

- Overview tab: no block, because the Content panel is hidden and the block only owns Content.
- Content tab: the block appears directly after `#an_table`, one instance only, `h2` at 17px,
  `box-shadow: none`, a `1px solid var(--line)` rule above the next card. Switching Content,
  Audience, Trends six times in a row still leaves exactly one block.
- Real route, empty data: "No videos in this range yet. Publish a clip, or pick a wider date range
  above." The live server sends `rows: []`, so this is what a person sees today.
- Fake rows with lengths (5 rows: 42s, 30s, 60s, 480s, no length; `total: 6`):
  "3 of the first 5 videos in this range are Shorts, meaning 60 seconds or less", three rows,
  0:42 / 0:30 / 1:00, and the plain-count sentence. 480s correctly excluded, exactly 60s included.
- Fake rows with viewed and swiped away (12 rows, range object `{viewed: 63400, swiped_away: 7700}`):
  the viewed-versus-swiped sentence with those exact numbers, and the 10-row cap with
  "The 10 with the most views, out of 12 Shorts."
- Fake rows with no length at all (4 rows, PeakCut's own posts shape): "The server sent 4 videos but
  not how long they run, so PeakCut cannot tell which ones are Shorts. Length comes from YouTube..."
- One video only: "1 Short: the only video in this range runs 60 seconds or less."
- Boundary rows (60, 61, 0, "0:45", "1:05", `duration: 30`, -5, 59.6, `length: "0:12"`): kept were
  60, "0:45", `duration: 30`, 59.6 and `length: "0:12"`; dropped were 61, 0, "1:05" and -5.
- Failure: the sentence names the reason ("The server said no.") and asks for a reload.
- Escaping: a row titled `<img src=x onerror=alert(1)>` with `url` `javascript:alert(2)` rendered as
  visible text, zero `<img>` elements, and no link, because only an `https://` address becomes one.
- A failing range asks once, not in a loop: two calls (the block's own, and the shell's table on its
  own route) and then nothing more across 2.5 seconds.

Screenshot of the block with sample data: taken and read back in this session to check the layout
(heading, range pill, count sentence, five rows with lengths and views, dash legend, the
viewed-versus-swiped sentence all line up, the long title clips at the column edge). The file is
not in the repo, because the browser tool only writes into the Downloads folder:
`C:\Users\Asus\Downloads\shorts-block.png`.

## What I could not do

- The real server at `http://127.0.0.1:8798` has no YouTube channel connected in this workspace, so
  `/api/analytics/videos` answers with `rows: []` and no `seconds` on any row. I could not see the
  list filled from real data, only from a fake answer of the shape the YouTube branch of
  `studio/api_analytics.py` returns.
- `studio/api_analytics.py` sends no swipe or viewed field on any route. So on this install the
  plain-count sentence is always the one that renders, and the viewed-versus-swiped sentence is
  proved only against the fake answer. If a later wave adds those fields to the route, the field
  names this block already reads are `viewed` / `stayed` / `viewed_count` / `viewed_share`,
  `swiped_away` / `swiped` / `dismissed`, and a range object under `shorts`, `split` or
  `viewed_vs_swiped`.
- The block reads length from the route, not from `#an_table`, because that file drops it. If a
  later change makes `analytics-table.js` keep `seconds` on its rows, this block could read the DOM
  instead; it works either way but currently asks the route.

## Rules I kept

- One registration, named after the file: `P.add("analytics-shorts", { load() { fill(); } })`.
- Every interpolated value goes through `esc(...)`, including titles, addresses, durations, counts
  and reasons. `put()` is used when it exists, `innerHTML` only as a fallback.
- No em dash, no en dash literal in the source (`DASH` is `"\u2013"`), no emoji, no exclamation
  mark, no marketing words. No absolute origin. No reference to `index.html`.
- `esc`, `ic`, `go` are bare identifiers. This file never calls `ic`, so no icon name can be wrong.
- Only existing CSS variables, no shadows, hover changes colour only.
