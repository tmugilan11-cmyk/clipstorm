# Wave 2 fixes

This file answers `peakcut/docs/swarm4/wave2/REVIEW.md` finding by finding. It lists what I changed, in
which file, and the literal output of the command that proves it.

The review's verdict was SHIP with no critical findings. This pass covers both Important findings,
Minors 4, 5 and 7 in full, the Traffic half of Minor 3, and one of the four notes. Left over: Minor 6
and the Content half of Minor 3, both explained at the end with the reason each was not a small change.

Skill loaded before any edit: `code-review`.

---

## Important 1. Four files linked to a Settings address that draws the wrong tab

**The finding.** `analytics-kpi.js:25`, `analytics-realtime.js:43`, `analytics-shorts.js:30` and
`analytics-traffic.js:20` set `APPS = "/app/settings/apps"`. `fromPath` turns that into
`["settings", "apps"]`, then `go()` keeps the tab only when `setTabs()` knows it. `setTabs()` holds
profile, security and storage, so the tab fell back to `profile` and the Profile form drew. The link
says "Connected apps" and the person landed on Profile.

`web/feat/analytics-empty.js:26` already had the right value. The page registered at
`web/feat/menu-pages.js:185` (`path: "apps"`, `nav: "Connected apps"`) is the one that draws the form.

**What I changed.** One string in each of the four files, from `/app/settings/apps` to `/app/apps`.
Nothing else on those lines moved.

```
web/feat/analytics-kpi.js:25        APPS = "/app/settings/apps"  ->  APPS = "/app/apps"
web/feat/analytics-realtime.js:43   APPS = "/app/settings/apps"  ->  APPS = "/app/apps"
web/feat/analytics-shorts.js:30     APPS = "/app/settings/apps"  ->  APPS = "/app/apps"
web/feat/analytics-traffic.js:20    APPS = "/app/settings/apps"  ->  APPS = "/app/apps"
docs/INSIGHTS.md:94                 /app/settings/apps            ->  /app/apps
```

The review only named the four feature files, but `docs/INSIGHTS.md:94` repeated the broken address
for a reader who follows the instructions, so it is fixed in the same change.

**Proof.**

```
$ grep -rn "/app/settings/apps" web/feat docs/INSIGHTS.md
(no matches)
$ grep -rn 'const APPS = ' web/feat/*.js
analytics-empty.js:26:  const APPS = "/app/apps", LINK = "Connect a channel";
analytics-realtime.js:43:  const APPS = "/app/apps";
analytics-shorts.js:30:  const APPS = "/app/apps", DASH = "\u2013", SHOW = 10;
analytics-traffic.js:20:  const APPS = "/app/apps", DASH = "–", LIST = ["sources", "traffic", "rows", "items", "data"];
$ grep -n 'APPS' web/feat/analytics-kpi.js
25:  const DASH = "–", APPS = "/app/apps", DAY = {day: "numeric", month: "short"}, IC = typeof ic === "function";
128:    const apps = `<a href="${APPS}">Connected apps</a>`, fill = `Connect a channel in ${apps} to fill these in.`;
```

`analytics-kpi.js` declares the constant on the same line as its other constants, so a grep for
`const APPS` alone does not show it; the second command does. All five files that link to Connected
apps now point at `/app/apps`.

```
$ node --check web/feat/analytics-kpi.js        ->  ok
$ node --check web/feat/analytics-realtime.js   ->  ok
$ node --check web/feat/analytics-shorts.js     ->  ok
$ node --check web/feat/analytics-traffic.js    ->  ok
$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
```

Served copies from the running server on http://127.0.0.1:8798, so the fix is not only on disk:

```
$ python -c "... GET /assets/feat/<name>.js, find APPS ..."
analytics-kpi 200 APPS = ['/app/apps']
analytics-traffic 200 APPS = ['/app/apps']
analytics-shorts 200 APPS = ['/app/apps']
analytics-realtime 200 APPS = ['/app/apps']
```

`api_analytics.py` and `studio/server.py:1617` still redirect to `/app/settings/apps` after a
connection is made. That address still resolves and still shows the right form, because after a real
connection the redirect carries `?connected=youtube` and the app reads it. I did not touch it: it is a
server redirect, not one of the four links, and `tests/test_connect.py:122` asserts that exact string.

---

## Important 2. Lifetime sent a day count the routes refuse

**The finding.** `analytics.js:39-42` builds Lifetime as 1 January 2005 to today, which is 7994 days.
`analytics-audience.js` sent that number to `/api/analytics/audience`, declared
`days: int = Query(28, ge=0, le=3650)` at `studio/api_analytics.py:328`. FastAPI answers 422 with a
list in `detail`, and `api()` turns a non-string detail into "Something went wrong".
`analytics-kpi.js` sent the same 7994 to `/api/analytics/summary` and hit the same 422.

**What I changed.** One clamp in each of the two files that send the number, written the way
`analytics-charts.js:72` and `analytics-retention.js:140` already do it, so the site has one shape.

```
web/feat/analytics-audience.js  days()      Math.round(n)  ->  Math.min(3650, Math.round(n))
web/feat/analytics-kpi.js       asked()     days: pick(...)  ->  days: d === null ? null : Math.min(3650, Math.round(d))
```

The `d === null ? null : ...` guard is needed because `Math.round(null)` is `0`, and `0` is a real
value on this route (it means "everything"), so a missing count must not become 0. I did not touch
the other models the review listed as already correct.

**Proof.** The live route, before and after the number the page now builds:

```
$ python -c "GET /api/analytics/audience?days=..."
422 days=7994 {"detail":[{"type":"less_than_equal","loc":["query","days"],...
200 days=3650 {"source":"peakcut","days":3650,"start":"2016-11-23","end":"2026-11-20",...
200 days=28 {"source":"peakcut","days":28,"start":"2026-10-24","end":"2026-11-20",...
```

The real `days()` and the real `asked()`, lifted unchanged out of the two files and run on a Lifetime
range, then on a 28 day range:

```
$ node /tmp/pkfix/probe_audience.js
Lifetime -> days = 3650 | within le=3650: true
Last 28 days -> days = 28 | within le=3650: true
Last 365 days -> days = 365 | within le=3650: true

$ node /tmp/pkfix/probe_kpi.js
Lifetime path built: /api/analytics/summary?start=2005-01-01&end=2026-11-20&days=3650
start = 2005-01-01 | end = 2026-11-20 | days = 3650
days within the route le=3650: true
28 day query keeps days=28: 28
```

Both routes answer the exact query that is now built:

```
$ python -c "GET /api/analytics/summary?start=2005-01-01&end=2026-11-20&days=3650"
status 200
top-level start/end: 2016-11-23 2026-11-20
```

`docs/INSIGHTS.md` said the Lifetime choice "can leave those cards dashed with a sentence". That is
no longer true, so the bullet now says what actually happens: the routes take at most 3650 days, so
Lifetime covers the last ten years rather than every year the channel has existed. That is a limit a
reader can see on the screen, and it is not hidden.

```
$ node --check web/feat/analytics-audience.js   ->  ok
$ node --check web/feat/analytics-kpi.js        ->  ok
$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
```

The key number row still prints the range the server itself reported (`b.range`, else `b.start` and
`b.end`), so with the clamp it reads "23 Nov to 20 Nov"-style server dates rather than the 2005 label.
The row does not claim a span the numbers do not cover.

---

## Minor 3. Two panels labelled a window the route did not use (Traffic half fixed)

**The finding.** `analytics-table.js:199` sends `from` and `to` to `/api/analytics/videos`, which
`studio/api_analytics.py:272` declares as `days` and `limit` only, so the answer is always 28 days.
`analytics-table.js:170` still writes "Every number covers <from> to <to>".
`analytics-traffic.js:63` does the same: it sends `start` and `end` to a route that reads `days`;
`analytics-traffic.js:119` then shows the shell's range in the pill.

**What I changed.** The Traffic half only, one line, because the route does send its own dates back
and the pill simply was not reading them:

```
web/feat/analytics-traffic.js:95
  -  const out = {rows, range: rangeOf(b.range)};
  +  const out = {rows, range: rangeOf(b.range || b)};   // the route answers a day count, so read its own dates
```

**Proof.** The real `rangeOf()`, run against the route's real answer, before and after:

```
$ node /tmp/pkfix/probe_traffic.js
route sends start/end: 2026-10-24 2026-11-20 days: 28
pill AFTER fix (rangeOf(b.range || b)): 24 Oct to 20 Nov
pill BEFORE fix (rangeOf(b.range))     :
```

Before the change the pill fell through to an empty string, so a person saw the pill blank. Now it
prints the window the numbers actually cover.

```
$ node --check web/feat/analytics-traffic.js   ->  ok
$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
```

**What I did not change, and why.** The Content table half is not a one-line fix. The route reads
`days`, but `analytics-table.js` works in real dates taken from the shell range and its own picker,
and it has no day count to send. Making that honest means either teaching the route `from`/`to` in
`studio/api_analytics.py` (a server change, outside this task) or mapping the two dates to a day count
in the table, which changes what the table asks for and how its picker behaves. Either one is a
change larger than "as little as possible", so the sentence at `analytics-table.js:170` still names
dates the answer does not use.

`docs/INSIGHTS.md` documented both halves together, so fixing Traffic made that bullet wrong. It now
says the Content table is the one that answers a 28 day window while naming the dates you picked, and
that the Traffic pill shows the window its answer covers:

```
- The Content table and the Traffic tab send dates. Those two routes read a day count instead, so both answer
- a 28 day window whatever the header says.
+ The Content table sends dates. That route reads a day count instead, so the table answers a 28 day window
+ while its sentence names the dates you picked. The Traffic tab sends dates too, but its pill now shows the
+ window the answer covers, so the two numbers on that tab agree.
```

That is a doc line, not code, and leaving it would have made the doc describe a defect that no longer
exists on one of the two tabs.

---

## Minor 4. The dash was three different characters

**The finding.** `analytics-trends.js:14` used a plain ASCII `-`. Three files wrote a literal U+2013
and five wrote the escaped `"\u2013"`. `analytics-audience.js` was not in the review's list but used
a plain ASCII `-` in three places.

**What I changed.** The value is the same character everywhere now; only the source spelling differs,
and that is fine because the spelling is what the file's other constants already used.

```
web/feat/analytics-trends.js:14   DASH = "-"   ->  DASH = "\u2013"
web/feat/analytics-audience.js    added  const DASH = "\u2013";
                                  three placeholders  "-"  ->  DASH
```

The three Audience placeholders were `show()` at line 35, `pc()` at line 73 and the `aa-pct` span at
line 110. The constant itself sits at line 32.

**Proof.** Every file's dash constant, with its codepoint read out:

```
$ python -c "...read the dash constant from each analytics file, print spelling and codepoint..."
analytics-trends     escaped \u2013       U+2013
analytics-kpi        '–'                  U+2013
analytics-traffic    '–'                  U+2013
analytics-realtime   escaped \u2013       U+2013
analytics-shorts     escaped \u2013       U+2013
analytics-revenue    escaped \u2013       U+2013
analytics-table      escaped \u2013       U+2013
analytics-compare    '–'                  U+2013
analytics-audience   escaped \u2013       U+2013
```

Nine files, one character. Two spell it as a literal and the rest escape it, which was already true
before this change and is not worth rewriting.

And no ASCII dash placeholder is left in the analytics files:

```
$ grep -n '? "-"' web/feat/analytics-*.js
[grep exit: 1]
```

The two files whose dash changed, and the gate, still pass:

```
$ node --check web/feat/analytics-trends.js     ->  ok
$ node --check web/feat/analytics-audience.js   ->  ok
$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
```

---

## Minor 5. The route gate could not see a DELETE

**The finding.** `tests/test_insights_pages.py:25` matched only `@router.get` and `@router.post`, so
`@router.delete("/api/trends/saved")` at `studio/api_trends.py:364` was invisible, and the test leaned
on a GET and a POST on the same path. The page does call DELETE (`analytics-trends.js:364`), so the
gate was passing for the wrong reason.

**What I changed.** One word in the pattern.

```
tests/test_insights_pages.py:25
  -  @(?:router|app)\.(?:get|post)\(
  +  @(?:router|app)\.(?:get|post|delete)\(
```

**Proof.** The same scan with the old and the new pattern over `studio/*.py`:

```
$ python -c "...count paths each pattern finds, and which paths only the new one sees..."
old pattern paths: 130 | new pattern paths: 134
/api/trends/saved in old: True | in new: True
paths only the new pattern sees: ['/api/accounts/{aid}', '/api/creators/{cid}', '/api/jobs/{jid}/clips/{cid}', '/api/upload/{upid}']
```

That second line is the whole point. The old pattern did see `/api/trends/saved`, but only because
a GET and a POST sit on the same path. The DELETE itself was never matched, so the test would have
passed even if the page had called an address no route served.

What the fix actually adds is four paths that are reachable by DELETE alone:

```
$ python -c "...list the methods on each route..."
/api/trends/saved methods: ['DELETE', 'GET', 'POST']

/api/accounts/{aid}              ['DELETE']
/api/creators/{cid}              ['DELETE', 'PUT']
/api/jobs/{jid}/clips/{cid}      ['DELETE']
/api/upload/{upid}               ['DELETE']
```

The suite still passes, and the Trends row still names the three paths it fetches:

```
$ python tests/test_insights_pages.py
ok   analytics-trends.js fetches only routes this server has   /api/trends/saved, /api/trends/searches, /api/trends/videos
ok   no Insights file hard-codes an origin   all paths are relative

All checks passed. 80 ok
```

---

## Note. CSV cells starting with a minus were not prefixed

**The finding.** `analytics-export.js` prefixed `'` to cells starting `=`, `+` or `@` but not `-`, so
a negative number opened as a formula in a spreadsheet. The review filed this as a note rather than a
finding, and it is one character.

**What I changed.**

```
web/feat/analytics-export.js   if (/^[=+@]/.test(s))   ->   if (/^[=+@-]/.test(s))
```

**Proof.** The real `cell()` lifted out of the file and run twice, once with the old pattern put
back in memory, so the difference is the change and nothing else:

```
$ node -e "...run the cell() from the file, then the same body with /^[=+@]/ restored..."
"=1+1"       before: "'=1+1"      after: "'=1+1"
"-42"        before: "-42"        after: "'-42"
"-3 views"   before: "-3 views"   after: "'-3 views"
"Total"      before: "Total"      after: "Total"
```

Now the full behaviour of the shipped version, on the inputs that decide it:

```
$ node -e "...eval the cell() from the file..."
"=1+1"       -> "'=1+1"
"+1"         -> "'+1"
"@x"         -> "'@x"
"-42"        -> "'-42"
"-3 views"   -> "'-3 views"
"Total"      -> "Total"
"a,b"        -> "\"a,b\""
```

A plain word is still written unquoted, and a comma is still quoted, so nothing else changed.

```
$ node --check web/feat/analytics-export.js   ->  ok
```

---

## Minor 7. The docs said only Trends has no Export button

**What I changed.** One bullet in `docs/INSIGHTS.md`, corrected to what `analytics-export.js:56-62`
does: the button is dropped on Trends, and also on Audience and Traffic, because `OWN` is
`["overview", "content"]` and those two tabs hold no rows for the file to read.

```
- Export ... Trends holds no rows, so it has no button.
+ Export ... It has no button on a tab that holds no rows: Trends, and Audience and Traffic, which draw no table.
```
This is a documentation correction with no code behind it; the code was already right.

---

## Minor 6 and the two dead-code notes: not changed

**Minor 6** (`tests/test_feat_files.py:92-99` only checks escaping where `${` appears inside
`innerHTML =` or `insertAdjacentHTML(`) is a gap in the test's reach, not a bug in a page. Closing it
means teaching the gate a second shape, which is a change to the shared gate every one of 37 files is
checked by. That is not "as little as possible", and the review itself verified the five `put()` files
by hand and found them escaped.

**The dead fallbacks** at `analytics-retention.js:78` and `analytics-table.js:122` (`if (typeof
P.api === "function") return P.api(path);` then a `fetch`) are unreachable, because `api()` is a
`const` in the page script and always present. Removing them is not a fix to a defect: they are a
second way to fetch that costs nothing and never runs. I left them rather than widen the diff.

**The private `ytstats._videos` call** at `studio/api_trends.py:295` carries `noqa: SLF001` on
purpose and is covered by the backend agent's own file. I did not touch another agent's file.

---

## Final gates, run after the last change

```
$ node --check web/feat/analytics-audience.js  ->  ok
$ node --check web/feat/analytics-export.js    ->  ok
$ node --check web/feat/analytics-kpi.js       ->  ok
$ node --check web/feat/analytics-traffic.js   ->  ok
$ node --check web/feat/analytics-trends.js    ->  ok

$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.

$ python tests/test_insights_pages.py
All checks passed. 80 ok

$ python tests/test_menu_pages.py
All checks passed. 142 ok

$ python tests/test_trends_api.py
All checks passed. 8 ok
```

`web/index.html` was not edited and `git` was not run. The nine files named at each finding above are
the only files changed: seven feature files, one test file and one doc. The probe scripts live in the
temp folder, outside the repo.
