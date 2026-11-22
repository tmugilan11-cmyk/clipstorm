# analytics-empty

**Skill loaded.** `frontend-design`, before any reading.

**The file.** `web/feat/analytics-empty.js`, new, 126 lines, 6,821 bytes. It registers exactly one
plug-in, `PeakCut.add("analytics-empty", ...)`, adds its CSS through `PeakCut.css` under the same
name, and nothing else was edited. I did not touch `web/index.html`, `analytics.js`, or any other
agent's file.

## What it does

Every box on Insights is filled by a different file, and each one answers an empty box in its own
way: a grid of dashes, a sentence of its own, or nothing at all. This file watches the four boxes
and, when one is still empty after the others have had their turn, adds one line to it: what is
missing, and one link to the page that connects a channel.

The line it adds:

```html
<p class="an-empty" data-an-empty="1">
  <span><b>No videos are listed.</b> Nothing came back for this range.</span>
  <a href="/app/apps" data-act="go" data-v="apps"><span>Connect a channel</span> <arrowr svg></a>
</p>
```

`data-act="go" data-v="apps"` is what the page's own click handler looks for, so the link moves to
the Connected apps page without reloading the tab. `href="/app/apps"` is there for a real click
with the keyboard, a middle click, or a copy of the address.

**What is missing, in the words of the box it went missing from.** The sentence is chosen by the box
id and, for the shared body box, by the tab the page says is showing:

| box | when it is empty | the line |
|---|---|---|
| `#an_kpi` | summary did not arrive | No key numbers yet. The analytics answer for this range did not arrive. |
| `#an_charts` | no series | The charts are empty. No daily views or watch time arrived for this range. |
| `#an_table` | no rows | No videos are listed. Nothing came back for this range. |
| `#an_body`, audience | no audience answer | The audience is missing. Viewer types, countries and hours come from YouTube, and none of them arrived for this range. |
| `#an_body`, traffic | no traffic answer | Traffic sources are missing. The searches and pages that sent these views come from YouTube, and none of them arrived for this range. |
| `#an_body`, anything else | nothing yet | Nothing to show yet. No answer arrived for this range. |

No numbers appear anywhere in that text, because the rule is that a number the server did not send
is a dash and a sentence, and a dash is exactly what was already on the screen.

## The four rules, and how each one is kept

- **Empty means empty, not almost empty.** `EMPTY = /^[\s.,:;\/\\|()\-_\u2010-\u2015\u2212]*$/`. A box
  holding spaces, punctuation, or a single dash is empty. A box holding one real word is not, so a
  box that says "No views in this range yet." or carries a note is left alone. Invisible characters
  (zero width space, byte order mark) are stripped before the test, so markup that looks empty on
  screen counts as empty here.
- **Never overwrite.** The only write is `insertAdjacentHTML("beforeend", ...)`, which adds one node
  and touches nothing already in the box. Nothing in this file sets `innerHTML`. When the box later
  fills with real content, the line removes itself: the next look sees other words beside its own
  paragraph and takes the paragraph out again.
- **Never twice on the same box.** The box is marked `data-anEmpty="1"` when the line goes in, and a
  box that already holds an `.an-empty` returns immediately, so a box can only ever hold one line.
  If the mark is found without its line (the box was cleared from elsewhere) the mark is dropped, so
  a fresh line can be added later.
- **Only on a box somebody can see.** A box inside a `[data-an-panel]` that is `hidden` is skipped,
  because the tab is not showing; the tab switch asks again. `#an_table` and `#an_body` live in
  panels that are hidden on the Overview tab, which is the correct state for them there.

## Why it waits before deciding a box is empty

A box is often empty for a moment while its request is still out. A line saying "nothing arrived"
over a number that is on its way is worse than no line at all, so a box must stay empty for
`WAIT = 1300` ms before the line is written. The first look records the time in a `Map`; a later look
only writes once that time has passed. A box that fills in the meantime is forgotten, not described.

## A bug found and fixed

The first version used the usual debounce:

```js
function ping() { clearTimeout(later); later = setTimeout(scan, 220); }
```

The Insights page repaints constantly, and each repaint fires the MutationObserver, so every call
pushed the timer back and the scan never ran. The symptom in the browser: after clearing `#an_table`
the box stayed empty, with `lines: 0` and `ds: {}`, across repeated renders; calling
`window.PeakCut["analytics-empty"].load()` and waiting also showed nothing. (The probe call even hit
the 30 s tool timeout waiting for an answer that never came.)

The fix is a single-flight scheduler: one scan is queued at a time, and a later change does not
postpone it.

```js
let queued = 0;
function schedule(ms) {
  if (queued) return;
  queued = setTimeout(() => { queued = 0; scan(); }, ms);
}
function ping() { schedule(220); }
```

`scan()` queues one more look after `WAIT` when any box is still settling, which is how the delayed
lines get written.

## Ways in

Four, all collapsing into the one scheduler: `peakcut:render` on `document`, a MutationObserver on
`#view`, `DOMContentLoaded` (or immediately if the page is already parsed), and the plug-in's own
`load()`, which the shell calls on every range and tab change.

## Gates, and the literal output

```
$ node --check web/feat/analytics-empty.js
(no output, exit 0)
```

```
$ python tests/test_feat_files.py | grep -E "analytics-empty|^\{|All checks"
ok   analytics-empty.js parses
ok   analytics-empty.js declares one plug-in
ok   analytics-empty.js is named after itself
ok   analytics-empty.js is the only owner of analytics-empty
ok   analytics-empty.js does not write into index.html
ok   analytics-empty.js draws only fixed markup
ok   analytics-empty.js uses no absolute origin
ok   analytics-empty.js invents no clashing id
{"files": 37, "checks": 302}
All checks passed.
```

```
$ python tests/test_menu_pages.py | tail -3
ok   menu-pages.js draws its page

All checks passed. 142 ok
```

```
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/assets/feat/analytics-empty.js
200
```

The file also appears in `GET /assets/feat`, so the loader picks it up with no change anywhere else.

## What the live page showed

Checked in the shared browser against `http://127.0.0.1:8798/app/analytics`.

- **It is loaded.** `PeakCut._order` contains `analytics-empty`, and `PeakCut["analytics-empty"]` has
  keys `["label","load"]`.
- **With this account, the four boxes are not empty**, so nothing is added and the page looks exactly
  as it did before this file existed. `#an_kpi` is a grid of six `–` cells plus a note that already
  links to Connected apps; `#an_charts` says "No views in this range yet."; `#an_table` says "No
  videos in this range yet. Publish a clip, ..."; `#an_body` on Audience carries the audience note
  and three sections. Every one of them is a box with a sentence, so the rule "never overwrite a box
  that has real content" keeps the line out. That is the right outcome, and it is the case a reader
  will see most of the time.
- **A dash-only box gets the line.** `#an_kpi` emptied to a single `–` and left alone for 3.6 s
  without any render:

  ```
  lines: 1, ds: {sig: "/api/analytics/summary?...", anEmpty: "1"}
  text: "–No key numbers yet. The analytics answer for this range did not arrive.Connect a channel"
  href: "/app/apps"
  ```

- **A wholly empty box gets the line, in each of the three other boxes.** `#an_charts` blanked:

  ```
  lines: 1, ds: {anEmpty: "1"}
  text: "The charts are empty. No daily views or watch time arrived for this range.Connect a channel"
  href: "http://127.0.0.1:8798/app/apps"
  ```

  `#an_table` blanked, with the table's own empty frame left in place so it does not remount over the
  top: `lines: 1`, `text: "No videos are listed. Nothing came back for this range.Connect a channel"`.

  `#an_body` blanked on the Audience tab: `lines: 1`, `text: "The audience is missing. Viewer types,
  countries and hours come from YouTube, and none of them arrived for this range.Connect a channel"`.

- **The markup is exactly the one written above**, read back out of the page:

  ```html
  <p class="an-empty" data-an-empty="1"><span><b>The charts are empty.</b> No daily views or watch
  time arrived for this range.</span><a href="/app/apps" data-act="go" data-v="apps"><span>Connect a
  channel</span><svg viewBox="0 0 256 256" aria-hidden="true"><path d="M221.66,133.66l-72,72a8,8,0,
  0,1-11.32-11.32L196.69,136H40a8,8,0,0,1,0-16H196.69L138.34,61.66a8,8,0,0,1,11.32-11.32l72,72A8,
  8,0,0,1,221.66,133.66Z"></path></svg></a></p>
  ```

  The icon is `arrowr`, a real name from the set in `index.html`.

- **Never twice.** Three more `peakcut:render` events, then 2.2 s: `linesBefore: 1`, `linesAfter: 1`,
  `sameNode: true`, `totalOnPage: 1`. The same paragraph, not a second one.
- **Never overwrite, live.** A real `.ac-wrap` block of views put into `#an_charts` beside the line:
  after 2 s, `lines: 0`, `ds: {}`, `text: "Views 12,480"`, and the block still there. The line
  stepped out of the way on its own.
- **The link goes where it says.** Clicking the line's own anchor moved the tab to `/app/apps`, where
  the page reads "Connected apps / The accounts PeakCut posts your clips to." It worked from
  `#an_table` and from `#an_body` alike, without a reload of the app shell.
- **Nothing is left behind.** After a reload, all four boxes report `lines: 0` and only the data
  attributes of their own fillers remain (`sig`, `antBound`); `total: 0` for `.an-empty` on the page.
  No console errors: `dsh_browser_console` reports nothing logged.

## What I could not do

- **The boxes on this machine are never truly empty**, because every other analytics file already
  gives its empty case a sentence. So the three "empty box" checks above were made by blanking the
  box from the browser, not by catching the server in that state. The code path is the same either
  way, and the blanking was undone by a reload.
- **I could not make the server send an empty answer.** With no YouTube channel connected it already
  answers with the PeakCut fallback plus a note, which is not empty. I did not edit `api_analytics.py`
  to force a different answer, since the box fills come from files and routes other agents own.
- I did not test a second browser. The file uses nothing beyond `MutationObserver`, `Map`, template
  strings and `insertAdjacentHTML`, and all four have a guard or a fallback.
