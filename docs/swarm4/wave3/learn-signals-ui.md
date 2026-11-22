# learn-signals-ui

## What I built

`web/feat/learn-signals.js`: a card on the Improve page that draws the retention curve and the two
sentences the server makes from it.

- Registers with `PeakCut.add("learn-signals", {...})` and draws through the `after.drawSettings` hook,
  the hook the loader already runs against a page after its own `load` finishes (`web/plugins.js:112-137`).
- Finds the Improve page by its own `.lrn` container. When that container is not on screen it returns
  quietly, the way `web/feat/heard.js:62` skips a job card that is not there.
- The card is a `.box` (the Improve page's existing card class) holding an `<h3>` and one of four states:

| Server answer | What the card shows |
|---|---|
| points and sentences | inline SVG sparkline of kept over at, plus "Hook: ..." and "Length: ..." |
| sentences sent as a list | the same sparkline, then each sentence unlabelled in server order |
| points but no sentence keys | the sparkline alone, and nothing that was not sent |
| no points | one sentence: "A curve appears here once a clip from the last N days has watching numbers." |
| the request failed | one sentence in the card, no console line, the rest of the page untouched |

- Reads `GET /api/learn/signals?days=N` through `PeakCut.api`. `N` comes from the page's own
  `#lrn_days` select, defaulting to 28 when the select is missing. A `change` on that select refetches.
- The sparkline is one plain `<polyline>` plus a baseline `<line>`, no library, `viewBox="0 0 100 36"`,
  `width:100%` in CSS so it follows the card. `vector-effect="non-scaling-stroke"` keeps the stroke from
  being stretched by the non-uniform viewBox. A single point is drawn as one circle instead of a
  zero length line, because a polyline of one point draws nothing.
- Styling is the existing palette variables only (`var(--brand)`, `var(--line)`, `var(--ink)`,
  `var(--bad)` through the existing `.err` class) and one `P.css("learn-signals", ...)` block.

Nothing is invented: the only sentences written by this file are the empty-state line and the failure
line, and neither quotes a number. Every other word on the card came from the server or from the
static headings.

### Decisions worth knowing

- **The point array is found by `Array.isArray`, not by the first truthy value.** The wave 3 backend
  report (`docs/swarm4/wave3/retention-signals.md:23-26`) says `signals()` returns `points` as a
  **count** while `curve()` returns the array. Looking for `body.points` first would have hidden a
  perfectly good `curve` array behind the integer. The reader now takes the first array among
  `points`, `curve`, `series`, `retention`.
- **Kept may be a fraction or a percentage.** 100-based curves and 1-based curves share a shape, so the
  largest value picks the scale once instead of six separate guesses. A value that is not a number is
  dropped, never defaulted to 0.
- **`at` and `kept` are the names the backend already emits**, so a point that carries them plots
  unchanged. Other names are accepted as fallbacks, nothing is required.
- **A list of sentences is shown unlabelled.** If the server sends `lines` in reading order (hook, drop,
  length) rather than named keys, labelling the first one "Hook" would put a label on a sentence that
  may not be one. Unlabelled in server order is the honest reading.
- **The page redraws itself** when a round starts, which throws the card away. A `MutationObserver` on
  `#view` puts it back. It is guarded in `try/catch` and checks for `.lrn` first, so it can never run on
  another page. No timer is used.

## The file I own

`web/feat/learn-signals.js`. No other file was edited. `web/index.html` was not touched.

## The exact command and its output

```
$ cd peakcut && node --check web/feat/learn-signals.js && echo "JS OK"
JS OK
```

```
$ cd peakcut && python tests/test_feat_files.py 2>&1 | tail -3
ok   loader keeps the documented folder
{"files": 39, "checks": 318}
All checks passed.
```

The lines for this file specifically:

```
$ cd peakcut && python tests/test_feat_files.py 2>&1 | grep learn-signals
ok   learn-signals.js parses
ok   learn-signals.js declares one plug-in
ok   learn-signals.js is named after itself
ok   learn-signals.js is the only owner of learn-signals
ok   learn-signals.js does not write into index.html
ok   learn-signals.js draws only fixed markup
ok   learn-signals.js uses no absolute origin
ok   learn-signals.js invents no clashing id
```

The live check, on the test server the contract names:

```
$ python - <<'PY'  (asks http://127.0.0.1:8798/assets/feat for the served list)
served: 38 files
learn-signals served: True
```

Behaviour check, run in node against a stub DOM, since there is no real curve in this install:

```
POLYLINE: true
VIEWBOX: true
HOOK: true
LENGTH: true
NO NAN: true
TEXT: Where people stop watching Kept watching over the clip, last 28 days. Hook: At 5 percent in, 68 percent are still watchi
EMPTY: Where people stop watching A curve appears here once a clip from the last 28 days has watching numbers.
FAILED: Where people stop watching The retention curve could not be read just now.
ABSENT PAGE: returned quietly, no throw
90 DAYS RANGE: Where people stop watching Kept watching over the clip, last 90 days.
```

The point array in that probe is synthetic and only proves the drawing, not a measurement.

## What I could not do

- **`GET /api/learn/signals` does not exist yet.** `studio/api_learn.py` still has three routes
  (`state`, `run`, `undo`), and a repository search for `api/learn/signals` returned nothing. The card
  therefore always shows its failure sentence on this install. The route belongs to the wire owner in
  this wave; the brief forbids me touching `studio/api_learn.py`.
- Because of that, I could not see the real payload. The reader accepts the shapes the backend report
  documents (`points`/`at`/`kept`, `hook`, `length`, `lines`) and tolerates a wrapper key
  (`{"signals": {...}}`), but a route that answers with something else will draw the empty sentence.
- I did not load `/app` in a browser. No browser tool is available in this slot. The mount path is
  proved by the stub DOM run above and by reading how `web/plugins.js:112-137` invokes `drawSettings`
  after a page's own `load`, not by a real page render.
- I did not run `python tests/run.py`. It starts a server, and this file is not imported by Python, so
  the suite cannot see it.

## For the reviewer

- `learn.js` draws `#lrn_days` only when a round is not in progress. While one runs, the select is not
  in the DOM, so `daysOf` falls back to 28. That is the same default the page itself uses
  (`web/feat/learn.js:183`), so the card and the page agree.
- `paint` reuses a `.lsig` it already made, so the observer and the hook can both fire without the card
  appearing twice.
- `esc()` is applied to every value that reaches markup, including the two constants, because the empty
  line carries a day count taken from the page.
- A failure shows the same sentence for every cause. The brief asks for one short line, and the route's
  own error text would put a server string on the page.
