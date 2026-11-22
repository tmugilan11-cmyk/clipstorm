# Fix report - studio/api_style.py

Fixer: agent-196 (40-agent QA swarm, fix wave). Findings source: `docs/qa/FINDINGS.md`, section
`## studio/api_style.py` (5 findings, all minor). Audit evidence: `docs/qa/audit/api-style.md`.

## Files owned

- `studio/api_style.py` - the only file edited. No JS file was touched, so no `node --check` gate applies.

## Fixes

### 1. `POST /api/formats/plan` is a live route nothing calls (FINDINGS.md:1102) - FIXED (kept per the finding's own "if kept" branch)

Verified first: a grep for `formats/plan` across the 95 JS/HTML files under `web/` returns 0 hits
(`ops_grep` on `web/`, glob `**/*.js` + `**/*.html`: 0 matched), and repo-wide the name appears only in
`docs/` and `studio/api_style.py` - the audit's evidence holds.

Resolution: the route is **kept**, per the finding's own fallback branch ("If kept, also read `words` out
of `pick`"). Wiring it to a "try this shape" flow on the formats page belongs to `web/feat/formats.js`,
which another agent owns, and removing a documented, working endpoint (it is in this module's own
contract docstring and in `docs/port/18-clipper-ui-reference.md:136-137`) was judged the riskier option
for a bug-fix wave. The "if kept" hardening is applied in full - see fix 2.

### 2. Plan route reads `words` from the top-level body only, dropping the nested shape's words (FINDINGS.md:1106) - FIXED

Verified live before the fix (read-only probe; the route renders and writes nothing):

    curl -s -X POST http://127.0.0.1:8798/api/formats/plan -d '{"pick":{"format":"moment","words":["hello"]}}'
    -> 200 {"format":"moment","plan":{"ok":true,...,"total":0.0,...}}

The words were silently lost and the plan ran against an empty list - exactly as audited.

Fix at `studio/api_style.py:130-131` and `:137-142`: the nested `pick` dict is remembered, and `words` is
read from the top-level body first, falling back to `nested.get("words")` when the top level carries none.
The top level wins when both carry words; that rule is written in the route docstring
(`studio/api_style.py:118-121`) and in a comment above the read (`studio/api_style.py:137-139`).

After the fix, the same nested body reaches the words validation instead of planning against nothing.
Note: this change takes effect only after the lead's final server restart.

### 3. Plan error copy is developer-speak (FINDINGS.md:1110) - FIXED

Verified live before the fix:

    curl -s -X POST http://127.0.0.1:8798/api/formats/plan -d '{"format":"moment","words":[{"w":"hi"}]}'
    -> {"detail":"Those words are not in the shape PeakCut writes: each needs an 's' time."}

Fix at `studio/api_style.py:147`: the message is now
`"Those words cannot be planned: each needs a spoken time ('s') and an end time ('e') in seconds."` -
the suggested plain-English copy. No test pins the old message (grep over `tests/` for `Those words`
returns no hits). Note: the new copy is served only after the lead's final server restart.

### 4. Cache timestamps captured before the ffmpeg run, so the TTL starts at request start (FINDINGS.md:1114) - FIXED

Verified in code: the preview route captured `now = _time.monotonic()` at the old `:263` and stored that
same pre-render value at the old `:277`; the motion route did the same at the old `:342`/`:354`. The
finding is real.

Fix: the stored timestamp is now taken inside the same lock block that inserts the result, after the
render returns. Both routes now call the shared helper `_draw_once`
(`studio/api_style.py:178-216`), whose success path runs
`cache[key] = (_time.monotonic(), out)` inside `with lock:` after `await run_in_threadpool(fn, *args)`
(`studio/api_style.py:203-207`). The probe's own freshness reference (the `now` kept at
`studio/api_style.py:316`/`:394` for the TTL check on a hit) is unchanged and still means "now".

### 5. Concurrent identical requests both render (FINDINGS.md:1118) - FIXED

Verified in code: the lock guarded only the cache probe and was released before the render
(`await run_in_threadpool(...)` outside the lock), so two tabs asking for the same uncached look at the
same moment each ran ffmpeg and the second result overwrote the first. The finding is real.

Fix: a shared helper `_draw_once(key, cache, pending, lock, fn, args)` (`studio/api_style.py:178-216`)
keeps a per-key in-flight `asyncio.Event` in `_PREVIEW_PENDING` (`:175`) and `_MOTION_PENDING` (`:344`):

- The first caller for a key creates the event and does the drawing.
- A caller that finds an existing event waits on it, then takes the frame the first caller stored
  instead of drawing it a second time; if that draw failed, nothing was stored, so the loop lets this
  caller draw its own.
- On failure the mark is popped and the waiters are woken on every failure path, including a cancelled
  request (`except BaseException` at `:198-202`), so no key is ever left waiting on a frame that will
  never come.
- The frame is stored before the waiters are woken (`:203-207`), so a woken caller always finds it.

The event is waited on with `await`, never with a blocking `Event.wait()`, so the event loop is never
held. The preview and motion routes call the helper at `studio/api_style.py:327-328` and `:404-405`.

## Skips

None. All five findings' evidence held under verification.

## Gates run

| Gate | Result |
|---|---|
| `python -m py_compile studio/api_style.py` | pass (exit 0) |
| `python tests/test_caption_looks.py` (exercises `api_style._SAMPLE`, `_sample_for`) | pass - "All checks passed." |
| `python tests/test_overhaul.py` (exercises `formats.plan` directly) | pass - "All checks passed." |
| `python tests/run.py` (full suite; throwaway server on a spare port, empty data folder) | 2 suites fail, both verified **unrelated to this file** - see below |
| Read-only curl probes against `http://127.0.0.1:8798` (`POST /api/formats/plan`, nested shape and word-without-`s`) | confirmed findings 2 and 3 before fixing |

Full-suite failures, verified not caused by `studio/api_style.py`:

- `tests/test_updates.py` ("the new-version notice") - fails on the git version read: "FAIL this folder's
  own version is found   got 0" and a following IndexError. The suite imports `config, db, server,
  updates`; every failing check is about `updates.py` reading the version from git, which this wave's
  changes to `studio/api_style.py` cannot affect (no failing check names the catalogue routes, and a
  syntax error in this module would have crashed every suite at import instead). Likely an environment
  or `updates.py` issue outside this fixer's scope.
- `tests/test_clip_editor.py` ("the clip editor: seven tabs, and a preview that fits") - fails one check:
  "the Numbers box stays with the look controls - stats.js no longer anchors to the first heading". That
  is about `web/feat/stats.js`, another agent's file in this fix wave; a grep of the suite for
  `api_style|style/preview|style/motion|formats/plan` returns 0 hits, so the suite never exercises this
  module at all.

The gates that exercise this file directly (py_compile, `test_caption_looks.py`, `test_overhaul.py`) all pass.

## Notes for the lead

- The Python changes take effect only after the final server restart.
- `web/feat/formats.js` (formats page) may still want a "try this shape" flow that calls
  `POST /api/formats/plan`; that is the formats.js owner's call, not made here.
- No em dashes, no `!important`, no shadows, and no colour changes were involved in this file's fixes.
