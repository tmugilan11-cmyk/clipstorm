# pill: "1 video running" in the top bar

Agent slug: `pill`. One file owned and written: `peakcut/web/feat/pill.js` (172 lines, 9,000 bytes).

## What it does

From any page in the app, the top bar now carries one small button that says what PeakCut is doing:

- `1 video running` / `3 videos running` when jobs have `status: "running"`.
- `1 recording` / `2 recordings` when a live recording is going. A recording is never added into the video
  count, so the two are never conflated.
- When both happen at once: `1 recording` followed by `2 videos running` as a second clause.
- When nothing is running but work is queued: `1 video waiting` / `2 videos waiting`.
- Nothing running and nothing queued: the button is removed from the top bar entirely.

Clicking it goes to the work: it uses the page's own router to open the video list, then scrolls the first
running card into view and flashes it once. When the thing running is a live recording it targets the live card
instead, because recordings are drawn into their own box (`#live`) rather than as a normal job card.

## How it is built

`window.PeakCut.css("pill", ...)` registers the stylesheet, then `window.PeakCut.add("pill", ...)` registers:

- `after.drawShell()` and `after.drawJobs()`: both repaint the button, because a job changing and the top bar
  being redrawn are the two moments the words can go stale.
- `act.pcrungo()`: the click handler, found by the loader through `data-act="pcrungo"`.

A 1.2 s `setInterval` also repaints, because state can change without the top bar's markup changing. The paint
only writes to the DOM when the words actually differ, so an idle page costs one loop over the job list.

### Where the button is inserted, and why not inside `#actions`

`drawShell` (`peakcut/web/index.html:1291-1348`) ends with `put($("#actions"), act)`, and `put()`
(`peakcut/web/index.html:963`) replaces that element's `innerHTML` whenever the markup string changes. A child
placed inside `#actions` would therefore be destroyed on the next redraw, and a redraw happens on every view
change and every 15 s status poll.

So the button is inserted as a direct child of `.topbar`, immediately after `#actions`:

```js
const acts = bar.querySelector("#actions");
if (acts && acts.parentNode === bar) bar.insertBefore(el, acts.nextSibling); else bar.append(el);
```

That keeps the top bar's own slot and survives every `drawShell` run. It reuses `.btn.sm`, so its height, radius,
font and hover behaviour are the app's, not a new invention.

### Counting, and not counting twice

`tally()` makes one pass over `PeakCut.state().jobs`, counting `running`, `queued` and `live`. It records the job
ids it saw, then counts `creator.live_job` only when that job was not already in the list. A recording whose job
has already reached the list therefore counts once, and a creator row that names a job one poll before it lands
still produces `1 recording` instead of nothing.

### Navigation

`pcrungo` reads the current view. If it is already the library it reveals immediately. Otherwise it clicks the
real sidebar nav button, `#nav [data-act="go"][data-v="library"]`, which the page's own click handler at
`peakcut/web/index.html:2795` routes to `go("library")`, pushing `/app/videos` through `history.pushState`. If no
such button is reachable (for example on a phone, where the sidebar sits behind a menu) it falls back to
`location.href = "/app/videos"`.

Reveal is attempted immediately, again on the next animation frame, and once more after 240 ms, because the job
list can land a frame after the view changes.

### Safety details

- Every label write uses `textContent`; the one `innerHTML` in the file is a fixed literal for the dot and the two
  text spans. No server string reaches markup, so there is nothing to escape.
- `state()` and the whole paint are wrapped so that a thrown error hides the button instead of breaking the page.
  Verified against `PeakCut.state` throwing, against `null` / id-less / unknown-status jobs, and against a missing
  `#actions`.
- Failures are silent and non-fatal by design: no toast, no console noise.
- The two-clause label is joined by a CSS separator for sighted users, so an explicit `aria-label` gives screen
  readers `1 recording, 2 videos running` instead of the run-together `1 recording2 videos running`.
- Dismissible motion: the glow ring and the flash are disabled under `prefers-reduced-motion: reduce`, and the
  scroll becomes instant rather than smooth.

### Styling

Only existing tokens are used (`--brand`, `--brand-soft` family, `--line-2`, `--muted`, `--dim`, `--faint`,
`--live`). Three variants share the shape: brand tint when videos are running, red tint for a recording, neutral
grey while only waiting. The app's house rule is "no shadows", so the flash animates background colour and border
colour only, never a shadow.

## Endpoints used

- `GET /api/sync` (read indirectly, via `PeakCut.state()`, which the page fills from this endpoint). The key for
  this feature is `jobs[].status` (`queued` / `running` / `live` / `done`) and `creators[].live_job`
  (`studio/server.py:703` sets it to the live job's id or `null`).
- `GET /assets/feat` (the loader's file list, which decides whether `pill.js` is served at all).
- `GET /assets/feat/pill.js` (the file itself).

No new endpoint was added. Nothing on the server changed.

## Commands run and their output

```
$ cd peakcut && node --check web/feat/pill.js && echo "JS OK"
JS OK

$ wc -l web/feat/pill.js
172 web/feat/pill.js
```

```
$ curl -s http://127.0.0.1:8798/api/sync | head -c 300
{"v":"1a4b.5.0","jobs":[{"id":"20261119-171742-d88fe196d1","kind":"video","creator":null,"created":1795088862.0077834,"source":{"kind":"file","name":"demo.mp4"},"options":{"max_clips":1,"min_len":5,"max_len":12,"style":"bounce","layout":"blur","quality":720,"range_start":null,"range_end":null,"capti
```

The `jobs` array in that response holds exactly one job, and its `status` is `done`. Nothing is running on the
server, which is why the button is correctly absent in an untouched page.

```
$ curl -s -o /dev/null -w "GET /assets/feat/pill.js -> %{http_code}, %{size_download} bytes\n" http://127.0.0.1:8798/assets/feat/pill.js
GET /assets/feat/pill.js -> 200, 9000 bytes

$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["autopilot.js","day.js","filters.js","grid.js","heard.js","log.js","mood.js","peek.js","pill.js","stage.js","stats.js","style-tiles.js"]}
```

## Live browser verification

Browser tools were available, so the file's behaviour was checked on the real page at `http://127.0.0.1:8798/app`
rather than argued from source alone.

Registration, on an untouched page:

- `pill` is in `PeakCut._order` alongside the other features (the list grows as sibling agents land their files,
  so the position is not meaningful; on the last check it read
  `["filters","autopilot","grid","log","heard","mood","peek","pill","stage","style-tiles","stats"]`).
- `PeakCut.pill.act` = `["pcrungo"]`, `PeakCut.pill.after` = `["drawShell","drawJobs"]`.
- `document.getElementById("pcss_pill")` exists, and its sheet holds every rule below.
- `.topbar .pcrun` is absent because the only real job is `done`. That is the correct idle state, not a miss.

The state matrix, driven through `PeakCut.state().jobs` and forced repaints, reading text, class and `data-job`
fresh after each paint:

| state | button | class |
|---|---|---|
| 2 queued | `2 videos waiting` | `btn sm pcrun is-wait` |
| 1 queued | `1 video waiting` | `btn sm pcrun is-wait` |
| nothing | absent | n/a |
| 2 running | `2 videos running` | `btn sm pcrun` |
| 1 running + 1 queued | `1 video running` (queued not mixed in) | `btn sm pcrun` |
| 2 running + 1 queued | `2 videos running` | `btn sm pcrun` |
| live job `L1` plus creator `live_job: "L1"` | `1 recording` (counted once) | `btn sm pcrun is-rec` |
| live + 2 running | `1 recording` + `2 videos running` | `btn sm pcrun has2 is-rec` |
| 2 live | `2 recordings` | `btn sm pcrun is-rec` |
| creator row only, job not yet listed | `1 recording` | `btn sm pcrun is-rec` |

The click path, measured on the real page:

- With a running job and the view on `/app`, clicking the pill moved `location.pathname` to `/app/videos`,
  `PeakCut.state().view` to `library`, and `section[data-job="20261119-171742-d88fe196d1"]` existed afterwards.
- Exactly one element carried `pcrun-flash`, and it was that `SECTION`. The flash class was gone again after
  2.1 s, and the pill was still present after navigation.
- With no sidebar nav button reachable and the view on the overview, clicking fell through to
  `location.href = "/app/videos"` and landed on the library page.
- A live recording targeted its card, which lives outside `#jobs`; the flash still landed on a real element.

Layout and robustness checks:

- The pill sits as the last child of `.topbar`, right of `#actions`, inside the bar bounds (1920 px wide:
  right edge 1874 against bar right 1902).
- Six forced repaints left exactly one `.pcrun` in the document, so nothing accumulates and no button nests.
- With `#actions` removed from the bar the button still appears; with `PeakCut.state` replaced by a thrower it is
  removed rather than throwing; with `null`, id-less and unknown-status jobs it still reads `1 video running`.
- Rendering was also checked on the creator view, where `#actions` holds a live-record button. The pill sits beside
  it without swallowing it.

## What could not be tested

- **A real running job.** The server has no running or live job right now (one job, `status: "done"`), and I may not
  restart it or create work. The pill was therefore exercised by writing job states into the page's own
  `PeakCut.state()` in the live page and forcing a repaint. Every code path that reads state, paints, navigates and
  flashes ran for real; what is unproven is only a genuinely progressing job arriving from `/api/sync`.
- **A real live recording.** Same reason: no `live` job and no creator with `live_job` exists on this server. The
  dedupe and the `#live` fallback were driven synthetically, and the `#live` box did not exist in that synthetic
  situation, so the fallback to the card was what ran. If a real recording is running, the `#live .livecard`
  branch is the path that will be taken.
- **Phone width.** The viewport could not be narrowed in this session. The CSS was written against the app's own
  breakpoints and inspected, but not seen rendered at 560 px.

## Phone behaviour (as asked, stated explicitly)

The pill is **not** hidden on a phone. At `max-width: 760px` the second clause is dropped, so `1 recording` in red
still shows without the trailing `2 videos running`. At `max-width: 560px` the pill shrinks to a 30 px height with
12 px text, matching how `peakcut/web/index.html:789` already shrinks the top bar buttons. The reason it is kept:
the button is the only sign anywhere in the app that work is happening, and the top bar's own phone rule already
fits `#actions` buttons at that size. If a reviewer judges the phone bar too tight, hiding it under 560 px is a
one-line change in the `@media (max-width:560px)` block, but it would remove the feature's whole point on phones.

## Reviewer notes

- The insertion point is deliberately a sibling of `#actions`, not a child. Moving it inside `#actions` would look
  natural and would break on the next shell redraw, since `put()` replaces that element's `innerHTML`.
- `data-act="pcrungo"` is registered with the loader and was checked for collisions before writing
  (`grep -rn "pcrun\|pcrungo" web/` found nothing).
- The flash animates colour only. An earlier version used a `box-shadow`, which contradicts the app rule in
  `peakcut/AGENTS.md` ("no shadows"); it was rewritten to background and border colour and re-verified.
- The whole feature can be removed by deleting `peakcut/web/feat/pill.js`; it adds no markup to `index.html` and
  touches no other file.
- A 1.2 s interval is used, which is not free but is negligible: it reads the already-polled state and writes
  nothing unless the words differ.
