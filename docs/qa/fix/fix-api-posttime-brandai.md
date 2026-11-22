# Fix report — studio/api_posttime.py + studio/api_brandai.py

Slug: `fix-api-posttime-brandai`. Owner: agent-190. Date: 2026-11-22.
Findings source: `docs/qa/FINDINGS.md` sections `## studio/api_posttime.py` and `## studio/api_brandai.py`, both from audit `api-learn` (`docs/qa/audit/api-learn.md`).

## Files owned (and the only files edited)

- `studio/api_posttime.py`
- `studio/api_brandai.py`

No other file was touched. `web/feat/post-time.js` and `web/feat/brand-ai.js` were read to confirm where each fix must land, but not edited (not in the ownership list).

## Fix 1 — studio/api_posttime.py:63,73-75 (usability, real, FIXED)

**Finding.** Best-hours are computed from the UTC hour of each post (`(when % 86400) // 3600`, line 63) and presented as bare clock labels (`"14:00"`, `"averaged 500 views at 14:00"`) with no zone marker. A beginner reads "14:00" as their local clock and posts hours early or late.

**Verified.** Confirmed in code before editing: line 63 is the UTC hour; lines 73-75 format `f"{hour:02d}:00"` and `"...at {hour:02d}:00."` with no zone. The only consumer is `web/feat/post-time.js:23`, which renders `b.label` verbatim through `esc()`, so the fix has to land in the label itself.

**Fix applied (the finding's option B: append " UTC").**

- `studio/api_posttime.py:76` - `label` is now `f"{hour:02d}:00 UTC"` (the user-visible part, rendered by post-time.js).
- `studio/api_posttime.py:78` - the per-row note now reads `"2 posts averaged 2000 views at 18:00 UTC."`
- `studio/api_posttime.py:80` - the top-level note now says `"Read from N posts with view counts. Hours are UTC. Small numbers can mislead."`
- `studio/api_posttime.py:9-10` - the module docstring states the rule in plain language: hours are named in UTC and every label says so, because a bare clock time would be read as the person's own local time.

**Why option B and not converting to the account's local zone (measured, not guessed).** `tests/test_wiring.py:72` asserts `rich["best"][0]["hour"] == 18` for rows built from UTC epochs (`3600 * 18 + 100`). Converting to local time before labelling would fail that gate on any non-UTC machine. Appending " UTC" keeps the numeric `hour` field and every existing gate intact while removing the ambiguity the finding names.

**Proof.**

- `python -m py_compile studio/api_posttime.py studio/api_brandai.py` - exit 0 (`PY_COMPILE_OK`).
- `python tests/test_wiring.py` - `23 checks run`, `All checks passed.`
- Direct probe of the changed function: `hours_for(...)` on six UTC rows printed `POSTTIME_LABEL_OK 18:00 UTC | 2 posts averaged 2000 views at 18:00 UTC.` (label, per-row note and top note all carry UTC; the not-enough branch still answers `"Not enough posts yet..."`).
- `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/api/posttime` - `200` (the live instance still runs the pre-fix code; the new labels take effect after the lead's final restart).

## Fix 2 — studio/api_brandai.py:52-56 (usability, real, measured, FIXED in-file)

**Finding.** `POST /api/brandai/suggest` blocked for 41.0 s on this install. The throttle message says nothing about the wait, and the route's docstring does not warn callers how slow an enforced-schema ask is (compare the 8.9 s vs 38.3 s measurement in AGENTS.md). Suggested fix: a hint under the button.

**Verified.** Confirmed in code: the route at `studio/api_brandai.py:52-56` had a one-line docstring with no wait warning and a throttle message with no wait warning; `_work` sends `_SCHEMA` through `ai.call(..., 60.0)` (line 94 of the pre-fix file), which is the enforced-schema ask AGENTS.md documents as slow. Live probe during this fix: my own `POST /api/brandai/suggest` (no body) had to be aborted at 10 s (`curl` exit 28, status 000) - the route is alive and slow exactly as the audit measured. Not repeated, to avoid real AI spend.

**Fix applied (the two gaps the finding names, both inside the owned file).**

- `studio/api_brandai.py:52-59` - the route docstring now warns callers: "One ask is slow by design: an answer that must match the schema can take about half a minute (measured 41.0 s here), so a page that sends this should say so under the button."
- `studio/api_brandai.py:60-61` - the throttle message (user-visible on 429) now reads: "That is a lot of brand suggestions at once. Give it a moment; even one ask can take about half a minute."

**Remaining one-line frontend hint (left for the lead).** The suggested fix's location - a hint under the Ask button - is `web/feat/brand-ai.js:27-31`, a file that is not in my ownership list (my brief names the two studio files; FINDINGS.md has no fixer section for `web/feat/brand-ai.js`). The one-line change for whoever owns it: extend the sub sentence at `web/feat/brand-ai.js:27-28` with "this can take about half a minute" so a beginner does not think the card hung while the ask runs. I did not edit that file.

**Proof.**

- `python -m py_compile studio/api_posttime.py studio/api_brandai.py` - exit 0 (`PY_COMPILE_OK`).
- `python tests/test_wiring.py` - `23 checks run`, `All checks passed.` (it greps the brandai route for its declaration and `brand_ai.preview(`; both intact).
- Route alive on the live server (probe above); the wording changes take effect after the lead's final restart.

## Skips

- None. Both findings' evidence held. The only out-of-scope remainder is the one-line button hint in `web/feat/brand-ai.js:27-31`, recorded above rather than skipped silently.

## Gates run

| Gate | Result |
|---|---|
| `python -m py_compile studio/api_posttime.py studio/api_brandai.py` | exit 0 |
| `python tests/test_wiring.py` | 23 checks run, all passed |
| `python tests/run.py` (full suite, per AGENTS.md for any studio change) | every section passed except one pre-existing failure: `tests/test_updates.py` ("the new-version notice") |
| `python tests/test_feat_files.py` | 75 files, 606 checks, all passed (no web/feat file was edited) |
| `python tests/test_text_ink.py` | 10 checks, all passed |
| Direct `hours_for` probe | `POSTTIME_LABEL_OK 18:00 UTC | 2 posts averaged 2000 views at 18:00 UTC.` |
| `curl http://127.0.0.1:8798/api/posttime` (read-only) | 200 |

**On the one failure (`tests/test_updates.py`).** Pre-existing and environmental, not caused by this fix: its line 31 requires a real git checkout (`check("this folder's own version is found", len(updates.current()), 40)`, where `updates.current()` reads `.git` refs under `config.ROOT`), but this workspace has no `.git` at all (`git describe` answers "fatal: not a git repository"). The same test's fake-`.git` section (lines 20-29) passes. My changes cannot affect version reading - `studio/api_posttime.py` and `studio/api_brandai.py` are not imported anywhere in that path.

## Restart note

Both fixes are in Python route files, so nothing here changes the running instance until the lead's final restart. The live-server probes above were read-only against the pre-fix code.
