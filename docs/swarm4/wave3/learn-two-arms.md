# learn-two-arms: two-arm trials

**Skill loaded:** `python-patterns`, one of the skills `docs/swarm3/CONTRACT.md` allows.

**Status:** done. The module imports, passes its own smoke test, and compiles.

## What I built

`studio/ai_arms.py` lets a round try one setting at a time and keep the order, so a change in the channel
numbers can be credited to one arm instead of a guess.

The problem it removes: `studio/learn.py` `run()` applies up to two changes in one round. When views move,
nobody can say which of the two did it. A trial here runs one setting, measures it, then runs the other.

How a trial goes:

1. `start("hook_words", "wait for it", "clip_len", "45")` writes the record down. Arm a is next.
2. `applied(trial)` returns the one change to apply, as `[{"setting": ..., "value": ...}]`, which is the
   shape a round already uses, so the caller hands it straight on.
3. After that arm has been measured, `turn(trial)` records that arm as run and flips to the other arm.
   The record handed in is copied, never changed, so the caller can keep the old one.
4. After the second arm, `turn()` again, and `done(trial)` is `True`.
5. `read(trial, before, after)` returns one sentence naming the arm that did better and quoting both view
   counts from `studio.learn.compare()`.

`ARMS` is `("hook_words", "clip_len")`, built from `learn.HOOK[0]` and `learn.LENGTH[0]` rather than typed
out, so it follows the engine if the engine renames them. Those two were picked because both are per-clip
values with no file behind them: a trial cannot fail because a look this machine cannot draw or a sound it
does not have was chosen. They also change different parts of a clip, so a move can be credited to one.
The wave's retention work points at the same two.

`read()` uses `learn.compare()` rather than growing a second opinion that could disagree with the Improve
page. A cut of what it actually says, run against the real module:

```
Arm b, which set clip length to 45 did better than arm a, which set hook words to "wait for it": Views up 125 percent, from 400 to 900.
Arm a, which set hook words to "wait for it" did better than arm b, which set clip length to 45: Views down 56 percent, from 900 to 400.
Arm b, which set clip length to 45 did better than arm a, which set hook words to "wait for it": Views up 50 percent, from 20 to 30, but both readings are under 50 views, so that difference is inside the noise.
Arm a, which set hook words to "wait for it" and arm b, which set clip length to 45 ended level on views at 400 each, so this trial does not say which setting is better, even though hours watched down 50 percent, from 2 to 1.
Only one arm of this trial has a reading, so PeakCut cannot yet say whether arm a, which set hook words to "wait for it" or arm b, which set clip length to 45 did better.
One of the two readings has no view count, so PeakCut cannot say whether arm a, which set hook words to "wait for it" or arm b, which set clip length to 45 did better.
```

The noise line is not a hard-coded 50. It reads `learn.MIN_SAMPLE_VIEWS` at call time, so the sentence and
the engine can never disagree about where noise starts.

Fail soft, as the rules require. A missing reading, both readings empty, a reading with no view count, a
complete failure of `learn.compare()`, a trial that is not a dict at all, and a junk value of `None`, `42`
or `[]` each produce a sentence instead of an exception. A module that cannot import `learn` still returns
the five setting names as plain words, so a trial can be written down while the engine is broken.

Nothing is written to disk, nothing is imported from `server.py` or any api module, and the only imports are
`from __future__ import annotations`, `time`, and `learn`. The setting names, the value ranges and the
sample limit stay in `learn.py`, where they already live, so there is one copy of each fact.

**One addition to the record you should know about.** `start()` returns the six keys you specified and one
more, `"runs": []`. Without it, a trial that has not started and a trial where both arms are finished look
identical, because both say `"arm": "a"`, and `done()` could not tell them apart. `turn()` appends to that
list. If you would rather the record stay exactly six keys, the flip alone cannot answer `done()` honestly,
so that key is load bearing.

## The file I own

`studio/ai_arms.py`, 315 lines. No other file was edited.

Public names: `ARMS`, `start`, `turn`, `applied`, `done`, `read`. Everything else is a private helper.

## The exact command I ran, and its literal output

```
$ cd C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut
$ python -m py_compile studio/ai_arms.py && echo "PY_COMPILE_PASS"
PY_COMPILE_PASS
```

Re-run on its own to show the exit code:

```
$ python -m py_compile studio/ai_arms.py; echo "exit=$?"
exit=0
```

`py_compile` prints nothing on success, so `PY_COMPILE_PASS` above is the echo, and `exit=0` is the code.

The module's own smoke test, also run:

```
$ python -c "from studio import ai_arms as A; ..."
ARMS = ('hook_words', 'clip_len')
arm  = a | keys ok: True
a applied = [{'setting': 'hook_words', 'value': 'wait for it'}]
done after start = False
arm  = b | b applied = [{'setting': 'clip_len', 'value': '45'}] | done = False
arm  = a | done = True
REFUSED: A trial needs two different settings. The same setting twice cannot say which change did it.
REFUSED: PeakCut does not change a setting called nope. The settings it can try are: style, hook_words, clip_len, sound, captions_always.
```

Repository suite, `python tests/run.py`, before and after my file existed. The same two groups fail both
times:

```
FAILED: queue under load, the new-version notice
```

With `studio/ai_arms.py` moved out of the tree entirely and the suite re-run, the verdict was byte for byte
the same. Neither failure names my module, and nothing in the repository imports it yet.

## Anything I could not do

**Two test failures that are not mine, reported not fixed** (the rules here are own one file, report the rest):

- `tests/test_load_queue.py:45`, `check("it sees a fully loaded processor", hot["cpu"] > 80 and hot["busy"], ...)`.
  It starts one burner per CPU, sleeps 18 seconds, then wants `cpu > 80`. On this machine it reads 37 while
  `busy_cpu` is 82 and `busy` is `False`, so the monitor sees the threshold but not the load. Run alone with
  `python tests/test_load_queue.py "$(pwd)"` it fails identically, so it does not depend on the rest of the suite.
  My guess is the burners are not getting the cores on this machine, but I did not prove that and did not
  touch the file.
- `tests/test_updates.py`, three checks: `this folder's own version is found`, `the version PeakCut started
  on is remembered`, and `...and only the one small question was asked`. Each expects a 40 character version
  string and gets `0` and `[]`. This folder is not a git checkout, so there is no commit to read. It is an
  artefact of where this copy sits, not a code fault.

**Not done, and deliberately:** I did not write a test for `ai_arms.py`. `tests/` has no file for it and the
brief gave me one file only. Whoever wires `learn.py` should add one. The smoke test above is what the
module has been held to so far.

**Not done, for the wire agents:** `learn.run()` still applies up to two changes in one round. Switching it
to call `start`, `applied`, `turn` and `done`, and to keep the trial record where the rounds are stored, is
that agent's change inside `studio/learn.py`, not mine. Until then this module is available but unused.
`read()` takes the two readings as arguments by design; it never fetches them, so no number here is one I
did not receive.
