# Prover, wave 2

## What I built

Nothing in `web/` and nothing in `studio/`. My task was proof, so the deliverable is one document:
`docs/swarm4/wave2/PROOF.md`.

It records, with its literal output and a PASS or FAIL beside it, each of these:

1. `python tests/test_feat_files.py`
2. `python tests/test_menu_pages.py`
3. `python tests/test_insights_pages.py`
4. `python tests/test_trends_api.py`
5. `python tests/test_analytics_api.py`
6. `python -c "import studio.server"`
7. `node --check` on every file in `web/feat/` (38 files)
8. `curl -s http://127.0.0.1:8798/healthz`
9. `curl` of every `/api/analytics/*` and `/api/trends/*` route (13 routes)

All ten are PASS. PROOF.md carries the exact text each command printed, not a summary of it.

The output in PROOF.md is not retyped by hand. Each gate wrote its output to a file under
`.pctest/proof2/out/`, and `.pctest/proof2/build_proof.py` copies those files into the document.
That was deliberate: a proof document people have to trust cannot depend on me copying a line right.

## Skill I loaded

`python-testing`. It shaped how I read the results: run each gate as its own thing, look at the exit
code as well as the words, and treat a test that only prints "ok" as evidence only when the runner
also says how many checks it made. `tests/test_feat_files.py` prints `{"files": 37, "checks": 302}`,
which is why the document can say 302 checks rather than "some checks".

## The exact files

| File | What it is |
|---|---|
| `docs/swarm4/wave2/PROOF.md` | The deliverable. Gate results with literal output. |
| `.pctest/proof2/prove.sh` | The script that ran the curls, so the same list can be run again. |
| `.pctest/proof2/build_proof.py` | Builds PROOF.md from the captured output files. |
| `.pctest/proof2/out/*.txt` | What each gate printed, as it printed it. |
| `.pctest/proof2/trends.backup.json` | The saved-terms file as it was before the write test. |

I did not edit `web/index.html`, any file in `web/feat/`, or any file in `studio/`. I read them.

## Commands I ran, and what they printed

The full text is in PROOF.md. The short version:

```
$ python tests/test_feat_files.py
...
{"files": 37, "checks": 302}
All checks passed.
[exit 0]

$ python tests/test_menu_pages.py
All checks passed. 142 ok
[exit 0]

$ python tests/test_insights_pages.py
All checks passed. 80 ok
[exit 0]

$ python tests/test_trends_api.py
All checks passed. 8 ok
[exit 0]

$ python tests/test_analytics_api.py
All checks passed. 29 ok
[exit 0]

$ python -c "import studio.server"
[exit 0, printed nothing]

$ for f in web/feat/*.js; do node --check "$f"; done
checked 38 files, 0 failed
[exit 0]

$ curl -s http://127.0.0.1:8798/healthz
{"ok":true}  [http 200]
```

The eleven read routes answered 200 except `/api/analytics/retention`, which answered 400 twice.
That route cannot answer without a video id, and cannot answer at all without a connected channel.
Both refusals are sentences a person can read:

```
/api/analytics/retention                  400  {"detail":"Paste a YouTube link or a video id."}
/api/analytics/retention?video=dQw4w9WgXcQ 400  {"detail":"Retention comes from YouTube. Connect a channel under Connected apps."}
```

I did not score that as a failure, because it is the route doing what it was written to do, and
`tests/test_analytics_api.py` exercises the same guards and passed. PROOF.md says so in the words
beside the result rather than hiding it.

## The server was already running, so I left it alone

Port 8798 was in use before my first command. The owner is python, PID 29352, started 05:48:18,
about half an hour before I began. My instructions were to never leave a server on a port that was
already in use, so I did not start one, did not restart this one, and did not stop it. It is still
running now, serving the same process it was serving when I arrived. `.pctest/start.sh` was read but
not run, because there was nothing to start.

## The two write routes, and putting the file back

`POST` and `DELETE` on `/api/trends/saved` are the only routes in my list that write. They write
`data/users/u_local/trends.json`. I backed that file up before touching it, added one term, read it
back, deleted it, read it back again, and then compared the file with the backup:

```
$ diff .pctest/proof2/trends.backup.json data/users/u_local/trends.json
[diff exit=0]
```

No output and an exit of 0 means the two files are the same. The real file is back to `{"terms": []}`.
I also confirmed the blank-term refusal still answers `{"detail":"Type a search term first, then save it."}`
with 400, so the guard did not get loosened by my poking at it.

## What I checked beyond the gate list

The gates prove the files are valid. They do not prove the page runs them. So I loaded
`/app/analytics` in a browser and looked:

- `window.PeakCut._order` held all 37 features, including every `analytics-*` file.
- All five tabs (Overview, Content, Audience, Trends, Traffic) drew content when clicked.
- Changing the range from 28 days to 7 redrew the page and it read
  `Showing 14 Nov 2026 to 20 Nov 2026. The page is set to Last 7 days.`
- The Trends tab fetched `/api/trends/searches`, `/api/trends/videos` and `/api/trends/saved`, and
  all three came back 200.
- The console stayed empty the whole time.

I also checked every 200 route that returns numbers carries `start` and `end`. They all do, except
`status` (which carries its own note instead) and `saved` (a list of words, no numbers). No page is
showing a number without a date range.

## What I could not do

- **The retention curve with real points.** It needs a YouTube account connected, and none is. I
  proved the guard instead. That is the most this machine can prove about that route.
- **YouTube's own numbers.** Every figure on this install is PeakCut's own, because
  `peakcut/data` has no connected channel. The YouTube branch of each route was only exercised
  through its refusal path.
- **Comparing against a pre-wave-2 baseline.** There is no earlier PROOF.md for wave 2 to diff
  against, so this document records the state as it is now, not a change from something.

## Anything a reviewer should look at

1. `tests/test_trends_api.py` prints 8 ok and `tests/test_analytics_api.py` prints 29 ok. Those are
   lower than the feature-file counts because they are API tests with one check each, not because
   coverage is thin. Worth a glance if the reader expects the numbers to match.
2. The 400 on `/api/analytics/retention` is the one result a reader could mistake for a failure.
   PROOF.md explains it directly under the block so it cannot be misread.
3. `.pctest/proof2/` is scratch space I created. If the workspace is meant to stay clean, that folder
   can go once PROOF.md has been read. PROOF.md itself does not depend on it.
