# review-hooks (wave 6, agent-120)

## Result: done

Created `web/feat/review-hooks.js`. Skill loaded: make-interfaces-feel-better.

## What it does

- On the Review page (`#rvroot` exists) it adds a small pill to each review card: `Hook 85`
  (or `Hook 4.5` when the score is not a whole number), matched by job + clip id.
- Scores are fetched ONCE per page load from `GET /api/learn/hooks`.
- A clip with no score gets no pill. No dashes, no zeros, no invented values.
- If the fetch fails, one quiet line is drawn under the list:
  "Hook scores could not be loaded: ..." with the server string passed through `esc()`.
- Handlers live in `PeakCut.add`. The framework has no review-page hook name, so the file
  uses the `after: { drawShell: onShell }` hook (`.topbar` changes when the review view
  opens, same approach as `web/feat/keys.js`) plus a MutationObserver on `#view` so each
  redraw of the review list is decorated again. Nothing outside my file was touched.

## Evidence (commands and output)

- `node --check web/feat/review-hooks.js` -> `JS OK`
- `python tests/test_feat_files.py` -> `{"files": 64, "checks": 518}` then
  `All checks passed.`
- `curl http://127.0.0.1:8798/assets/feat` -> `review-hooks.js served: True`,
  `total served: 64`
- Browser on `http://127.0.0.1:8798/app`: `PeakCut._order.includes("review-hooks")`
  -> `true` (order length 64). Plugin is registered and loaded on the live page.
- Live server, real endpoint: entering Review with the endpoint still 404 gave
  `cards: 1, pills: 0` plus the quiet failure line. Correct: no data, no pill.
- Render path proven with a clearly labeled in-page test stub (fetch stubbed for
  `/api/learn/hooks` only, returning `[{"job":"20261120-003159-e8505dbf42",
  "clip":"clip01","score":85}]`, the card's real ids): result
  `hookCalls: 1, cards: 1, pills: 1, pillText: "Hook 85"`. The pill renders, matches by
  job+clip id, and fetches once.

## What is not known yet

- `GET /api/learn/hooks` is still `404 {"detail":"Not Found"}` on the test server. The
  backend slot that owns it has not landed. Until then the page honestly shows no pills.
- Response shape is not specified anywhere I could find. My `normalize()` accepts a list
  of `{job, clip, score}` entries (also `job_id/jid`, `clip_id/cid`, `value`) and a nested
  map `{job: {clip: score}}`. Non-finite numbers are dropped. If the backend chooses a
  different shape, this one function is the only place to touch.

## Router line

None needed for this file. The `/api/learn/hooks` route belongs to the backend slot;
its one-line import/include is that slot's job, not mine.
