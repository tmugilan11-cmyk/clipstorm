# Audit — API area: /api/learn/*, /api/brandai/suggest, /api/posttime

Slug: `api-learn`. Auditor: agent-151. Date: 2026-11-22. Server: http://127.0.0.1:8798 (live QA instance).
Skill loaded before starting: `systematic-debugging`. No browser tools used (lead owns the browser).

## Files owned (read fully, audited)

| File | Routes |
|---|---|
| studio/api_learn.py:1-305 | GET /api/learn/state, POST run, POST undo, GET/POST/DELETE /api/learn/arms, GET signals, GET cost |
| studio/learn.py:1-692 | the engine behind run/undo/state (facts, measure, compare, _apply, undo) |
| studio/api_hooks.py:1-85 | GET /api/learn/hooks |
| studio/api_learnreport.py:1-58 | GET /api/learn/report |
| studio/api_brandai.py:1-113 | POST /api/brandai/suggest |
| studio/api_posttime.py:1-97 | GET /api/posttime |

Supporting modules read for contracts (not owned): studio/learn_report.py, studio/ai_arms.py, studio/hookscore.py,
studio/learn_signals.py, studio/learn_guard.py, studio/ctx.py, studio/jobs.py:309-318, studio/server.py:120-230,216.

## Checks run (all against the live server)

- GET /api/learn/state — 200, newest-first rounds, settings from brand, `can_run`/`why_not` honest.
- GET /api/learn/cost — 200, `"8 of 8 rounds left today, and 60,000 of 60,000 tokens."`
- GET /api/learn/arms — 200 `{"trial":null}`; after POST start → trial saved; after DELETE → `{"trial":null}` (cleanup done, no trace left).
- GET /api/learn/signals?days=28&seconds=0 — 200 empty shape; ?days=banana&seconds=abc — 200 same empty shape (quiet fallback, by design).
- GET /api/learn/hooks — 200, 5 hooks scored (5 strong, 0 weak), note empty-state string present.
- GET /api/learn/hooks?limit=banana — **HTTP 422** raw FastAPI validation body.
- GET /api/learn/report — 200 (findings below); ?limit=1 — 200 (order probe); ?limit=banana — **HTTP 422**.
- GET /api/posttime — 200 honest not-yet: `"Not enough posts yet. PeakCut names no hour until there are 5 posts with view counts."`
- POST /api/learn/run {"dry":true} — 200 honest preview, no mutation; {"days":"bad","dry":true} — 200, silently days=28; [1,2] — 400.
- POST /api/learn/undo {"at":"banana"} — 400 plain-language; {"at":0} — 400 `"There is no round from that time."` (the error message's own suggested example); success path NOT exercised live: it would restore brand values from the newest round and mutate the operator's brand mid-audit, so it was verified by reading studio/learn.py:658-692 instead.
- POST /api/learn/arms {"target":"banana","value":"x"} — 400 with the settings list; "hello" — 400; {"target":"style","value":"beast"} (one arm) — 400 `"a setting called nothing"`; {"target":"hook_words","value":"wait for it","other":"clip_len","other_value":"45"} — 200 trial saved; same setting twice — 400 plain-language.
- POST /api/brandai/suggest {} — 200 after 41.0 s: honest `"nothing this brand accepts"` with a `why` sentence and full `before` document. One call only (real AI spend; throttle is 10 per 300 s).
- Server-up probe and all four routers confirmed mounted (studio/server.py:258,264,265,266,267).
- User scoping verified: gate sets `ctx._uid` per request (studio/server.py:216); jobs.list_jobs filters by ctx.uid() (studio/jobs.py:309-312) — no cross-user leak in /api/learn/hooks.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | studio/api_learnreport.py:50-53 | `/api/learn/report` reads `learn.log()`'s **newest-first** list as if it were oldest-first: `rounds[-take:]` selects the **oldest** `take` rounds, `rows.reverse()` then outputs them **oldest-first**, and `prev = rounds[i-1]` hands `learn_report.shape()` a **newer** round where its contract says "the round before it" (learn_report.py:171-176), so a record lacking `moved` gets a comparison that runs backwards in time against the wrong pair. | Live: `GET /api/learn/report` → `rounds[0].at=1795128089.73 < rounds[1].at=1795200008.31` while `GET /api/learn/state` returns newest-first (1795200008 first); `?limit=1` returned the round with at=1795128089 (the oldest of two), not the newest. Code: studio/learn.py:95 (`list(reversed(data["rounds"]))`). | Iterate `rounds[:take]` (newest-first), pair each raw with the **next** slice entry as `previous` (None for the last), and drop the final `rows.reverse()`; or reverse the list once where `learn.log()` builds it and keep the current pairing. |
| important | studio/api_learnreport.py:57 | The `table` in the same response ignores `limit` and is ordered newest-first while `rounds` is oldest-first — one response carrying two contradictory orderings. | Live default response: `table.rows[0]="1 days 13 h ago"` (the newer round, at=1795200008) while `rounds[0].at=1795128089` (the older one); with `?limit=1`, `count:1` but `table.rows` still holds both rounds. | Build `table` from the same take-limited, ordered slice used for `rows`, so one response has one order. |
| important | web/feat/learn-arrows.js:28 vs studio/learn_report.py:127 | Shape mismatch: the report route's shaped change rows carry `setting`/`from`/`to`, but the Improve page's "Every round, before and after" card reads `c.key` — `NAMES[c.key]` is `NAMES[undefined]` → undefined → `esc(undefined)` → `""`, so every change renders as "from X → Y" with a **blank setting name**. Cross-file finding: the fix belongs in learn-arrows.js (route to lead). | studio/learn_report.py:127 (`out.append({"setting": ..., "from": ..., "to": ...})` — no `key`); web/feat/learn-arrows.js:28 (`NAMES[c.key] || c.key`); web/feat/learn-arrows.js:44 calls this exact endpoint (`/api/learn/report?limit=8`). A live changes-round could not be created without an AI key + channel, but the two shapes are unambiguous in code. | In web/feat/learn-arrows.js:28 read `c.setting` instead of `c.key` (and keep the `NAMES` map keyed on the same five setting names it already lists). |
| important | studio/api_hooks.py:44-52 and studio/api_learnreport.py:39-46 | A malformed `limit` query is refused by the framework as a raw English FastAPI validation body **before the handler runs**, so both handlers' own bad-limit fallbacks (`int(limit)` try/except) are unreachable dead code. Sibling route `/api/learn/signals` deliberately takes `days`/`seconds` as str params for exactly this reason and documents it (studio/api_learn.py:195-197) — these two routes did not follow the pattern. | Live: `GET /api/learn/hooks?limit=banana` → 422 `{"detail":[{"type":"int_parsing","loc":["query","limit"],"msg":"Input should be a valid integer..."}]}`; `GET /api/learn/report?limit=banana` → 422. Both handlers keep a quiet fallback that can never fire. | Declare `limit: str = "40"` (hooks) / `limit: str = "20"` (report) and coerce with the existing try/except, matching `/api/learn/signals`. |
| minor | studio/api_learn.py:114 (and :122) | The undo 400 message's own example `{"at": 0}` can never succeed: every round records `at > 0` and matching is `abs(r.at - at) < 1` (studio/learn.py:671), so `at=0` always answers "There is no round from that time." A beginner who copies the suggested shape gets an error. | Live: `POST /api/learn/undo {"at":0}` → 400 `"There is no round from that time."`; studio/learn.py:671. | Change the example to `"leave \"at\" out to undo the newest round"` and drop the `{"at": 0}` shape from the message. |
| minor | studio/ai_arms.py:96 (via POST /api/learn/arms) | A one-arm request is refused with `"PeakCut does not change a setting called nothing."` — it never says the second setting is missing. The page blocks this client-side with clearer copy ("Pick two different settings for the trial.", web/feat/learn-arms.js:271-278), so the server copy only shows for hand-crafted calls, but the two disagree. | Live: `POST /api/learn/arms {"target":"style","value":"beast"}` → 400 `"a setting called nothing"`; studio/ai_arms.py:94-97 validates both arms in one loop. | In ai_arms.start, refuse an empty arm with `"Name two settings to try, one for each arm."` before the known-settings check. |
| minor | studio/api_learn.py:87-93 | An invalid `days` value silently becomes 28 with no note anywhere in the answer. The response does carry `"days": 28`, so it is discoverable, but an operator sending `{"days": 30}` is never told. | Live: `POST /api/learn/run {"days":"bad","dry":true}` → `"days": 28`, no note. | Either accept 1-365 and clamp only at the extremes, or add a `"note"` sentence naming the fallback. |
| minor | studio/api_learn.py:19-20 vs :224-236 | The module header promises "Every route answers with a sentence as well as data", but `GET /api/learn/arms` returns `{"trial": null}` with no sentence (only the module-missing path carries a `why`). The empty answer is exactly the one the header says most needs explaining. | Live: `GET /api/learn/arms` → `{"trial":null}` (empty and after cleanup). | Add `"why": "No trial is saved yet. Start one to try two settings against each other."` alongside `trial: null`. |
| minor | studio/api_hooks.py:75-76 | The comment says "a broken job folder must not take the page down", but the handler raises `HTTPException(500, ...)` — the page does get an error. Either behavior is defensible; the comment contradicts the code. | studio/api_hooks.py:75-76. | Return `{"ok": false, "hooks": [], "note": "The clips could not be read: ..."}` (200) to match the comment, or fix the comment to say the page gets a friendly 500. |

## Usability (first-class findings)

| where | what | fix |
|---|---|---|
| studio/api_posttime.py:63,73-75 | Best-hours are computed from the **UTC** hour of each post (`(when % 86400) // 3600`) and presented as plain clock labels (`"14:00"`, `"averaged 500 views at 14:00"`) with no zone marker. A beginner reads "14:00" as their local clock and posts 5.5 h early (IST +5:30). | Either convert to the account's local zone before labelling, or append " UTC" to `label` and `note` (e.g. `"averaged 500 views at 14:00 UTC"`). |
| studio/api_brandai.py:52-56 (measured) | `POST /api/brandai/suggest` blocked for 41.0 s on this install. The throttle message says nothing about the wait, and the route's docstring does not warn callers how slow an enforced-schema ask is (compare the 8.9 s vs 38.3 s measurement recorded in AGENTS.md). | Add a hint where the button is defined ("this can take about half a minute") so a beginner does not think it hung. |
| studio/api_learnreport.py:50-53 (covered above) | The report the operator reads draws the **oldest** rounds and oldest-first — the history contradicts every other list on the Improve page. | Same fix as finding 1. |

## Not bugs (checked and settled)

- `/api/learn/state` shows round `before.style="hormozi"` while `settings.style="beast"`: the brand was changed after that round was recorded; both reads are from where the values really live (studio/learn.py:610-615).
- `hooks?limit=0` → `take = max(1, min(0,120)) = 1` — clamped, honest.
- `learn_guard.spent`/`report`, `learn_signals.signals/lines`, `ai_arms.start`, `hookscore.score` all exist and are imported lazily where the route needs them; module-missing paths answer 200 with the empty shape plus `why` (verified by reading, not by removing files).
- No 500s, no crashes, no 404s on any route in this area; every 400/422 body is plain-language except the two raw framework 422s filed above.
- Trial cycle left no trace: POST start → GET confirms → DELETE → GET confirms `{"trial":null}`; the temporary `arms_default.json` is removed by `_write_trial` (studio/api_learn.py:175-176).
