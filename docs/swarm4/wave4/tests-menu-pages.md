# tests-menu-pages: the menu test now checks the seven new rows, their routes, and their escaping

Skill loaded before any other tool call: **python-testing**.

The file I own is `tests/test_menu_pages.py`. Nothing else was edited. I did not touch
`web/index.html`, `web/plugins.js`, another agent's `web/feat/*.js`, or `studio/*.py`.

## What I built

Three new check groups, appended to the file after the existing menu-row checks. Every
check prints `ok` or `FAIL` and the run ends either with `All checks passed. N ok` or with
`N check(s) failed` and one line naming each failure, then exit code 1.

### 1. The seven wave-4 rows are really in the menu

`WAVE4` names each row by the label a person reads in the sidebar, with the page name(s)
accepted for it:

    ("Creators", ("creators",)), ("Live", ("live",)), ("Schedule", ("schedule",)),
    ("Help", ("help",)), ("Clip formats", ("formats",)), ("Sounds", ("sounds",)),
    ("Usage", ("usage", "ai-usage")),

For each row: the page is registered somewhere, the file that registers it exists in
`web/feat/`, and that file has a `PeakCut.add(...)` registration. A row is looked up by
page name first, then by label, so a page can be renamed without the row silently
vanishing from this test's view. `Usage` accepts both `usage` and `ai-usage` because the
brief called that row `usage` while `web/feat/usage.js` registers the page as
`ai-usage`; the label `Usage` is what a person actually sees.

### 2. Every address a page asks for is a route the server answers

The test collects every `/api/...` string written anywhere in a feature file (not only
the ones passed to `P.api` / `P.send`, because several files build the path in a local
const first), then compares it to every route decorator in `studio/**.py`:

    @(?:app|router|api)\.(?:get|post|put|patch|delete|api_route)\(\s*["']([^"']+)["']

Matching rules, all of which the repo needs today:

- `?query` and `#fragment` are dropped before comparing.
- `${...}` counts as one segment of any name, so
  `/api/jobs/${encodeURIComponent(jid)}` matches `/api/jobs/{job_id}`.
- A segment in braces, on either side, matches any one segment.
- A path may also be the front of a longer real route, because pages concatenate onto a
  base: `P.api("/api/jobs/" + jid)` in `web/feat/peek.js` is checked against
  `/api/jobs/{job_id}`, not against a route that stops at `/api/jobs/`.

40 distinct addresses are checked, and all 40 resolve to a real route.

### 3. Pages escape what they interpolate into markup

Two checks per file that registers a menu page, deliberately narrow so the test does not
cry wolf and get ignored:

- If the file builds markup (a template literal containing `<`) it must call `esc(`
  somewhere. This catches a page that forgot the helper entirely.
- An interpolation that is a bare server-shaped field must not sit inside markup
  unwrapped. The shape is `\.(name|title|label|error|message|note|email|handle|text|why|
  say|tip|url|href|src|reason|detail|channel|user|platform|track|kind|status)\b`; an
  expression containing a call, `esc(` or `num(` is not flagged, because in this repo the
  escaping for those happens inside the helper (`cell(t.v, t.u, t.tip)` in
  `web/feat/analytics-traffic.js:110` escapes its own arguments). Plain locals that
  already hold escaped markup, numbers, and fixed strings are not flagged.

I chose this over "every `${...}` needs esc(" because that flagged 326 expressions across
the 47 feature files, almost all of them arithmetic or already-escaped locals, and a check
that fails on 300 true statements is worse than no check. I also did **not** require
`num(...)` for numbers: `num` is not a page global (it is a local helper inside a couple
of files), so demanding it would have failed the whole repo for a rule that does not
exist.

Because an icon can be added at run time, the icon set is the page's own map **plus**
every `PeakCut.icon("name", ...)` and every `{ icons: SET }` / `icons: X` object a feature
file hands the loader. Without that, `web/feat/help.js` looked broken: it uses
`icon: "help"`, and `help` is drawn by `web/feat/menu-icons.js` (`SET.help`, registered
through `P.icon(n, SET[n])`), not by the map in `index.html`.

## Routes the checked pages read

Every one of these is answered by `studio/`:

`/api/overview`, `/api/accounts`, `/api/creators`, `/api/formats`, `/api/captions/styles`,
`/api/style/preview`, `/api/hunt/live`, `/api/hunt/watching`, `/api/hunt/watch`,
`/api/hunt/unwatch`, `/api/autopilot/spec`, `/api/autopilot/preview`,
`/api/autopilot/install`, `/api/autopilot/remove`, `/api/schedule/preview`, `/api/moods`,
`/api/moods/prime`, `/api/usage`, `/api/learn/state`, `/api/learn/run`, `/api/learn/undo`,
`/api/learn/cost`, `/api/learn/arms`, `/api/learn/signals`, `/api/jobs`,
`/api/jobs/{id}`, `/api/jobs/{id}/clips/{id}/history`, `/api/preview`.

## What this file cannot do yet

- **It cannot tell whether an escaped value is escaped in the right place.** A page that
  calls `esc()` somewhere but wraps a server field in a URL attribute it does not escape
  still passes. The check is a smoke alarm, not a proof.
- **It does not check the words.** The brief asks for a plain-English `.hint` line under
  every control and for failure sentences instead of silent catches. Neither is
  mechanically decidable here, and a regex for "is this plain English" would be a
  guessing game. Those remain a human read.
- **It does not run the pages.** Nothing here proves a page draws at the live server on
  port 8798; it proves the file parses and the strings it uses exist. A page that fetches
  a real route and then throws still passes.
- **The route check trusts the shape, not the method.** `P.send(path, body, "DELETE")`
  against a route that only accepts GET passes here.
- **`/api/hunt/live` is matched only by its first segment.** `live.js` builds it as
  `"/api/hunt/live?platform=" + ...`, which is fine, but a page could ask for a route
  that exists with the wrong query names and this would not notice.
- **Two wave-2 fixes named in the brief are in files I do not own** and are not checked
  here: `analytics-table.js:199` sending `days`, `analytics-traffic.js:63` not labelling
  an unused window, the two em dashes in the analytics copy, and
  `tests/test_insights_pages.py:25` also seeing `@router.delete(`. I left all four alone
  rather than edit another agent's file.

## One thing I found and did not fix (not my file)

`web/feat/usage.js` registers a plug-in named `usage` but a menu page named `ai-usage`
(path `ai-usage`, nav `Usage`). That is legal today: `tests/test_feat_files.py` only
requires the plug-in name to match the file stem, and this file only requires the page to
exist and to have a label. It is worth a deliberate decision, because a future test that
assumes page name equals file stem would fail on this one row. My check accepts either.

## Commands I ran, and what they said

    $ python tests/test_menu_pages.py
    ...
    ok   the Creators row is in the menu
    ok   the Live row is in the menu
    ok   the Schedule row is in the menu
    ok   the Help row is in the menu
    ok   the Clip formats row is in the menu
    ok   the Sounds row is in the menu
    ok   the Usage row is in the menu
    ok   some page asks the server for something   40 addresses
    ...
    All checks passed. 312 ok
    exit=0

    $ python tests/test_feat_files.py
    {"files": 47, "checks": 382}
    All checks passed.

    $ for f in creators live schedule help formats sounds usage; do node --check web/feat/$f.js; done
    node --check web/feat/creators.js: OK
    node --check web/feat/live.js: OK
    node --check web/feat/schedule.js: OK
    node --check web/feat/help.js: OK
    node --check web/feat/formats.js: OK
    node --check web/feat/sounds.js: OK
    node --check web/feat/usage.js: OK

I also proved the new checks can fail, by copying the tree into a scratch folder inside
the workspace and breaking it three ways (then deleting the copy):

    - a page asking for /api/does-not-exist, interpolating ${row.name} into markup:
        FAIL route /api/does-not-exist exists
        FAIL bogus.js escapes what it puts in markup
        FAIL bogus.js escapes the server fields it names
    - the Help row's registration removed:
        FAIL the Help row is in the menu
        1 check(s) failed

Two mistakes of my own, for the record: the first draft had an unbalanced bracket in one
`check(...)` call (`SyntaxError: unmatched ')'`), and an earlier prototype crashed with
`re.PatternError: missing ), unterminated subpattern` because it passed the bare string
`"esc("` to `re.findall` instead of an escaped pattern. Both are fixed in the file as
shipped.
