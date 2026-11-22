# peek — four stills on a finished clip, and one button to take them

**Slug:** `peek` · **File owned:** `web/feat/peek.js` (one file, nothing else edited)
**Skill loaded:** `frontend-design`

## What I built

A finished clip used to be a black box: a cover picture and two numbers until somebody played it.
The server could already cut four stills out of a clip and paste them into one wide strip, and it
already listed them on every clip it had looked at. Nothing on the card showed them. This does.

Two states, both inside the clip card:

- **Has stills.** The strip is drawn under the clip title and above the row of buttons at the
  bottom of the card, at its own shape (the served jpg is 544 by 240, a four-up strip, so it is
  shown wide and never cropped into the 9:16 cover hole), with the four moments it was taken from
  written underneath as `0:03 0:04 0:06 0:07`.
- **Has no stills.** One quiet button in the same place: a dashed outline, a small filmstrip icon,
  the words "Take stills". Press it and it becomes "Taking stills…", disabled, and when the
  server answers the strip replaces it.

The strip is dark on purpose. It sits on the white card, and a film strip reads as a strip when
the frames are held in the page's own `--frame` (near-black) rather than floating on white. No
shadow, no gradient, one hairline border in `--frame-2`, per `AGENTS.md` ("Keep the existing
palette, no shadows, and hover states that change colour only").

### Where it goes in the card

`web/index.html:1774-1796` `clipHtml(j, c)` builds each card. The body is:

```
article.clip
  button.shot[data-act="openclip"][data-j][data-c]      the cover, and the way into the dialog
  div.clip-body
    p.hook                                              the hook line
    p.ttl                                               the title
    div.row                                             (only when the clip has post pills)
    div.clip-foot                                       select / download / copy / delete / Post
```

So the strip is inserted with

```js
body.insertBefore(box, body.querySelector(".clip-foot"));
```

which lands it after `.ttl` (and after `.row`, when present) and before `.clip-foot`, and lets
`.clip-foot` keep its `margin-top:auto` so the buttons stay pinned to the bottom of the card.

## Endpoints used

Both already existed. I added nothing to the backend and edited no Python.

| What | Route | Notes |
| --- | --- | --- |
| Read the strip | `GET /api/jobs/{jid}/peek/{cid}` | `studio/api_preview.py:100-117`, returns `image/jpeg`, `Cache-Control: private, max-age=60` |
| Take the stills | `POST /api/jobs/{jid}/peek?cid={cid}` | `studio/api_preview.py:63-97`, returns `{"ok": true, "frames": [...]}` |
| Re-read the job | `GET /api/jobs/{jid}` | the page's own route, used after the stills are made |

**The `cid` has to be on the query string.** The route is

```python
def peek_clip(request: Request, jid: str, cid: str = Query("", max_length=64), body: dict = Body(default={})):
```

The `body` parameter is declared but never read inside the handler, so a JSON body alone does
nothing. My call sends it in both places, which is harmless and makes the intent obvious in the
network panel:

```js
const got = await P.send("/api/jobs/" + jid + "/peek?cid=" + cid, { cid });
```

Then `GET /api/jobs/{jid}`, then a merge of only `peek`, `peek_at` and `peek_version` onto the
matching clip in the page's state, so no other part of the job object can be clobbered by a stale
read.

## Never a request on draw

The contract's hook, `after: { drawJobs(root) }`, runs on every repaint of `#jobs`, and
`web/plugins.js:72-74` keys its paint cache on `hookName + ":" + el.innerHTML.length`, so my own
insert makes the hook run once more. The whole file is written around that:

- `paint(root)` and `place(card, job)` only read `window.PeakCut.state().jobs` and the DOM. No
  `fetch`, no image request, no `api()`.
- The only fetch in the file is inside `act.peektake`, the button.
- Repainting is skipped when the node already matches: `place()` compares `old.dataset.cid` and
  `old.dataset.state` to the wanted state and returns before touching the DOM.

Proven in the live page: eight consecutive hook calls added **0** resource entries to
`performance.getEntriesByType("resource")`, and the `.pcpeek` node kept the same identity
(`sameNode: true`) across all eight.

## Ids

Every id is checked against `/^[A-Za-z0-9_-]+$/` before it is used anywhere:

- `place()` validates the job id once per card and returns early if it fails, so no URL is built
  from a bad job id at all.
- Each clip id is validated before the strip is built.
- `act.peektake` validates both `data-j` and `data-c` before doing anything, and returns with one
  quiet line ("That clip cannot be read.") if either fails.
- Because the ids that survive are already the only characters a URL may contain, the URL is
  built by plain concatenation and nothing is percent-encoded: `/api/jobs/` + jid + `/peek/` +
  cid, plus `?v=` and a floored non-negative number from `peek_version`. No `encodeURIComponent`,
  per the brief.

Proved: calling the act with `dataset.c = "../../etc"` returned early on the id check.

## Nothing unescaped reaches the page

The contract says it twice, so the file has its own `esc()` (the page's `esc` is also on `window`,
but a feature file should not depend on load order) and every server value goes through it before
it becomes markup: `esc(jid)`, `esc(cid)`, `esc(srcFor(...))`, `esc(alt)`, `esc(mmss(t))`. Markup
is built with `<template>`, never by string-assigning `innerHTML`.

## Failing softly

Every failure path shows one quiet line and puts the button back. Nothing throws into the page:

| Situation | What happens |
| --- | --- |
| Server says the clip is unknown | toast "No such clip in this job." (the server's own words), button returns to "Take stills", enabled |
| Request never lands | toast with the error text, button returns |
| The strip was claimed but the file is gone | the `img`'s `error` (or a `load` with `naturalWidth === 0`) swaps the strip back to the button and toasts "The stills for that clip are gone. Take them again." |
| A clip stops being finished | its `.pcpeek` is removed |
| Bad id on the button | one line, no request |

## A bug worth knowing about

The first version rendered the strip but the image never loaded. The card had been drawn while it
was off screen, so `<img loading="lazy">` never decided to fetch it: `img.complete === false`,
`naturalWidth === 0`, and no entry in the resource timing at all. The box collapsed to 200 by 23
px and stayed empty.

`nudge(box, img, whenDead)` fixes it: an `IntersectionObserver` starts the load when the card
really comes into view, and because the observer does not fire in this browser either (hidden tab,
no layout reporting), there is one `setTimeout(…, 1500)` that checks `getBoundingClientRect()`
once. Starting means `img.loading = "eager"`, and re-setting `img.src` **only** when
`performance.getEntriesByType("resource")` shows the strip was never asked for, so the fix cannot
double-fetch. A 3000 ms check calls `whenDead` if the image is still empty.

After that: `naturalWidth 544`, `naturalHeight 240`, and exactly **one** `/peek/` request.

## Small width handling

The four times row is a nicety. A card can be squeezed to about 150 px on a narrow screen, where
`0:03` does not fit and the labels clipped to `0:…`. Rather than clip, the row disappears:

```css
.pcpeek{container-type:inline-size}
@container (max-width: 126px){ .pcpeek .pat{display:none} }
```

Verified: at 200 px the row is `display:grid` with all four labels intact; at 150 px it is
`display:none`; at 2.6x zoom it is `display:none`; back at normal width it is `grid` again.

## Accessibility

- The strip is a `role="group"` with `aria-label="Stills from this clip"`, and the image has
  `alt="Still frames from this clip"`.
- The strip holds nothing focusable, so the card gains no extra tab stops.
- The button is a real `<button type="button">`, takes focus with the page's own `.btn` focus ring,
  and while it is working it is `disabled` with `aria-busy="true"` and reads "Taking stills…", so
  the state is announced rather than only coloured.

## Exact commands and their output

Run from the workspace root. Nothing else was run against the app; the server was never restarted
and `git` was never invoked.

```
$ cd peakcut && node --check web/feat/peek.js && echo "JS OK"
JS OK

$ curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download}\n" \
    "http://127.0.0.1:8798/assets/feat/peek.js"
200 text/javascript; charset=utf-8 12892

$ curl -s "http://127.0.0.1:8798/assets/feat"
{"files":["autopilot.js","day.js","filters.js","grid.js","heard.js","history.js","keys.js","log.js","mood.js","peek.js","pill.js","stage.js","stats.js","style-tiles.js"]}

$ curl -s "http://127.0.0.1:8798/api/jobs/20261119-171742-d88fe196d1" | head -c 400
{"id":"20261119-171742-d88fe196d1","kind":"video","creator":null,"created":1795088862.0077834,"source":{"kind":"file","name":"demo.mp4"},"options":{"max_clips":1,"min_len":5,"max_len":12,"style":"bounce","layout":"blur","quality":720,"range_start":null,"range_end":null,"captions":true,"format":null,"moment_labels":false},"status":"done","stage":"Done","progress":1.0,"title":"demo.mp4","uploader":"

$ curl -s -X POST -H "Content-Type: application/json" -d '{"cid":"c0"}' \
    -w "\nHTTP %{http_code}\n" \
    "http://127.0.0.1:8798/api/jobs/20261119-171742-d88fe196d1/peek?cid=c0"
{"ok":true,"frames":[{"id":"c0","peek":"c0_peek.jpg","peek_at":[3.0,4.0,6.0,7.0],"peek_version":11}]}
HTTP 200

$ curl -s -o /tmp/peek_strip.jpg -w "HTTP %{http_code} %{content_type} %{size_download} bytes\n" \
    "http://127.0.0.1:8798/api/jobs/20261119-171742-d88fe196d1/peek/c0"
HTTP 200 image/jpeg 18699 bytes

$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST \
    "http://127.0.0.1:8798/api/jobs/20261119-171742-d88fe196d1/peek?cid=nope"
HTTP 404
```

The strip is 18699 bytes and measures 544 by 240 pixels (PIL), which is the four frames side by
side, and is why the CSS shows it at its own shape instead of cropping it.

## What I could not test

- **Only one job exists on this server**, so I could not look at a page with several jobs and
  several clips at once. I did prove the per-clip path by adding a second card in the page (a
  clone of `c0` with `data-c="c1"`, done, no `peek`): it got its own "Take stills" button while
  `c0` kept its strip, one `.pcpeek` per clip.
- **No clip on this machine has a genuinely missing strip.** I simulated it two ways: dispatching
  `error` on the image (strip swaps to the button, correct toast) and asking the server for
  `nosuchclip` (404, "No such clip in this job.", button restored).
- **No new job was started**, so I have not seen the feature on a job that is still working
  through its clips. `place()` requires `String(clip.status) === "done"`, and setting a clip's
  status to `"making"` in the page state left zero `.pcpeek` nodes, which is the behaviour I
  wanted, but that was a state edit rather than a live job.
- The browser I used is the shared one for this workspace, not a fresh profile, so a previously
  cached strip could in principle have hidden a caching bug. `?v={peek_version}` changes on every
  take, so the strip cannot be stale after a take.

## Reviewer notes

- **The hook is idempotent by comparison, not by marker.** `place()` asks "is the node here already
  the one I want?" (same cid, same state) rather than setting a flag, because the page replaces a
  card's markup wholesale when the job changes and any flag would go stale with it.
- **`peek` is checked with `typeof clip.peek === "string" && clip.peek !== ""`**, not truthiness.
  A clip object that has never been looked at has no `peek` key at all; one that was looked at has
  a file name.
- **`DEAD` is a module-level Set of `jid:cid`**, so a strip that failed stays failed across
  repaints instead of retrying on every frame. Pressing the button clears it for that clip, because
  a person asking again is a good reason to try again.
- **`redraw(btn)` does three things** and the order matters: put the button back first (it may
  still be in the DOM if the request failed), then call the page's own `drawJobs()` in a
  try/catch, then `paint(#jobs)` directly, then dispatch `peakcut:render`. The direct `paint` is
  there because the page's paint cache is keyed on markup length and a tiny markup change can slip
  past the watcher.
- **`merge()` copies only three keys.** The rest of the re-read job is thrown away on purpose: a
  full replace would fight the page's own polling and roll back things like a just-selected
  checkbox.
- The four times come from the clip's own `peek_at` and are formatted `m:ss` with `Math.round`,
  the same way `heard.js` formats times, so the two features read alike.
- Comments and user-facing words are plain language for people who do not program, per
  `AGENTS.md`: no jargon, no emoji, no em dash.

I did not restart the server, did not run `git`, and did not edit any file other than
`web/feat/peek.js` and this report.
