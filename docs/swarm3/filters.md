# filters

Status pills with live counts and a search box for the list of videos.

- File owned: `peakcut/web/feat/filters.js` (only file I wrote in the app).
- Skill loaded before writing code: `ui-design-guide`.
- Endpoint used: none. Everything reads `PeakCut.state().jobs`, which the page already polls.

## Where the bar lives, and why there

`playLibrary` (`peakcut/web/index.html:1381`) sets `#view` to `<div id="add"></div><div id="jobs"></div>`, so the
element that holds `#jobs` is `#view`. My bar is inserted into `#view` as its own child, immediately before
`#jobs`, and never inside `#jobs`. That matters because `drawJobs()` (`peakcut/web/index.html:1897-1901`) writes
its empty state straight into `#jobs` with `root.innerHTML = ...`, which would destroy anything living in there.
A sibling above the list survives, and the section cards `drawJobs` rewrites are untouched.

It is inserted directly before `#jobs` rather than as the first child of the holder, so on All videos it heads the
list itself and sits below the paste-a-link box (`#add`) instead of above it.

The creator page has a second `#jobs`: `setTab("clips")` (`peakcut/web/index.html:1397`) builds
`<div id="live"></div><div id="add"></div><div id="jobs"></div>` inside `#cbody`. Because the bar is created per
holder (found with `:scope > .pcf-bar`) rather than once globally, that page gets its own bar above its own list,
and the two never fight over one element.

## What it does

- **Pills.** All / Making / Ready / Failed, each with a count taken from `PeakCut.state().jobs`. Making is `queued`
  or `running`, Ready is `done`, Failed is `error`. Any other status (a live recording, for instance) is counted in
  All only, since it is none of the three. The choice is held in a module variable `mode` and survives every
  redraw, because each `apply()` rebuilds the pill state from `mode` instead of from the DOM.
- **Search.** `<input type="search">`, matched case-insensitively against the job title, the source name, and the
  title and hook of every clip on that video. Two listeners (`input` and `search`) plus Escape to clear.
- **Filtering without fighting the page.** I never rewrite a card. `apply()` reads the live `section[data-job]`
  elements, works out which ids should show, and sets `data-pcfilter="out"` (styled `display:none!important`) on the
  rest. `drawJobs` keeps drawing whatever it wants; the attribute is re-applied after every draw and on every
  keystroke. Attributes, not classes, so a card whose `className` is reset by the page cannot lose my marker.
- **Empty state.** While a filter is active and hides everything, the page's own "No videos yet" block inside
  `#jobs` gets the same `data-pcfilter="out"` and my line "Nothing matches that." appears below the list. Both are
  undone the moment the filter is cleared or something matches again. If the page drew no cards at all, its own
  wording is already correct and mine stays away.
- **Counts on creator pages.** `listed()` mirrors `drawJobs`: when `state.view` starts with `c:`, only that
  creator's videos are counted, so the numbers agree with the list underneath them. It also mirrors the one other
  thing `drawJobs` does: when a `#live` box is on the page, a job whose status is `live` is drawn up there instead of
  in the list, so it is left out of the counts as well. Otherwise the numbers and the cards would disagree by one.
- **Quiet.** Every write is guarded by a comparison, so a second pass with the same numbers touches nothing and the
  page's per-frame repaint loop does no work.

## One-row layout on a phone

`.pcf-bar` is `display:flex; flex-wrap:wrap; gap:8px`. The pill row wraps, and the search box is `flex:1 1 180px`.
Below 560px the search box takes `flex-basis:100%`, so it drops to a second line instead of squeezing the pills.
Nothing is ever clipped or scrolled sideways.

Styling uses only the existing tokens (`--brand`, `--brand-soft`, `--brand-line`, `--brand-ink`, `--brand-deep`,
`--line`, `--muted`, `--dim`, `--faint`, `--r`), keeps the page's no-shadow rule, and puts a hover state that only
changes colour. The pills are real `<button type="button">` elements carrying `aria-pressed`, inside a labelled
group, so they are keyboard reachable and announce their state; the search input has an `aria-label`.

## Verification

```
$ cd peakcut && node --check web/feat/filters.js && echo "JS OK"
JS OK

$ curl -s http://127.0.0.1:8798/assets/feat
{"files":["filters.js","grid.js","heard.js","stage.js"]}

$ curl -s -o /dev/null -w "%{http_code} %{size_download}\n" http://127.0.0.1:8798/assets/feat/filters.js
200 9986
```

The server picks the file up from `web/feat/` with no other change, and `/assets/feat` lists it, which is what
`plugins.js` uses to load it.

The real job list, straight from the live server:

```
$ curl -s http://127.0.0.1:8798/api/jobs | head -c 200
[{"id":"20261119-171742-d88fe196d1","kind":"video","creator":null,"created":1795088862.0077834,
  "source":{"kind":"file","name":"demo.mp4"},"options":{"max_clips":1,"min_len":5,"max_len":12,"style":"bou
```

There is exactly one job: `demo.mp4`, status `done`, creator `null`, one clip whose keys include `title` and `hook`.
So on this instance the bar should read All 1, Making 0, Ready 1, Failed 0, and searching "demo" should keep the
card while searching anything else should hide it and show my line. The other two pills cannot be exercised against
this data because no job is queued, running or errored; the bucket mapping is exercised through the same code path
but its non-empty case is reasoned, not observed.

I have no browser tools in this session, so I did not click anything. Verification here is `node --check`, the
served-file check, and a read of `drawJobs`, `jobHtml`, `clipHtml`, `setTab` and `playLibrary` to confirm the
hook, the holder and the field names `title`, `source.name`, `status`, `clips[].title`, `clips[].hook` all match
what the page actually writes.

## Needs from files I do not own

none.
