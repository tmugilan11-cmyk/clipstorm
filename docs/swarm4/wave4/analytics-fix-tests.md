# analytics-fix-tests — the route scan now reads every verb

Wave 4, item 4 of the four carried-over Important findings from wave 2's review.

## What I built

One file: `tests/test_insights_pages.py`. Nothing else was edited.

The scan was at line 25 (now line 29 after the added comment and checks). It decides which
server routes exist, and every "this plug-in fetches only routes this server has" check is
downstream of it. It read only `get`, `post` and `delete`. Two problems followed:

1. `put` and `patch` routes were invisible. `/api/upload/{upid}/{n}` (`@app.put`) was
   missing from the route map altogether, and the PATCH half of
   `/api/jobs/{jid}/clips/{cid}` was missing, so a plug-in that asked for either would
   have been reported as asking for a route that does not exist.
2. Nothing checked that a DELETE was counted at all. `/api/trends/saved` happens to be
   decorated GET, POST *and* DELETE, so dropping `delete` from the pattern still left
   the *path* in the route map — the loss was silent. That is exactly why the finding
   said the DELETE "cannot be counted": counting paths hides it.

### The changes

- **The pattern** (now line 29) reads `get|post|put|patch|delete`, and captures the
  **verb as group 1** and the path as **group 2**. Grouping the verb is what lets the
  test report a verb rather than throw it away:

  ```python
  ROUTE = re.compile(r"@(?:router|app)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']")
  ```

- **`route_paths()`** now returns `(routes, verbs)`. `routes` maps path → file, as
  before. `verbs` maps path → the set of upper-case verbs answered there, so one path
  can be shown to carry several.

- **Three new checks**, right after the route count, each of which fails if a verb is
  dropped from the pattern:
  - `the scan sees DELETE routes` — the union of all verbs contains DELETE, and the
    detail line prints every DELETE route it found.
  - `the Trends DELETE route is counted` — `DELETE /api/trends/saved` from
    `studio/api_trends.py` is among them.
  - `the Trends route is counted as three verbs` — `/api/trends/saved` carries exactly
    `{GET, POST, DELETE}`. This is the check that makes the loss loud instead of silent.

### Measured effect

- Routes found: **137 → 138**. One path was previously invisible to the scan and is now
  seen: `/api/upload/{upid}/{n}` in `studio/server.py:989`, which is a `@app.put`.
- The second widened-verb gain is on an existing path rather than a new one:
  `/api/jobs/{jid}/clips/{cid}` is answered by `@router.patch` at `studio/api_review.py:98`
  as well as by `@app.delete` at `studio/server.py:1091`. The path was already counted
  through its DELETE; the PATCH on it was invisible, so before the change that route
  looked like it only accepted DELETE.
- Check count: **80 ok → 83 ok**, all passing.
- `/api/trends/saved` is now recorded as `GET, POST, DELETE`; before the change the
  verb information did not exist at all, which is what let a missing `delete` go unnoticed.

### Negative test (proves the checks bite)

I copied the file with `delete` removed from the pattern
(`(get|post|put|patch|delete)` → `(get|post|put|patch)`) and ran it:

```
exit: 1
FAIL the scan sees DELETE routes   no DELETE decorator was read
FAIL the Trends DELETE route is counted   DELETE /api/trends/saved from api_trends.py
FAIL the Trends route is counted as three verbs   GET, POST
3 check(s) failed
```

Exactly the three new checks fail and nothing else, which is the behaviour the finding
asked for. The temporary file was deleted afterwards.

## Which routes it reads

This file reads no HTTP routes; it is a static checker. It scans the decorators in
`studio/*.py` — `@router.get|post|put|patch|delete(...)` and
`@app.get|post|put|patch|delete(...)` — and compares the request paths written in
`web/feat/analytics-*.js` against them. The DELETE it now counts is
`DELETE /api/trends/saved` at `studio/api_trends.py:364`.

## What it cannot do yet

- The scanner is a regex, not a parser. It only sees decorators written as a quoted
  path literal on the same call: a route built from a constant, or spread over lines
  between `(` and the first quote, is still missed. No such route exists today; if one
  is added, this check will not see it and the plug-in check may report a false miss.
- It does not record the verb of a *request* from the JavaScript side. It checks that a
  path exists, not that the page uses the right method on it — a plug-in could POST to a
  GET-only route and still pass. Adding that would mean parsing `P.send(...)` calls.
- `analytics-trends.js` is checked only for its paths (`/api/trends/saved`,
  `/api/trends/searches`, `/api/trends/videos`); which verb it uses on `/api/trends/saved`
  is not asserted.

## Commands I ran and their results

```
$ python tests/test_insights_pages.py
ok   studio files say what routes they answer   138 routes
ok   the scan sees DELETE routes   DELETE /api/accounts/{aid}, DELETE /api/creators/{cid},
     DELETE /api/jobs/{jid}, DELETE /api/jobs/{jid}/clips/{cid}, DELETE /api/learn/arms,
     DELETE /api/trends/saved, DELETE /api/upload/{upid}
ok   the Trends DELETE route is counted   DELETE /api/trends/saved from api_trends.py
ok   the Trends route is counted as three verbs   DELETE, GET, POST
...
All checks passed. 83 ok
exit code 0

$ python tests/test_feat_files.py
...
{"files": 39, "checks": 318}
All checks passed.
exit code 0
```

A later re-run of `tests/test_feat_files.py` reported `{"files": 42, "checks": 342}` and still
`All checks passed.` — the count grows because other wave-4 agents are adding their own
`web/feat/*.js` files at the same time. My change does not touch that file or those counts.

Baseline before the change, for comparison: `All checks passed. 80 ok`, 137 routes.

`node --check` does not apply to this job — the file I own is Python, not a
`web/feat/*.js` file. `tests/test_insights_pages.py` itself runs `node --check` on all
14 `analytics-*.js` plug-ins and they all parse.
