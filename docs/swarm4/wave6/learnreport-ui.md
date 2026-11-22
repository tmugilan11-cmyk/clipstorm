# learnreport-ui: The full report card

## What I added

`web/feat/learn-report.js` (the one file I own). It appends one disclosure card to the end of the
Improve page (`.lrn` root), titled "The full report". Opening it the first time asks
`GET /api/learn/report` once and shows the answer as plain text in a `pre` block (monospace,
pre-wrap, 320px scroll cap). Every server string goes through `esc()`. A failed read shows one
sentence and the next open asks again, so a route that lands later starts working with no reload.
An empty report is not hidden: the card says "No report is saved yet. Run a learning round and its
report will be written here." An answer with no text field at all gets its own honest sentence, so
"empty" is never claimed when the shape simply did not match.

Design note: plugins.js calls `e.preventDefault()` on every `[data-act]` click it dispatches, which
would kill a native `<summary>` toggle. So the disclosure is a real `<button>` with
`data-act="lrepopen"` and `aria-expanded`, handled in `PeakCut.add(...).act`, per the rule that
handlers live in `PeakCut.add`. Mount uses the same proven pattern as `learn-signals.js`:
`after.drawSettings` plus a `MutationObserver` on `#view`, so the card survives page redraws. The
fetch fires only on first open, never on mount.

## Gates (commands and output)

- `node --check web/feat/learn-report.js` -> `JS OK`
- `python tests/test_feat_files.py` -> `{"files": 63, "checks": 510}` then `All checks passed.`
  (learn-report.js rows: parses, one plug-in named after itself, only owner, no index.html writes,
  escapes what it draws, no absolute origin, no clashing id)

## Live proof (test server on 127.0.0.1:8798)

- `GET /assets/feat` -> `served count: 64`, `learn-report.js served: True`
- Browser at `/app`: `window.PeakCut._order` contains `learn-report` (orderLength 64).
- Improve page: card mounts as the last box, header "The full report", `aria-expanded="false"`.
- First open against today's server (route not live yet, 404): body shows exactly one line,
  "The report could not be read just now (Not Found)." Screenshot:
  `docs/swarm4/wave6/learn-report-live.png`.
- Empty-report path (P.api stubbed in the tab, `{"report": ""}`): the honest note shows, visible.
- Text path (stubbed `{"text": "... <img src=x onerror=alert(1)>"}`): text shows in the pre block
  with the newline kept (`white-space: pre-wrap`) and no `img` element was injected, so `esc()`
  held. The stub died with the page reload; the server was never touched.

## Not known yet

The exact response shape of `GET /api/learn/report`: the route does not exist on the live server
today (`curl http://127.0.0.1:8798/api/learn/report` -> `{"detail":"Not Found"}`, status 404,
measured during this run, 2026-11-20 18:59 local). The card reads,
in order: a plain string, or an object with one of `report`, `text`, `body`, `content`, `saying`,
`said` as a non-empty string, or any of those keys as an all-string array (joined with newlines).
If the backend returns another shape, the card says "The report arrived without plain text this
card can show." rather than pretending the report is empty.

## Still missing

- The `GET /api/learn/report` route itself. It is a backend slot's file, not mine. No UI change is
  needed once it lands; the card retries on the next open.
- Nothing else. The card writes nothing, changes no setting, invents no number.

## Needs from files I do not own

None.
