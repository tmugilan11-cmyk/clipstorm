# signal-tests

## What I built

`tests/test_learn_signals.py`, the test file for wave 3's five new studio modules. It is a plain
script in the house style of `tests/test_learn.py` and `tests/test_brand_reaches_work.py`: no pytest,
a `check(name, got, want=True)` helper, `All checks passed. N ok` at the end, and exit code 1 when any
check fails.

It runs 97 checks across five sections. Each section is guarded by its own `try/except ImportError`
around the module import, and a missing module prints `SKIP <module>` and skips only that section,
so the other four still run.

What each section promises:

- **learn_signals** - a curve with real points writes a hook sentence that names "5 percent" and the
  share still watching; an empty curve writes empty strings and no number; `drop_off` finds the
  crossing at 25 percent on the sample curve and returns `{"at": None, "kept": None}` for two points
  or none; `hook_signal` and `length_signal` on 2 points stay silent; `signals()` on a video with no
  curve gives two empty sentences and zero points.
- **hookscore** - "you lose the rent money" scores 100 (strong) and the 15-word filler line scores 41,
  so the short concrete hook wins; an empty phrase scores 0, verdict weak, one reason; `compare` names
  the stronger phrase and quotes both scores; `suggest` never returns a phrase it was not given,
  keeps the strongest first, drops blanks, and returns nothing when asked for 0.
- **ai_arms** - `start` opens on arm a, `turn` flips to arm b, `applied` names `hook_words` on arm a
  and `clip_len` on arm b, `done` is False after one turn and True after two, and the record handed in
  is not mutated. One arm of readings under `learn.MIN_SAMPLE_VIEWS` says "inside the noise"; the same
  move above the limit does not; a trial with no reading or no view count is refused in words. A
  setting PeakCut cannot change raises `ValueError`.
- **learn_guard** - a day at the call cap is refused (`ok` False) with a sentence naming the cap and
  saying when it frees, never printing None; `report` speaks in whole numbers at the cap and on an
  unused day; `note` writes a round that `spent` then counts with its real time.
- **learn_report** - `shape({})` fills all 13 contract keys and none of them is None; `story({})` is
  the sentence "Nothing has run yet."; `when` never returns None or "" for 0, None, "", "not a time"
  or -5.

## The file I own

`tests/test_learn_signals.py` - created, nothing else edited.

## Exact commands and their literal output

```
cd peakcut && python -m py_compile tests/test_learn_signals.py; echo "[compile exit $?]"; echo "=== run ==="; python tests/test_learn_signals.py; echo "[run exit $?]"
```

```
[compile exit 0]
=== run ===

All checks passed. 97 ok
[run exit 0]
```

The SKIP path was verified by blocking two modules with a meta-path finder:

```
SKIP hookscore
SKIP learn_report

All checks passed. 59 ok

[exit 0]
```

## What I could not do, and what is left

1. **`learn_guard` is tested by stubbing `_rows`, not `spent`.** The brief says "with a stubbed
   `spent()` at the cap, `allow()` says no". `allow()` does not call `spent()` in the delivered code;
   it reads `_recent(_rows(uid))` itself and counts the rows. Stubbing `spent` would not change
   `allow()`'s answer, so the test would pass without testing anything. The record is stubbed with
   the exact rows `spent()` would have counted, which keeps the promise under test identical. If the
   wire agent changes `allow()` to call `spent()`, the stub should move there.
2. **`hookscore.score` on my filler line returns verdict "workable" at 41 points**, not "weak". The
   `WORKABLE_AT` threshold is 40, so that is correct behavior, but it means the test cannot assert
   the long filler is called weak. The test asserts what the code does: lower score, and the word
   count and filler reasons present.
3. **`learn_signals.curve()` is not exercised against a live curve.** It needs a YouTube token and a
   network call. The tests cover the pure functions (`drop_off`, `hook_signal`, `length_signal`,
   `signals`, `lines`) with hand-built points, and only check that a missing video gives the empty
   shape. A real YouTube response is untested here and belongs to whatever test the wire agent writes
   for `learn.py`.
4. **`learn_report.table()` is only checked by hand, not in the file.** It exists and returns its
   head with no rows for an empty history, but the brief did not list it, so I left it out to keep
   the file inside the budget.
5. **The AI arms sentence wording is asserted by substring, not exactly.** `read()` builds the
   sentence from `learn.compare`, so an exact match would break the moment the wording of a
   comparison changes in `learn.py`.
