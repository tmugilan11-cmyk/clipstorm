# Wave 2 review: Insights and Trends

Reviewer: agent-50. Read-only. Skill loaded: `code-review`.

Everything below was read from disk and every claim was re-run before it was written down. Where I
could not prove something I say so instead of calling it clean.

## What wave 2 changed

Web (15 files in `web/feat/`):

| File | Bytes | Lines |
| --- | --- | --- |
| `analytics.js` (the shell) | 11625 | 220 |
| `analytics-audience.js` | 14808 | |
| `analytics-charts.js` | 15174 | |
| `analytics-compare.js` | 12049 | 246 |
| `analytics-empty.js` | 6821 | 126 |
| `analytics-export.js` | 11416 | 252 |
| `analytics-help.js` | 15067 | 276 |
| `analytics-kpi.js` | 11166 | 180 |
| `analytics-realtime.js` | 11062 | 200 |
| `analytics-retention.js` | 21763 | 446 |
| `analytics-revenue.js` | 12664 | 229 |
| `analytics-shorts.js` | 15470 | 272 |
| `analytics-table.js` | 15435 | |
| `analytics-traffic.js` | 12371 | |
| `analytics-trends.js` | 21073 | 393 |

Server: `studio/api_trends.py` (381 lines, new), and one include line in `studio/server.py`
(`api_trends.router` at server.py:256, the import at server.py:28).

Docs and tests: `docs/INSIGHTS.md` (111 lines), `tests/test_insights_pages.py`, `tests/test_trends_api.py`.

Fourteen agent reports sit beside this file in `docs/swarm4/wave2/`.

## What I ran, and the literal output

All five gates, in one go, from `peakcut/`:

```
python -m py_compile studio/api_trends.py studio/api_analytics.py studio/server.py tests/test_trends_api.py tests/test_insights_pages.py
py_compile OK
```

`node --check` on each of the 15 files: fifteen `OK` lines, exit 0.

```
python tests/test_feat_files.py
ok   loader keeps the documented folder
{"files": 37, "checks": 302}
All checks passed.

python tests/test_insights_pages.py
ok   no Insights file hard-codes an origin   all paths are relative

All checks passed. 80 ok

python tests/test_trends_api.py
ok   test_google_refusing_a_connected_account_is_not_a_500

All checks passed. 8 ok

python tests/test_menu_pages.py
ok   menu-pages.js draws its page

All checks passed. 142 ok
```

I did not trust the route gate on its own, because it only reads GET and POST decorators. I wrote a
separate sweep that reads every `@router.<verb>` and `@app.<verb>` decorator in `studio/*.py` and
compares it with every `/api/...` literal in the analytics files:

```
routes: 150
19 /api literals across analytics files
MISSING ROUTES: none
```

The 19 literals resolve to `GET /api/analytics/{summary,timeseries,videos,audience,traffic,retention}`
and `GET|POST|DELETE /api/trends/saved`, `GET /api/trends/{searches,videos}`. Every one exists.

To check the Lifetime range I called the real app through `TestClient` with the same environment
`tests/test_trends_api.py` uses, asking for the day count `analytics.js` produces for Lifetime today
(7994 days, from 1 January 2005):

```
422 {"detail":[{"type":"less_than_equal","loc":["query","days"],"msg":"Input should be less than or equal to 3650","input":"7994","ctx":{"le":3650}}]}  /api/analytics/summary?days=7994
422 (the same body)  /api/analytics/audience?days=7994
422 (the same body)  /api/analytics/videos?days=7994
422 (the same body)  /api/analytics/traffic?days=7994
422 (the same body)  /api/analytics/timeseries?days=7994
200 {"source":"peakcut","days":0,...}  /api/analytics/summary?days=0
200 {"source":"peakcut","days":28,...}  /api/analytics/summary?days=28
```

## Findings

### Critical

None. No file fails to parse, no fetched path is missing, no number is invented, nothing writes into
`web/index.html`, and no wave-2 id collides with an id in the page.

### Important

**1. Four files link to a Settings address that draws the wrong tab.**
`web/feat/analytics-kpi.js:25`, `web/feat/analytics-realtime.js:43`, `web/feat/analytics-shorts.js:30`
and `web/feat/analytics-traffic.js:20` all set `APPS = "/app/settings/apps"`. The link text is
"Connected apps" (`analytics-kpi.js:127`, `analytics-realtime.js:130`, `analytics-shorts.js:187`,
`analytics-traffic.js:135` and `:136`).

That address is served (the SPA catch-all at `studio/server.py:426-430`) and `fromPath` at
`web/index.html:1365` does return `["settings", "apps"]`, but `go()` at `web/index.html:1393` then
does `S.stab = setTabs().some(x => x[0] === tab) ? tab : setTabs()[0][0]`, and `setTabs()` at
`web/index.html:2214-2217` holds only profile, security and storage. There is no `apps` entry, so
`S.stab` becomes `"profile"` and `drawSettings()` at `web/index.html:2432` draws the Profile tab.

A person who reads "connect a channel under Connected apps" and clicks lands on Profile, with no
Connect button in sight.

The working address is `/app/apps`, the plug-in page registered at `web/feat/menu-pages.js:181-196`,
and `web/feat/analytics-empty.js:26` gets this right (`const APPS = "/app/apps"`). Five files had the
correct pattern next door and four did not use it. `docs/INSIGHTS.md:94` repeats the broken address.

**2. The Lifetime range breaks the Audience tab and mangles the key number row.**
`analytics.js:39-42` computes Lifetime as a start of 1 January 2005 and `days` as the real day count
(7994 today). `analytics-audience.js:210-217` returns that number unchanged, and
`analytics-audience.js:186` sends it straight to `/api/analytics/audience`, whose signature is
`days: int = Query(28, ge=0, le=3650)` at `studio/api_analytics.py:328`. FastAPI answers 422 with a
list in `detail`. `api()` at `web/index.html:951-955` turns a non-string detail into
"Something went wrong", so `analytics-audience.js:59` draws three lines reading
"Returning and new viewers did not load. Something went wrong. Refresh the page to try again."

The same 422 hits `analytics-kpi.js:96`, which passes `days` through at `:98` without a clamp. Its
catch at `:162-166` renders "The summary could not be read. Something went wrong. Reload this page to
try again." So it fails soft, as the contract asks, but with no usable sentence.

Six other files handle this correctly and one of them should be the model:
`analytics-charts.js:72` and `analytics-retention.js:140` clamp with `Math.min(3650, ...)`,
`analytics-revenue.js:132` clamps, `analytics-shorts.js:131` and `analytics-trends.js:99` map anything
over 3650 to 0 (the lifetime sentinel). `analytics-audience.js` and `analytics-kpi.js` are the two
that do not.

`docs/INSIGHTS.md:106-107` documents the key number case. The Audience failure is not documented.

### Minor

**3. Two panels label a date window the server did not use.**
`analytics-table.js:199` asks `/api/analytics/videos?from=...&to=...`, but the route at
`studio/api_analytics.py:272-273` declares `days` and `limit` only, so `from` and `to` are ignored and
every answer is the 28-day default. `analytics-table.js:170` still writes "Every number covers
<from> to <to>." from the header range. Same shape in `analytics-traffic.js:63`, which sends `start`
and `end` to a route that reads `days` (`studio/api_analytics.py:375`).

This is a label that can claim a window the numbers do not cover, which is the spirit of rule 2. The
numbers themselves are real and the limitation is written down at `docs/INSIGHTS.md:108-109`, but the
sentence on screen does not say it.

**4. Two different dash characters for the same state.**
`analytics-compare.js:20` and `analytics-kpi.js:25` and `analytics-traffic.js:20` use U+2013,
`analytics-realtime.js:35`, `analytics-shorts.js:30`, `analytics-revenue.js:32` and
`analytics-table.js:39` use the escaped `"\u2013"` (the same character), and
`analytics-trends.js:14` uses plain ASCII `"-"`. A missing number prints one shape on four tabs and
another on Trends. Cosmetic, trivially fixed.

**5. `tests/test_insights_pages.py:25` cannot see DELETE routes.**
The regex is `@(?:router|app)\.(?:get|post)\(`. `@router.delete("/api/trends/saved")` at
`studio/api_trends.py:364` is invisible to it, and the comment at `test_insights_pages.py:23-24`
admits the author leaned on the GET and POST on the same path. `analytics-trends.js:364` does call
that DELETE with `{ method: "DELETE" }` and it works, so nothing is broken at runtime, but the gate
that is supposed to catch a missing route would not catch a missing DELETE.

**6. `tests/test_feat_files.py:92-99` under-checks escaping for five files.**
The escape assertion only fires when `${` appears inside an `innerHTML =` or `insertAdjacentHTML(`
expression. Files that build a string and hand it to `put()` get the weaker "draws only fixed markup"
line: `analytics-empty.js`, `analytics-revenue.js`, `analytics-shorts.js`, `analytics-realtime.js`,
`analytics-trends.js`. `analytics-help.js` gets "draws no markup" because it uses `textContent`.
I checked those six by hand (see the table below) and they are escaped, but the gate is not the thing
that proved it.

**7. The doc is wrong about where Export appears.**
`docs/INSIGHTS.md:110-111` says Trends has no button. `analytics-export.js:56-62` drops the button on
Trends and also on every tab not in `OWN = ["overview", "content"]` (`analytics-export.js:26`) that
holds no rows. Audience and Traffic render no `table tbody tr` and no `.akpi-c` (verified by reading
their markup), so they have no button either. The doc understates the rule.

### Notes, not defects

- `studio/api_trends.py:295` calls the private `ytstats._videos` with a `# noqa: SLF001` comment. It
  works (`ytstats.py:246`) and a failure falls back to the video id, so titles degrade rather than
  break. Worth a public helper later.
- `analytics-kpi.js:50` normalises a sent `change` by multiplying by 100 when `Math.abs(sent) <= 1.5`,
  which would misread a genuine 1 percent change sent as the number 1. It is a heuristic on
  server-supplied data, not an invented number.
- `analytics-export.js:136-140` prefixes `'` to cells starting with `=`, `+` or `@` but not to a
  leading `-`. A negative number would open as a formula in some spreadsheets. Low risk, easy fix.
- `analytics-retention.js:78` and `analytics-table.js:122` each carry a `fetch` fallback for when
  `P.api` is absent. Both are guarded by `if (typeof P.api === "function")` first, so on the real page
  they never run.

## File by file

Plain "yes" means I read the code and the check holds. "n/a" means the file has no such surface.

| File | Parses | One plug-in, own name | Escapes | data-act handled | Routes exist | Failure visible | No invented number | No id clash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `analytics.js` | yes | `P.page("analytics")` at :210 plus one merging `P.add` at :218 | yes | `data-an-tab`/`-range`/`-compare` at :196-208 | n/a | n/a | yes | yes |
| `analytics-audience.js` | yes | `P.add("analytics-audience")` :231 | yes | n/a | yes | yes (:59) | yes | yes |
| `analytics-charts.js` | yes | :254 | yes | pointer handlers :128-174 | yes | yes | yes | yes |
| `analytics-compare.js` | yes | :241 | yes (:171, :178) | n/a | yes | yes (:126-127) | yes (:102-104) | yes |
| `analytics-empty.js` | yes | :125 | yes (:34-39) | `data-act="go"` :61, handled at index.html:2833 | n/a, asks nothing | yes | yes | yes |
| `analytics-export.js` | yes | :250 | yes | `data-ae` :195 to :239-244 | n/a, reads the DOM | yes (:221-225) | yes | yes |
| `analytics-help.js` | yes | :261 | `textContent` only (:185, :190) | own click/keydown :198, :204 | n/a | n/a | yes | yes |
| `analytics-kpi.js` | yes | :179 | yes (:140-146) | n/a | yes | yes (:162-166) | yes | yes |
| `analytics-realtime.js` | yes | :198 | yes (:134-139) | n/a | yes | yes (:121-122) | yes (:105-106) | yes |
| `analytics-retention.js` | yes | :439 | yes | `data-ar` in `bind()` :307-331 | yes | yes (:199-208) | yes | yes |
| `analytics-revenue.js` | yes | :227 | yes (:146-177) | n/a | yes | yes (:159-164) | yes (:157-164) | yes |
| `analytics-shorts.js` | yes | :269 | yes | n/a | yes | yes (:183) | yes (:170) | yes |
| `analytics-table.js` | yes | :260 | yes | `data-ant` :210+ | yes | yes (:173-174) | yes | yes |
| `analytics-traffic.js` | yes | :176 | yes | n/a | yes | yes (:134) | yes (:101-108) | yes |
| `analytics-trends.js` | yes | :384 | yes | `data-atr-*` :375-384 | yes | yes (`failLine`, :78-81) | yes (:14, :205) | yes |

Checks that apply to the whole set:

- Registration. One `P.add` per file, named after the file, in all 14 siblings. `analytics.js` is the
  only file that also calls `P.page`, and its `P.add("analytics", ...)` merges into the same plug-in
  because `plugins.js` does `Object.assign` when the name already exists. No file registers twice and
  no file registers as somebody else.
- Escaping. Every `${}` in the 15 files is a number, a constant, `ic()` output, or a call to a helper
  that escapes (`esc`, `say`, `cell`, `head`, `bodyHtml`, `row`). The only interpolation into an
  attribute happens through `esc` at the point of insertion, for example
  `analytics-retention.js:182` `aria-label="${esc(label)}"`.
- No raw server text in `innerHTML`. `analytics-help.js` is the strictest of them and uses
  `textContent` throughout.
- Icons. Every `ic(...)` argument is a literal from the 58 in `web/index.html`. No dynamic icon name
  reaches `ic()`.
- House style. No em dash (U+2014) and no emoji in any of the 15 files, in `docs/INSIGHTS.md`, in
  `studio/api_trends.py`, or in the two new tests. No occurrence of "seamless" or "powerful". No
  exclamation mark in any user-facing sentence.
- Bare identifiers. No file uses `window.ic`, `window.esc` or `window.go`. The helpers are read as
  bare names or through `PeakCut`, with a `typeof` guard.
- `web/index.html`. It contains zero occurrences of the string "analytics", zero `id="an_` and zero
  `akhelp`, so none of the new boxes can clash. The file's mtime moved during the wave (05:17), which
  is inside the window, but no wave-2 file writes to it (`test_feat_files.py:87` asserts that per file
  and passes for all 37) and nothing wave 2 built needs markup there. I state the mtime as unproven
  rather than clean.
- Server. `api_trends.py` answers all six documented routes, refuses a blank term ("Type a search term
  first, then save it.") and the fifty-first ("You can keep 50 search terms. Remove one before adding
  another."), reads a broken JSON file as an empty list, writes through a `.tmp` and `replace`, and
  turns a Google refusal into a note rather than a 500. `_throttle` maps `auth.AuthError` to a 429 with
  a sentence. `_cached` never caches a failure.

## What I could not verify

- No YouTube channel is connected on this instance, so every path that needs a live Google answer was
  read from source and from the route's own no-connection branch, not from a successful response.
- I did not open the pages in a browser. Every judgement about what a person sees is reasoned from
  `web/index.html`, `web/plugins.js` and the feature files, not observed.
- The index.html mtime change cannot be attributed to a file from the files alone.

## Verdict

Every gate is green, every file parses, every fetched route exists, every failure surfaces as a
sentence on the page, no number is invented, no id collides and the frozen page was not edited. The
two important defects are the four wrong "Connected apps" links (fix them to `/app/apps`, and fix
`docs/INSIGHTS.md:94` with them) and the unclamped Lifetime day count in `analytics-audience.js:210`
and `analytics-kpi.js:96` (clamp to 3650 exactly as `analytics-charts.js:72` does). Both are small,
local, non-destructive changes a fixer can land without touching any other agent's file.

SHIP. All five gates pass and nothing found loses data or ships a wrong number as fact; the two important defects are a wrong link target and an unclamped day count, each a one or two line fix in a wave-2 file.

