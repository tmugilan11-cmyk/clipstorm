# grid: a week of posting, as a grid

Slug: `grid`. One file owned and changed: `peakcut/web/feat/grid.js` (198 lines, 11,884 bytes).
The report itself is `peakcut/docs/swarm3/grid.md` (182 lines).
Nothing else in the repository was edited. No git command was run. The server was not restarted.

Skill loaded with the `skill` tool: **`ui-design-guide`**.

## What it does

Settings > Tools gains one card, "This week".

- **Seven day columns.** The last seven entries of `daily` from `GET /api/overview`, oldest on the left and
  today on the right. Each column shows the weekday, the date (`19 Nov`), a bar whose height is that day's clip
  count scaled against the busiest day of the week, then the clip count, the post count, and the views written
  short (`980`, `1.2k`, `3.4m`).
- **Today is marked.** The column for the current date gets a warm background and a stronger border, so the
  right-hand end of the week reads as "now" without a legend.
- **A total line** under the columns: clips made, posts that went out, views, all for those seven days.
- **The queue below.** Posts whose `status` is `scheduled` or `posting` (the two values `studio/posting.py` uses
  for a post that has not gone out yet), sorted newest due first, capped at 10. Each row shows the clip title,
  the creator name, and the due time as `Today 18:30`, `Tomorrow 09:00` or `Wed 26 Nov, 09:00`, with a small
  `Scheduled` / `Posting now` label. Empty state is the exact string `Nothing queued.` The header shows `4 of 4`
  when the list is complete and still says how many exist when ten or more are waiting, so ten rows never look
  like the whole queue.
- **A Refresh button** (`data-act="pcgridrefresh"`) re-fetches and redraws. It disables itself and shows
  `Refreshing…` while the request is in flight, then goes back to `Refresh`. A second press while the first is
  still running is ignored.

### How it plugs in

`tools()` returns a `<section class="set-sec">` with the title, one help line, the Refresh button and
`<div id="pcgrid"></div>`. `index.html` collects that through `PeakCut.toolsHtml()` and puts it inside the existing
Settings > Tools mount, unchanged. `load()` fetches and draws. `act.pcgridrefresh` is routed by `plugins.js`.
CSS is registered once with `window.PeakCut.css("grid", …)`.

### Escape and fail-soft behaviour

Every value that comes from the server goes through the page's own `esc()`: clip titles, creator names, statuses,
day labels, and every number. The card never builds HTML from unescaped data.

Both the fetch and the drawing step are wrapped. A failed request paints one quiet line, `Could not read this
week. <reason>`, and returns. A response in an unexpected shape paints one quiet line instead of throwing. A
`daily` array that is missing or empty also paints one line rather than an empty box. Nothing in this file throws
into the page's click handler.

## Endpoint and the real shape

`GET /api/overview` is `index.html` → `studio/server.py:1511` → `posting.overview()` (`peakcut/studio/posting.py:245`).

It answers `{"paused", "creators", "posts", "daily", "alerts", "recording"}`. Two details worth recording because
they differ from a guess:

- **There is no top-level `queued` key.** The queued count is per creator, as `creators[].queued`. The card does
  not use it; it counts the waiting posts in `posts` itself.
- **`posts` is `queue + done`.** Waiting posts come first (`status` in `("scheduled","posting")`, `due_at`
  ascending), then up to 15 finished ones (`posted`, `failed`). The card filters to the waiting two, so the
  finished posts in the same array never reach the queue list.
- `daily` is the last 14 days, oldest first, each `{day: "YYYY-MM-DD", clips, posted, views}`. The card draws
  `.slice(-7)`.

`due_at` is unix seconds. `views` can be `null`. `creator_name` can be `""`, which the card shows as `No creator`.
`title` can be `""`, which the card shows as `Clip`.

## Exact commands and their output

```
$ cd peakcut && node --check web/feat/grid.js && echo "JS OK"
JS OK
```

```
$ curl -s http://127.0.0.1:8798/api/overview | head -c 500
{"paused":false,"creators":[],"posts":[],"daily":[{"day":"2026-11-06","clips":0,"posted":0,"views":0},{"day":"2026-11-07","clips":0,"posted":0,"views":0},{"day":"2026-11-08","clips":0,"posted":0,"views":0},{"day":"2026-11-09","clips":0,"posted":0,"views":0},{"day":"2026-11-10","clips":0,"posted":0,"views":0},{"day":"2026-11-11","clips":0,"posted":0,"views":0},{"day":"2026-11-12","clips":0,"posted":0,"views":0},{"day":"2026-11-13","clips":0,"posted":0,"views":0},{"day":"2026-11-14","clips":0,"pos
```

The full body is 14 days, `2026-11-06` through `2026-11-19`. Thirteen of them are all zeroes; only `2026-11-19`
has anything, `{"clips":1,"posted":0,"views":0}`. `creators` and `posts` are both empty, so against live data the
card draws seven columns with one bar at full height (104px), six bars at the 2px floor, and `Nothing queued.`

```
$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["autopilot.js","filters.js","grid.js","heard.js","log.js","mood.js","peek.js","stage.js","style-tiles.js"]}

$ curl -s http://127.0.0.1:8798/healthz
{"ok":true}
```

`grid.js` is in the served list, which is how `plugins.js` discovers and loads it.

## Live browser check

Against `http://127.0.0.1:8798/app/settings/tools`:

- `window.PeakCut._order` contains `grid`.
- The card mounts inside `#toolsec` with the other Tools cards; the title, the help line and the Refresh button are
  present.
- Seven columns draw, one per day, with 7 bars.
- Bar heights against live data: `2px` six times, `104px` once. Measured in the browser at 24px wide, so the
  scaled width sticks and the floor is real.
- Footer against live data: `1 clip made / 0 posted / 0 views` (singular, correct).
- Queue against live data: `Nothing queued.`
- Refresh: pressing it sets the label to `Refreshing…` and `disabled=true`, then returns to `Refresh`,
  `disabled=false`, with the card redrawn.

To exercise the paths live data cannot reach, `window.PeakCut.api` was stubbed in the page and the Refresh button
pressed. The stub was then removed and the real function put back, after which the card drew live data again.

- **Queue with data:** 4 waiting posts, newest due first, header `4 of 4`. Rows read `Next week | Sam | Fri 27 Nov,
  22:35`, `Short clip | No creator | Tomorrow 23:35`, `… | Sam | Today 23:35`, `… | Priya | Today 22:36 | Posting
  now`. A `posted` post in the same stub and a `cancelled` post were both correctly left out, and `0` due times
  printed `No time set`.
- **Cap:** 14 waiting posts gave exactly 10 rows and a header of `10 of 14`.
- **Escaping:** a title of `<img src=x onerror="window.__xss=1">Hook` and a creator of `<b>bad</b> & co "q"`
  rendered as literal text. `document.querySelectorAll("#pcgrid img").length` was `0`, no `<b>` was created inside
  the row, and `window.__xss` stayed undefined. Nothing executed.
- **Numbers:** `980` printed as `980`, `1200` as `1.2k`, `3400000` as `3.4m`, and the week total of `15400 + …`
  printed `3.4m`. Bars scaled `59, 104, 45, 15, 74, 30, 2` px for clip counts `4, 7, 3, 1, 5, 2, 0`.
- **Failure:** a throwing stub painted `Could not read this week. Server said no.` and left the Refresh button
  enabled and labelled `Refresh`. It did not throw.

Screenshots were captured to the browser download folder and are not checked into the repo:
`C:\Users\Asus\Downloads\grid-card2.png` (live data, one full bar and six 2px bars) and
`C:\Users\Asus\Downloads\grid-card-full.png` (stubbed data: bars scaled, today marked, queue rows with creator and
due time).

## Two problems found and fixed

**1. A class-name collision inflated every empty bar from 2px to 98px.** The card first marked a zero-clip day with
`class="bar empty"`. `index.html:536` already owns a global `.bar` rule (`height:6px; margin:6px 0`) and the page
also has a global `.empty` rule (a dashed 48px-padded flex placeholder box, used for empty states). The zero bars
picked up both. Measured in the browser, each empty bar rendered 42×98 with the dashed placeholder interior, so seven
of the columns looked like tall grey slabs and only the real bar was correct. Renaming the modifier to `zero` and
pinning `margin:0; border:0` on `.pcgrid .bar` fixed it; bars now measure exactly 24px wide and 2px or scaled
height. Lesson for the other feature files: `index.html` has short global class names, so a modifier as ordinary as
`empty` can drag in a whole placeholder style. Prefix or rename.

**2. A hard refresh straight onto `/app/settings/tools` left the mount empty.** `index.html` calls `loadTools()`
once, when it paints the tab. `plugins.js` loads the feature files about 1.4 seconds after boot, so on a cold load
of that URL the mount is assembled before any feature has registered and the tab keeps an empty slot; nothing asks
again, because `plugins.js`'s repaint loop watches only `#jobs`, `#ov`, `#cbody`, `#clipdlg`, `#sform` and
`.topbar`, none of which are in Settings. My `load()` therefore never ran, so recovering inside `load()` was not
possible.

The fix lives entirely in `grid.js`: when the file is evaluated it starts a short watch (about seven seconds, every
300ms) that fills the mount if, and only if, the mount is present and empty. It calls `PeakCut.toolsHtml()` and then
`PeakCut.loadTools()`, exactly what `index.html` would have done, and stops the first time it succeeds.
Verified: a hard load of `/app/settings/tools` now shows all five Tools cards and the grid, with no click.

This is a work-around in my own file for a load-order gap in files I do not own. The proper fix belongs to whoever
owns `peakcut/web/plugins.js`: either mount the Tools sections lazily when the tab opens, or add `#toolsec` to the
`repaint()` watch list. Until then, any other feature that only implements `load()` without its own watch will be
missing on a cold load of that URL, and will appear as soon as the user clicks another Settings tab and comes back.

## What could not be tested

- **Real queue data.** The live server has no creators and no posts, so every queue row I saw came from a stubbed
  `PeakCut.api`. The shape is the real documented shape (`posting.py:265`, `OPEN = ("scheduled","posting")`), and
  `scheduled` and `posting` are the two real waiting values, but the card has not been seen against an actual
  pending post.
- **Real views.** Live `daily` is all zeroes, so `1.2k` and `3.4m` were only exercised through the stub. The
  formatter itself was checked directly: `980` stays `980`, `1200` is `1.2k`, `3400000` is `3.4m`.
- **Sign-in on.** The live server runs with sign-in off, so the card was checked as the built-in owner only. It uses
  `PeakCut.api()`, which handles the 401 redirect the same way the rest of the app does.
- **Narrow screens.** The four-column collapse below 640px was written and `node --check`ed but not looked at in the
  browser; the window was not resized.

## Reviewer notes

- The file is self-contained: one IIFE, CSS registered once, one `PeakCut.add("grid", …)` call. It adds no
  dependency and touches no global beyond `window.PeakCut`.
- CSS uses only the palette variables `index.html` already defines (`--brand`, `--brand-soft`, `--brand-line`,
  `--brand-deep`, `--line`, `--line-2`, `--muted`, `--text`, `--dim`, `--faint`, `--r`). It adds no shadow, per
  `AGENTS.md`, and no hover rule of its own.
- `prefers-reduced-motion` turns off the bar height transition.
- The 2px floor is applied unconditionally (`Math.max(2, …)`), so a zero-clip day always draws a visible sliver
  rather than nothing, which is what the brief asked for. The zero bar is a lighter colour so it still reads as
  "empty" rather than as a tiny number of clips.
- Views are written lower-case (`1.2k`) as the brief specified. The page's own `fmtK` helper uses upper-case
  (`1.2K`); the difference is deliberate and easy to change if the reviewer prefers one style across the app.
- `grid` and the existing home-page chart read the same `daily` array. They are different views of it, not
  duplicates: the home chart is 14 days as one bar chart sized for the overview page, and this is 7 days as
  columns inside Settings, aimed at the day you are sitting in.
