# Fix - studio/api_trends.py

Fixer: agent-197 (40-agent fix wave). Date: 2026-11-22.
Binding rules: docs/qa/CONTRACT.md. Findings read from docs/qa/FINDINGS.md, section
"## studio/api_trends.py" (3 findings, all minor). Full source evidence:
docs/qa/audit/api-analytics.md. No browser was used; no subagents were dispatched;
the running server was only curled read-only.

## Files owned

- studio/api_trends.py - the only file written. It is 390 lines now (was 381).
- No other file was read for writing; web/index.html untouched; the server was not
  killed or restarted.

## Fix 1 - [minor] studio/api_trends.py:78, 195, 223, 273, 324, 332, 368

**What the finding said:** trends routes spend the rate limit on every request,
including cache hits - the exact thing studio/api_analytics.py:81-101 says must not
happen ("Asking for a number we already hold costs nothing, so it must count for
nothing"). Suggested fix: pass uid into trends `_cached` and throttle only on a cache
miss, as analytics does.

**Evidence verified before fixing (real):** every trends route called `_throttle(u.id)`
at the top, before the cache was probed, and trends `_cached(key, build)` took no uid
and never throttled. The sibling studio/api_analytics.py:81-101 does the opposite: its
`_cached(key, build, uid)` probes the cache first and throttles only when the answer
has to be rebuilt. auth.throttle counts requests in a sliding window
(studio/auth.py:57-69), so the difference was real: with the old code, 121 reads of a
cached trends route inside a minute answered 429 even though 120 of them were served
from the cache.

**Fix applied (same shape as analytics):**

- `_cached(key, build, uid="", limit=120)` now probes the cache first and calls
  `_throttle(uid, limit=limit)` only on a cache miss. Its docstring explains the
  change in plain words.
- `GET /api/trends/status` passes `u.id` and keeps its more generous limit:
  `_cached(f"trend_status:{u.id}:{bool(token)}", build, u.id, limit=240)` (was
  `_throttle(u.id, limit=240)` at the top).
- `GET /api/trends/searches` and `GET /api/trends/videos` pass `u.id`
  (default limit 120, as before).
- `GET /api/trends/saved`, `POST /api/trends/saved` and `DELETE /api/trends/saved`
  keep their top-of-route `_throttle(u.id)`: these three routes have no cache at all,
  so every request does real work (a file read or write) and spending the limit on
  each one is protection, not waste. The finding's fix is about the cached reads.

**Proof:**

- `python -m py_compile studio/api_trends.py` - OK.
- Behaviour, measured with a throwaway TestClient script kept outside the repo
  (removed afterwards): 150 rapid `GET /api/trends/searches?days=28` calls all
  answered 200, no 429. Before the fix, call 121 was told to wait (limit 120/60);
  after the fix a cache hit counts for nothing and the budget is only spent when the
  answer is rebuilt.
- `python tests/test_trends_api.py` - All checks passed. 8 ok.

## Fix 2 - [minor] studio/api_trends.py:198-213

**What the finding said:** `GET /api/trends/status` omits the `source` key its sibling
analytics status sends; a consumer keying on source gets nothing. Suggested fix: add
"source" to the trends status answer.

**Evidence verified before fixing (real):** every `build()` return in the status route
carried only `{"connected": ..., "note": ...}`, while studio/api_analytics.py:149-173
sends `source` on every path, and the trends `searches` route itself carries `source`
("peakcut" when nothing comes from YouTube, "youtube" when it does).

**Fix applied:** every `build()` return in the status route now carries `source`,
matching both siblings:

- no token: `"source": "peakcut"`
- connected but missing the analytics permission (no scope): `"source": "peakcut"`
  (the terms will not come from YouTube)
- connected, transient failure: `"source": "youtube"` (the same value the searches
  route sets on its failure path, and the same call the analytics sibling makes for a
  transient failure)
- connected, probe OK: `"source": "youtube"`

A plain-English comment at the top of `build()` names the rule.

**Proof:**

- Behaviour, same throwaway script: `GET /api/trends/status` answers 200 and the body
  carries `"source": "peakcut"` with no connection.
- `python tests/test_trends_api.py` - All checks passed. 8 ok (including the two
  status-route checks: every route answers, and the no-connection note).

## Fix 3 - [minor] studio/api_trends.py:334-342

**What the finding said:** a body that cannot be read as JSON is answered "Type a
search term first, then save it." - the person did send something; the message never
says the body was unreadable. Suggested fix: when `request.json()` raises, answer
"That body could not be read as JSON. Send a JSON object, like {\"term\": \"...\"}."

**Evidence verified before fixing (real):** `body = await request.json()` sat in a try
whose `except` folded the failure into `body = {}`, so a non-JSON body (text/plain,
truncated JSON, an empty body) reached the blank-term branch and was told to type a
search term.

**Fix applied:** when `request.json()` raises, the route now answers 400 "That body
could not be read as JSON. Send a JSON object, like {\"term\": \"...\"}." A body that
parses but is not an object keeps its existing refusal ("Send a JSON object, like
{\"term\": \"how to clip a stream\"}."), and a JSON object with no term keeps "Type a
search term first, then save it."

**Consequence worth naming:** a POST with no body at all now gets the JSON sentence
instead of "Type a search term first". An empty body is an unreadable body (there is
no JSON in it) and the new message tells a bare API caller exactly what to send. The
page never shows either message: web/feat/analytics-trends.js always posts a JSON
object with a term (web/feat/analytics-trends.js:354).

**Proof:**

- Behaviour, same throwaway script: POST with `content=b"plain text not json"` gives
  400 naming the JSON problem; POST `json=["a","b"]` gives 400 "Send a JSON object";
  POST `json={"term":"   "}` gives 400 "Type a search term first"; and none of those
  requests stored anything (GET /api/trends/saved still answers `terms: []`).
- `python tests/test_trends_api.py` - All checks passed. 8 ok (its own not-JSON,
  blank-term and array checks are part of the suite).

## Skips

None. All three findings held against the code and the audit evidence.

## Gates run

- `python -m py_compile studio/api_trends.py` - OK.
- `python tests/test_trends_api.py` - All checks passed. 8 ok.
- `python tests/test_analytics_api.py` (neighbour suite; studio/api_analytics.py was
  not touched) - All checks passed. 29 ok.
- Throwaway behavioural proof (TestClient, temp folder outside the repo, removed
  afterwards): 8 checks, all ok - 150 cached reads without a 429, `source` on the
  status answer, and the three save-route refusals.
- Read-only `curl http://127.0.0.1:8798/api/trends/status` - 200. The running server
  still carries the old code in memory: the three fixes take effect after the lead's
  final restart.

## Notes

- No JavaScript file was touched, so no `node --check` was needed. No colour was
  changed, so no contrast measurement was needed. No `!important`, no shadows, no
  em dashes were introduced (checked: 0 em/en dash lines in the file).
- Everything that changed is inside studio/api_trends.py: `_throttle`'s docstring,
  `_cached`'s signature and cache-miss throttle, the three cached routes' throttle
  placement, the status answer's `source` key, and the save route's unreadable-body
  sentence.
