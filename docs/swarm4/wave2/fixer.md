# fixer, wave 2

## Skill loaded

`code-review`. It is a review guide (Standards axis plus Spec axis), so it shaped how I read
`REVIEW.md` and how I checked each fix against the contract. It is not a fixing guide, and nothing in
it told me what to change.

## What this task was

Read `peakcut/docs/swarm4/wave2/REVIEW.md`, fix every critical and important finding in the file that
owns it, changing as little as possible, and leave the minors alone unless each is one line. Run
`node --check` on each touched file and `python tests/test_feat_files.py` after each fix. Write
`FIXES.md` with the proof.

The review found no critical issues. It found two important ones, five minors, and four notes.

## Files I changed

Feature files, one small change each:

- `peakcut/web/feat/analytics-kpi.js` line 25 (the Connected apps address) and line 97 in `asked()` (the day clamp)
- `peakcut/web/feat/analytics-realtime.js` line 43 (the address)
- `peakcut/web/feat/analytics-shorts.js` line 30 (the address)
- `peakcut/web/feat/analytics-traffic.js` line 20 (the address) and line 95 (the range pill)
- `peakcut/web/feat/analytics-audience.js` lines 32, 35, 73, 110 (one dash constant) and line 216 (the clamp)
- `peakcut/web/feat/analytics-trends.js` line 14 (the dash)
- `peakcut/web/feat/analytics-export.js` `cell()` (a minus sign is a formula character too)

Tests and docs:

- `peakcut/tests/test_insights_pages.py` line 25 (the route pattern now sees DELETE)
- `peakcut/docs/INSIGHTS.md` lines 94, 106-110 and 111-112

Written, not just edited:

- `peakcut/docs/swarm4/wave2/FIXES.md`
- `peakcut/docs/swarm4/wave2/fixer.md` (this file)

`peakcut/web/index.html` was not touched. No file belonging to another agent was touched. `git` was
not run. The probe scripts I used live in the temp folder, outside the repo.

## The findings, in short

1. **Important, wrong address.** Four files sent people to `/app/settings/apps` for "Connected apps".
   That path lands on Settings with an unknown tab, and the tab fell back to Profile, so the Connect
   button was not there. All four now use `/app/apps`, which is the page registered for exactly this
   (`web/feat/menu-pages.js:185`). The same wrong address in `docs/INSIGHTS.md` is fixed.
2. **Important, Lifetime broke two tabs.** Lifetime is 7994 days and the routes take at most 3650, so
   the Audience tab and the key number row got a 422 and printed nothing useful. Both now clamp to
   3650, the way four other files in the wave already do. The key row guard keeps a missing count
   missing instead of turning it into 0, which is a real value on these routes.
3. **Minor, Traffic half only.** The Traffic pill showed the shell's range while the route answered a
   28 day one; it now reads the dates the route sends back. The Content table half is not a one-line
   change and is explained in `FIXES.md`.
4. **Minor, one dash.** Two files used an ASCII `-` where six others used the same dash character.
5. **Minor, a blind gate.** `test_insights_pages.py` could not see a DELETE route, so the Trends page
   was passing on a GET and a POST that happened to share the path. One word in the pattern.
6. **Minor, not done.** The escaping gate only looks at two shapes of `innerHTML`. Closing that means
   changing the gate all 37 feature files are checked by.
7. **Minor, docs.** The Export bullet said only Trends has no button; Audience and Traffic have none
   either. Corrected to what `analytics-export.js:56-62` does.
8. **Notes.** One was a real one-line fix (a CSV cell starting with `-`), so I took it. The other three
   are not defects and I left them.

## What I ran, and what it said

Before any edit, to know the starting point, all exit 0:

```
$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
$ python tests/test_insights_pages.py        ->  All checks passed. 80 ok
$ python tests/test_trends_api.py            ->  All checks passed. 8 ok
```

After each fix, on that file:

```
$ node --check web/feat/analytics-kpi.js         ->  ok
$ node --check web/feat/analytics-realtime.js    ->  ok
$ node --check web/feat/analytics-shorts.js      ->  ok
$ node --check web/feat/analytics-traffic.js     ->  ok
$ node --check web/feat/analytics-audience.js    ->  ok
$ node --check web/feat/analytics-trends.js      ->  ok
$ node --check web/feat/analytics-export.js      ->  ok
$ python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
```

Final run, after the last change, all exit 0:

```
$ node --check web/feat/analytics-audience.js  ->  ok
$ node --check web/feat/analytics-export.js    ->  ok
$ node --check web/feat/analytics-kpi.js       ->  ok
$ node --check web/feat/analytics-traffic.js   ->  ok
$ node --check web/feat/analytics-trends.js    ->  ok
-----
{"files": 37, "checks": 302}
All checks passed.
-----
All checks passed. 80 ok
-----
All checks passed. 142 ok
-----
All checks passed. 8 ok
```

I also ran each fix against the live server on http://127.0.0.1:8798, because "the file parses" and
"the page gets the right answer" are different claims:

- `/api/analytics/audience?days=7994` answers 422 and `days=3650` answers 200. That is the bug, and it
  is why the clamp is 3650 and not something rounder.
- With the clamp in place, the real `days()` from the file turns Lifetime into 3650, 28 into 28 and
  365 into 365, and the real `asked()` builds
  `/api/analytics/summary?start=2005-01-01&end=2026-11-20&days=3650`, which answers 200.
- The real `rangeOf()` from `analytics-traffic.js` run on the route's real answer prints
  "24 Oct to 20 Nov". Before the change it printed nothing.
- The real `cell()` from `analytics-export.js` turns `-42` into `'-42` now, and still leaves `Total`
  alone.
- The four feature files are also served correctly by the running server: fetching each one from
  `/assets/feat/<name>.js` shows `APPS = ['/app/apps']`.

The probe scripts are in `C:\Users\Asus\AppData\Local\Temp\pkfix`, outside the repo. They read the
function text straight out of the shipping file and run it, so they test the code that ships and not a
copy of it.

## What I could not do

- **The Content table half of Minor 3.** The table sends `from` and `to`; the route reads `days`. The
  table has no day count, so making the sentence true means either teaching the route `from`/`to` in
  `studio/api_analytics.py`, or mapping two picked dates to a day count in the table. The first is a
  server change and the second changes what the table asks for. Both are bigger than "as little as
  possible", so I left the table alone. `docs/INSIGHTS.md` now says the Content table is the one that
  answers a 28 day window, so the reader is told rather than misled.
- **Minor 6.** Making the escaping gate see strings built and handed to `put()` is a change to the
  shared gate, not to a page. The review checked those five files by hand and found them escaped.
- **The two dead fetch fallbacks** are unreachable, so removing them would be tidying rather than
  fixing. I left them.
- **`studio/api_trends.py:295`** calls a private `ytstats._videos` with a `noqa` on purpose. That file
  belongs to the backend agent; I did not open the door to editing it.

## One thing worth passing on

The review was right about both important findings and I could reproduce each one before changing
anything. The one judgement call that is mine and not the review's: I also fixed `docs/INSIGHTS.md:94`,
which the review listed as part of finding 1 but which is a doc rather than one of the four code files.
It repeats an address a reader is told to visit, so leaving it would have sent people to the wrong
tab after the code was fixed. That is five files instead of four for one finding, which is the widest I
went.
