# learn-report

## What I built

`studio/learn_report.py`, one shape that describes a learning round so no page has to guess.

- `shape(round_doc, previous=None) -> dict` returns the thirteen promised keys, every one present and
  never `None`: `at`, `when`, `days`, `source`, `facts`, `changes`, `dropped`, `applied`, `saying`,
  `effect`, `moved`, `reading`, `undone`. A change with no recorded `from` becomes `"not set"` so the
  page can print a sentence. A change row has `setting`, `from`, `to`, `why`, `expect`; a dropped row
  has `setting`, `value`, `reason`; an applied row has `setting`, `value`, `ok`, `from`, `to`.
- `story(row) -> str` turns a round into one readable paragraph: what was read and when, what was
  seen, what changed, and whether the change before it worked. An empty round says
  `Nothing has run yet.` A round that recorded a proposal but nothing applied says so in words.
- `table(rounds) -> {"head": [...], "rows": [[...]]}` with the columns `when`, `days`, `source`,
  `changed`, `effect`; every cell is a string, so the same rows feed the page and the Insights CSV.
- `when(at) -> str` gives a time the way a person says it. It tries `learn._ago` first, imported inside
  the function so the two modules cannot wait on each other, and falls back to an identical local
  version if that import fails. It never returns an empty string.

Every public function returns its empty shape instead of raising, including on a string, a list, a
not-a-number and an infinite number. Nothing here reads a database, calls an AI or changes a setting.

## The file I own

`studio/learn_report.py`. I edited no other file.

## The exact command and its output

```
$ cd /c/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut
$ python -m py_compile studio/learn_report.py
```

It printed nothing and exited 0. With `&& echo "COMPILE_OK"` appended it printed `COMPILE_OK`.

The behaviour check, run the same way:

```
$ python -c "import time; from studio import learn_report as R; ..."
empty shape keys: 13 True
empty story: Nothing has run yet.
when(0): at an unknown time
when(now): 5 minutes ago
from becomes: not set
story: PeakCut read the last 28 days from youtube 2 h ago. It saw Views up 50 percent, from 1000 to
1500. It changed clip_len from not set to 30, because shorter clips held people. Against the round
before, views up 20 percent, from 1200 to 1440.
table: {"head": ["when", "days", "source", "changed", "effect"], "rows": [["2 h ago", "28", "youtube",
"clip_len from not set to 30", "Views rose."], ["at an unknown time", "0", "not known", "nothing",
"not known yet"]]}
bad input: 0.0 Nothing has run yet. {'head': [...], 'rows': []}
```

A second check asserted that eight bad inputs (`None`, a list, a string, an int, `{"at": "soon"}`,
`{"changes": "no"}`, `{"applied": [1, 2]}`, `{"reading": []}`) all give thirteen keys with no `None`
value, and printed `all shapes complete and non-None`.

A style check confirmed there is no em dash, no en dash, no non-ASCII character in the file, and that
all four public functions have docstrings.

## What I could not do

- I did not run `python tests/run.py`. It starts a throwaway server and was outside what one file
  owner in this wave should spend the time on; I only checked that `tests/test_learn.py` and
  `studio/learn.py` still compile beside the new module.
- Nothing imports `studio/learn_report.py` yet. The three wire owners (`learn.py`, `api_learn.py`,
  `learn.js`) have to call it; until then `GET /api/learn/state` and the Improve page still show the
  raw round records.
- `shape` pairs `changes` with `applied` by position first and by setting name second. That matches
  how `learn.run` and `learn._apply` write them, but a hand-written record where the same setting
  appears twice in one round could pair the wrong two. No such record exists in the current writer.
- `moved` is only recomputed from two readings when the record did not keep its own `moved` list; that
  needs `previous` to carry a `reading`. Otherwise the field is an empty list and `story` says there is
  nothing to compare yet, rather than guessing.
- The `table` columns are fixed to the five the brief named. It does not include the dropped proposals,
  so a CSV reader cannot see that a change was refused.
