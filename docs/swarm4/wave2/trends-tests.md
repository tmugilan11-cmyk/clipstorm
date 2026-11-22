# Trends route tests

Agent: agent-49. Skill loaded: **python-testing**.

## What I built

`tests/test_trends_api.py`, a new standalone test script for `studio/api_trends.py`. Nothing else was
touched, and no file outside my task was changed.

I copied the setup from `tests/test_analytics_api.py` line for line, because those two routers are
mirrors of each other and their tests should be too:

- `PEAKCUT_DATA` points at `tests/trends-data`, this file's own folder, never the live server's data.
- `PEAKCUT_FETCH_MODEL=0`, `PEAKCUT_UPDATE_CHECK=0`, `PEAKCUT_ACCOUNTS=0`, so no download, no phone-home,
  and one built-in owner.
- `PEAKCUT_PUBLIC_URL=http://127.0.0.1:8765` and `BASE` the same, so nothing reaches the real 8798 server.
- `TestClient(server.app, base_url=BASE, follow_redirects=False)`, so a redirect shows up as a 3xx instead of
  being followed into a plausible 200.
- `db.init()` before the client is made.
- One tiny caller, `call(method, path, **kw)`, that wraps every request in `with ctx.as_user("u_local")`.
  The routes read the person off the request, so a request outside that block has nobody and the gate
  answers 403. `get(path)` is the one-line form of it.

The file is a plain script, not a pytest module, matching the other 33 test files in `tests/`: `main()`
collects every `test_*` callable, runs it, prints `ok` or `FAIL` per check, and exits 1 with the failed
names. It also happens to collect cleanly under pytest, which I checked as a bonus, not as a requirement.

### The eight checks

| Check | What it pins down |
|---|---|
| `test_every_route_answers` | All four GET routes answer 200 and none answers 404, so a renamed path cannot leave a card empty with no reason |
| `test_no_connection_is_an_empty_list_and_a_note` | No YouTube gives `connected false`, empty `rows`, an empty saved list, and a real sentence as the note. Also pins the date range: `days=28` is a 27 day span ending today, `days=0` is 3649 days |
| `test_a_saved_term_comes_back` | A saved term is trimmed, comes back in the reply, reaches `trends.json` on disk, is newest first, and a repeat in different case is one entry |
| `test_a_blank_term_is_refused` | Spaces, a missing key, null, a tab and newline, the number 0, a JSON array, a body that is not JSON, and a term past the 120 character cap all answer 400, and none of them stores anything |
| `test_a_saved_term_can_be_deleted` | Deleting removes the one term and keeps the rest, deleting a term that was never saved is a 200 no-op, and a delete with no term named is 400 that leaves the list alone |
| `test_a_junk_trends_file_still_answers` | Five broken files (half an object, terms as a string, null, empty, NUL bytes) all read as an empty list with a 200, and a hand-written bare list is still read with blanks and repeats dropped |
| `test_a_range_past_the_cap_is_refused` | `days=99999`, `days=-1`, `limit=999` and `limit=0` are refused with 400 or 422 rather than quietly served as something else |
| `test_google_refusing_a_connected_account_is_not_a_500` | A connected channel whose read is refused still answers 200 with no rows, the source says `youtube`, and the note is a sentence that is not the no-connection sentence |

That last one is the check I care about most. When a token is present but Google says no, the honest
answer is an empty table plus a reason. A 500 would leave the page with nothing to say, and a row of zeros
would be a number nobody sent. The test swaps `trends.ytstats.analytics` for a function that raises an
error carrying `code = 403`, swaps `accounts.youtube_token` for one that returns a token, and puts both
back plus `trends._CACHE.clear()` in a `finally`.

### Plainness rules in this file

Comments and assert messages are written for someone who does not program, matching the rest of the repo.
No em dash, no en dash, no emoji, no marketing words, and no exclamation marks. I ran a character audit on
the file to confirm: zero em dashes, zero en dashes, and no non-ASCII characters at all. There are exactly
two `!` characters, and neither is punctuation: the `#!` on line 1, and the `!=` in the `assert code != 404`
on line 103.

Every assert message names the value it got, so a failure tells you what happened without opening the file.

## What I ran, with the literal output

```
$ cd peakcut && python tests/test_trends_api.py
ok   test_every_route_answers
ok   test_no_connection_is_an_empty_list_and_a_note
ok   test_a_saved_term_comes_back
ok   test_a_blank_term_is_refused
ok   test_a_saved_term_can_be_deleted
ok   test_a_junk_trends_file_still_answers
ok   test_a_range_past_the_cap_is_refused
ok   test_google_refusing_a_connected_account_is_not_a_500

All checks passed. 8 ok
[exit 0]
```

Run from a completely empty folder, to be sure the empty-list checks mean something rather than reading a
file an earlier run left behind:

```
$ cd peakcut && rm -rf tests/trends-data && python tests/test_trends_api.py
ok   test_every_route_answers
ok   test_no_connection_is_an_empty_list_and_a_note
ok   test_a_saved_term_comes_back
ok   test_a_blank_term_is_refused
ok   test_a_saved_term_can_be_deleted
ok   test_a_junk_trends_file_still_answers
ok   test_a_range_past_the_cap_is_refused
ok   test_google_refusing_a_connected_account_is_not_a_500

All checks passed. 8 ok
[exit 0]
```

Collected by pytest as well, which shows the checks run independently and in isolation:

```
$ cd peakcut && python -m pytest tests/test_trends_api.py -q
........                                                                 [100%]
8 passed, 4 warnings in 2.06s
[exit 0]
```

The four warnings are FastAPI telling the app that `on_event is deprecated`. Two point at
`studio/server.py:55` and `:61` and two at FastAPI's own `applications.py:4930`. They were there before
this file and belong to the server, not to the test.

The two house gates and the neighbouring test, all still green after my change:

```
$ cd peakcut && python tests/test_analytics_api.py
All checks passed. 29 ok
[exit 0]
```

```
$ cd peakcut && python tests/test_menu_pages.py
All checks passed. 142 ok
[exit 0]
```

```
$ cd peakcut && python tests/test_feat_files.py
{"files": 37, "checks": 302}
All checks passed.
[exit 0]
```

`test_feat_files.py` matters here even though I wrote no page: this swarm has 18 agents writing at once,
and that gate is the shared proof that `web/` is still consistent. It was green before I started and is
green now.

What the folder holds afterwards, so a later run is not reading this run's leftovers:

```
$ cd peakcut && find tests/trends-data -type f
tests/trends-data/peakcut.db
```

No `trends.json` is left behind. Each check that writes one deletes it again at the end.

## Two mistakes I made and fixed

Writing this down because both were the kind of assert that passes for the wrong reason.

1. I asserted the refusal message was longer than 40 characters. It is not: "Type a search term first, then
   save it." is 39. The check failed honestly, and I replaced a length guess with what I actually meant,
   that the message is a sentence with words in it and is not a leaked `ValueError`.
2. I wrote a disk assertion that removed the term from the text before checking the term was not in it. That
   is true of any file. I replaced it with two assertions that can fail: the file exists, and the term is
   in it.

I also dropped a planned check that a missing route answers 404, because a 404 is exactly what a route that
failed to mount returns, and the test would have had no way to tell the two apart. `test_every_route_answers`
covers the intent instead, by requiring 200.

## What I could not do

- **`tests/run.py` does not run this file.** Its `runs` list is hardcoded pairs of name and arguments, not a
  folder scan, so a new test file is invisible to `python tests/run.py` until someone adds a line for it. The
  list starts at line 48 and ends at line 79 with
  `("a saved brand reaches the clip: look, length, sound, hook words", ["tests/test_brand_reaches_work.py"])`.
  The analytics test got a line at line 75,
  `("the analytics routes answer, with and without YouTube", ["tests/test_analytics_api.py"])`, so the shape
  to copy is exactly that. `run.py` is not one of my files, so I did not edit it. Until its owner adds
  `("the trends routes answer, with and without YouTube", ["tests/test_trends_api.py"])`, this coverage runs
  only when a person names the file, which is still how `test_analytics_api.py` gets run by hand.
- I did not test the six routes against a real YouTube account. Doing so needs a live token and spends the
  operator's quota, and the repo's own rule is that tests need no keys. The refused-token check covers the
  half of that path that can be exercised offline.
- I did not touch `studio/api_trends.py`. Two behaviours I noticed but did not change, because the file is
  agent-37's: a delete for a term that is not saved answers 200 rather than 404, and the 120 second cache
  means a save is visible on the next read only because the saved list is not cached. Both seemed
  deliberate, and my tests pin the behaviour as it is rather than as I might prefer it.
