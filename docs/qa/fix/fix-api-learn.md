# Fix report — studio/api_learn.py

Slug: `fix-api-learn`. Fixer: agent-198. Date: 2026-11-22.
Wave: 40-agent fix wave for PeakCut. Findings source: `docs/qa/FINDINGS.md` section `## studio/api_learn.py`
(3 findings, all minor). Audit report: `docs/qa/audit/api-learn.md`.

## Files owned (and edited)

| File | What was touched |
|---|---|
| studio/api_learn.py | the run route's `days` fallback, the undo route's bad-body message, the arms route's empty answer |

No other file was read-modified. `web/index.html` untouched (lead owns it). No server kill or restart
(the lead does that once at the end). No subagents. No `dsh_browser_*` calls.

## Fixes (each verified real before the change)

### 1. studio/api_learn.py:114 (finding: undo message's own example `{"at": 0}` can never succeed) — FIXED

Verified real before fixing: the 400 message for a body that is not a JSON object suggested
`{"at": 0}`, but every round records `at > 0` (`time.time()`) and the engine matches with
`abs(r.at - at) < 1` (studio/learn.py:671), so `at=0` always falls through to
`ValueError("There is no round from that time.")` (studio/learn.py:675) and answers 400. A beginner
who copies the suggested shape gets an error.

Change: dropped the `{"at": 0}` shape from the message and replaced it with the guidance line 122
already carries, so both refusal messages now say the same usable thing:

```
        raise HTTPException(400, "Send a JSON object, or leave \"at\" out to undo the newest round.")
```

(The companion refusal at line 130 already says "Leave \"at\" out to undo the newest round." and was
left as it is — its copy is correct.)

Proof: `python -m py_compile studio/api_learn.py` → OK; `python tests/test_learn_api.py` →
"All checks passed. 76 ok" (its undo tests at tests/test_learn_api.py:192-194, :221-228 exercise these
routes and still pass; the not-a-dict message itself is not asserted by any test).

### 2. studio/api_learn.py:87-93 (finding: an invalid `days` value silently becomes 28 with no note) — FIXED

Verified real before fixing: `days = int(days)` on `TypeError`/`ValueError` → 28, and
`if days not in (7, 28, 90, 365): days = 28`, with nothing in the answer explaining the swap
(audit live evidence: `POST /api/learn/run {"days":"bad","dry":true}` → `"days": 28`, no note).

Change: the requested value is kept as `asked`, coercion failure sets `days = None`, and after the
engine answers the route adds a `note` sentence naming the fallback, so one response carries both the
span that ran and the reason:

```python
    if asked not in (7, 28, 90, 365):
        out["note"] = ("PeakCut runs rounds over 7, 28, 90 or 365 days. The days value sent (%s) is "
                       "not one of those, so this round used the usual 28 days." % asked)
```

Rendered example (proven with `python -c`): "PeakCut runs rounds over 7, 28, 90 or 365 days. The days
value sent (13) is not one of those, so this round used the usual 28 days."

Behaviour is otherwise unchanged: 7/28/90/365 run as before, a non-dict body still answers 400, and the
`note` is added only after the engine answers, so refusal paths keep their own sentences.

Proof: `python -m py_compile studio/api_learn.py` → OK; `python tests/test_learn_api.py` →
"All checks passed. 76 ok" (its day-count tests at tests/test_learn_api.py:157-172 — `{"days": 13}` →
200/`days == 28`, and the bad-body loop `{"days": "not a number"}`, `{"days": None}`, `{"days": [1, 2]}`,
`[]` → never a 500 — exercise the changed return path and still pass).

### 3. studio/api_learn.py:224-236 (finding: `GET /api/learn/arms` returns `{"trial": null}` with no sentence, contradicting the module header's promise at lines 19-20) — FIXED

Verified real before fixing: the module header says "Every route answers with a sentence as well as
data, because \"nothing happened\" is the answer that most needs explaining" (studio/api_learn.py:19-20),
but the arms route's normal and unreadable-trial paths returned `{"trial": None}` bare; only the
module-missing path carried a `why`.

Change: when the answer carries no trial, the route now adds the sentence the audit suggested:

```python
    if not got.get("trial"):
        # An empty answer is the one the module header says most needs explaining: without a sentence,
        # a page drawing no trial cannot tell "none yet" from a mistake.
        got["why"] = "No trial is saved yet. Start one to try two settings against each other."
```

Consumer safety checked before the change: the only consumer of the GET endpoint is
web/feat/learn-arms.js:234. When `trial` is null that page draws its "Start a trial" card and never
calls `sentenceOf()` (learn-arms.js:162 is reached only from `trialBlock`, which only runs when a trial
record exists, learn-arms.js:190-191), so the new sentence can never be misdrawn as a comparison
result. When a trial exists no `why` is added. tests/test_learn_api.py:260-262, :283-290 assert only
the `trial` key and still pass.

Proof: `python -m py_compile studio/api_learn.py` → OK; `python tests/test_learn_api.py` →
"All checks passed. 76 ok".

## Skips

None. All three findings held under re-verification, so all three were fixed.

## Gates run

| Gate | Result |
|---|---|
| `python -m py_compile studio/api_learn.py` | OK (exit 0) |
| `python tests/test_learn_api.py` | All checks passed. 76 ok |
| Read-only probe `curl http://127.0.0.1:8798/api/learn/state` | 200 (server up, untouched by this wave; the lead owns restarts) |
| Note-string render check (`python -c`, finding 2) | Renders the full plain-language sentence |

`node --check` was not applicable — no JavaScript file was touched.

## Note for the lead

The three fixes are in Python route code, so they take effect on the running QA instance only after the
final restart. Until then the live server keeps answering the old messages (`{"at": 0}` example, silent
`days` swap, bare `{"trial": null}`).
