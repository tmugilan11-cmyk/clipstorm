# Wave 3 review

Reviewer: agent-70. Read-only except for this file.
Skill used: `code-review`, called once. Its usual fixed point is a commit, and this project has
none: `git status --short` answers `fatal: not a git repository (or any of the parent directories): .git`,
and `docs/swarm3/CONTRACT.md:54` says "Do not run git. This is not a repo." So the change set is
defined by `docs/swarm4/WAVE3-BRIEF.md` plus the twelve reports in `docs/swarm4/wave3/`, and the
file list comes from those reports and from file mtimes (`2026-11-20 06:53` to `08:12`, plus one
later edit noted below).

Snapshot this review was measured against:

    studio/learn_signals.py               340 lines   14784 bytes  2026-11-20 07:48:52
    studio/hookscore.py                   248 lines   10250 bytes  2026-11-20 07:56:25
    studio/ai_arms.py                     315 lines   13836 bytes  2026-11-20 07:00:30
    studio/learn_guard.py                 191 lines    9220 bytes  2026-11-20 06:53:13
    studio/learn_report.py                293 lines   12914 bytes  2026-11-20 07:53:15
    studio/brand_ai.py                    364 lines   16361 bytes  2026-11-20 07:52:35
    studio/prompt_text.py                 122 lines    5196 bytes  2026-11-20 07:42:51
    studio/schedule_ai.py                 454 lines   19273 bytes  2026-11-20 08:12:14
    web/feat/learn-signals.js             228 lines    9992 bytes  2026-11-20 07:56:36
    web/feat/learn-arms.js                356 lines   16018 bytes  2026-11-20 08:08:30
    tests/test_learn_signals.py           329 lines   14664 bytes  2026-11-20 08:06:09
    studio/learn.py                       682 lines   30823 bytes  2026-11-20 07:56:32  (wired)
    studio/api_learn.py                   305 lines   13087 bytes  2026-11-20 07:57:34  (wired)
    web/feat/learn.js                     372 lines   19065 bytes  2026-11-20 08:39:21  (wired)

`web/feat/learn.js` was edited at 08:39 while this review was running: 18505 bytes became 19065 and
365 lines became 372, the wire agent adding an undo button at line 238. Every line number for that
one file in this review refers to the 08:39 snapshot, which I re-checked with `node --check` and
`tests/test_feat_files.py` after the edit. `web/index.html` also moved at 08:39:35, but it carries no
reference to the new panels (`grep -c "learn-signals\|learn-arms" web/index.html` finds none), so the
wave's page work is all in `web/feat/` as the contract requires. Everything else was stable throughout.

---

## The ten proofs

### 1. Compile every new file

    $ for f in studio/learn_signals.py studio/hookscore.py studio/ai_arms.py studio/learn_guard.py \
               studio/learn_report.py studio/brand_ai.py studio/prompt_text.py studio/schedule_ai.py \
               tests/test_learn_signals.py; do python -m py_compile "$f" && echo "OK  $f"; done
    OK  studio/learn_signals.py
    OK  studio/hookscore.py
    OK  studio/ai_arms.py
    OK  studio/learn_guard.py
    OK  studio/learn_report.py
    OK  studio/brand_ai.py
    OK  studio/prompt_text.py
    OK  studio/schedule_ai.py
    OK  tests/test_learn_signals.py

    $ for f in web/feat/learn-signals.js web/feat/learn-arms.js; do node --check "$f" && echo "OK  $f"; done
    OK  web/feat/learn-signals.js
    OK  web/feat/learn-arms.js

Both exit 0. Passing.

### 2. Every new module fails soft

Counted with an AST walk, not grep, so a `try` inside a string cannot inflate it. `raise X` means
a raise that constructs an exception; `bare-raise` means `raise` alone.

      file                    try  except  bare-raise  raise-N  empty-returns
      studio/learn_signals.py   11      11           0        0             14
      studio/hookscore.py        5       5           0        0              4
      studio/ai_arms.py          5       5           0        2              9
      studio/learn_guard.py      7       7           0        0              3
      studio/learn_report.py     7       7           0        0              6
      studio/brand_ai.py        11      11           0        0              3
      studio/prompt_text.py      4       4           0        0              6
      studio/schedule_ai.py      8       9           0        0              8

Every try has at least one handler. There are no bare raises anywhere. The only constructed raises
are two, both in `studio/ai_arms.py`, both deliberate refusal sentences:

    studio/ai_arms.py:96   raise ValueError(f"PeakCut does not change a setting called {name or 'nothing'}. ...")
    studio/ai_arms.py:99   raise ValueError("A trial needs two different settings. The same setting twice cannot say ...")

Both are caught by the route and turned into a 400 rather than a 500 (`studio/api_learn.py:261-264`),
which I proved live in proof 5 below. The JS matches: `learn-signals.js` has 5 try and 5 catch,
`learn-arms.js` has 4 try and 4 catch, and neither file contains a `throw` statement.

Behavioural check, not just shape. Fed garbage to the retention module:

    hook_signal(None) / "not a curve" / 42 / [{'at': 'x'}] / [None, None, None]
      -> "" and {'at': None, 'kept': None} every time, no exception
    signals("", 28, 0.0)
      -> {'hook': '', 'length': '', 'drop': {'at': None, 'kept': None}, 'points': 0}

And a real curve still produces its sentence:

    [{'at': 0, 'kept': 1.0}, {'at': 5, 'kept': 0.6}, {'at': 50, 'kept': 0.35},
     {'at': 90, 'kept': 0.31}, {'at': 100, 'kept': 0.3}]
      -> "At 5 percent in, 0.6 percent are still watching, 0.4 points below where the curve starts."

Passing.

### 3. An invented number

Found one, and it is the only Critical item in this review. See Critical 1.

### 4. `studio/learn.py` keeps its dry bypass, its six hour cooldown and its honest path

    $ python tests/test_learn.py 2>&1 | tail -3
    All checks passed. 103 ok

The cooldown, probed directly at `studio/learn.py:101-108`, with `ai.ready` stubbed True because
the function returns False for a missing key first and would otherwise mask the time rule:

    MIN_ROUND_SECONDS = 21600 = 6.0 hours
    a round just now               _may_run -> False
    1 second short of six hours    _may_run -> False
    exactly six hours              _may_run -> True
    six hours and one second       _may_run -> True
    no rounds ever                 _may_run -> True

Six hours exactly, and the comparison at `studio/learn.py:108` is `>= MIN_ROUND_SECONDS`.

The dry bypass, at `studio/learn.py:529`:

    526    # A preview changes nothing, so the wait between rounds does not apply to it. Asking "what would
    527    # you change?" and being told to come back in five hours is a refusal of a question that costs
    528    # nothing to answer, and it made the button look broken on a fresh install.
    529    if not dry and not _may_run(data):

and the writes are gated by `if not dry:` at `studio/learn.py:542`, `571` and `584`, so a preview
records nothing. Proved end to end through the API as well: `POST /api/learn/run {"days": 28, "dry": true}`
returns `applied: None` and leaves the round count at zero.

The honest path, `studio/learn.py:536-545`, when the numbers are not there:

    536    if not got["enough"]:
    537        # Not a failure: it is the honest answer. Nothing is asked of the AI, and nothing changes.
    ...
    545                   "effect": "Nothing was changed, so there is no effect to look for."}

and `studio/learn.py:582-583` keeps the effect as "Not known yet..." unless something actually moved.
Passing.

### 5. `studio/api_learn.py` still serves its three original routes

    $ python tests/test_learn_api.py 2>&1 | tail -3
    All checks passed. 39 ok

Route inventory, read from the file:

    57   @router.get("/api/learn/state")
    72   @router.post("/api/learn/run")
    103  @router.post("/api/learn/undo")
    188  @router.get("/api/learn/signals")
    224  @router.get("/api/learn/arms")
    239  @router.post("/api/learn/arms")
    275  @router.delete("/api/learn/arms")
    288  @router.get("/api/learn/cost")

The three originals are lines 57, 72 and 103, and `tests/test_learn_api.py:95-97` pins each as
"not a missing route". Five new route registrations were added on top.

I also exercised the new ones live, since no test does (see Minor 1):

    signals            200  {"hook": "", "length": "", "drop": {"at": null, "kept": null}, "points": 0}
    signals days=7     200  {"hook": "", "length": "", "drop": {"at": null, "kept": null}, "points": 0}
    signals days=abc   200  {"hook": "", "length": "", "drop": {"at": null, "kept": null}, "points": 0}
    arms get           200  {"trial": null}
    cost               200  {"calls": 0, "tokens": 0, "at": 0.0, "report": "8 of 8 rounds left today, and 60,000 of 60,000 tokens."}

    POST arms, target=style value=bold other=hook_words other_value=short
      -> 200 {"trial": {"at": ..., "target": "style", "value": "bold", "other": "hook_words",
                        "other_value": "short", "arm": "a", "runs": []}}
    GET  -> 200 the same trial
    DEL  -> 200 {"trial": null}
    GET  -> 200 {"trial": null}

    POST arms, nonsense setting
      -> 400 {"detail": "PeakCut does not change a setting called nothing. The settings it can try are: ..."}
    POST arms, the same setting twice
      -> 400 {"detail": "A trial needs two different settings. The same setting twice cannot say which change did it."}

`days=abc` and `days=999` both answer 200 with the empty shape rather than a 500, which is the
fail-soft rule holding at the doorway. Passing. Note for the lead: these probes ran against a
temporary data directory, and I confirmed afterwards that nothing under `data/` in the repo was
written by them.

### 6. The new JS passes `node --check` and the feat-file gate

    $ python tests/test_feat_files.py 2>&1 | tail -4
    ok   style-tiles.js invents no clashing id
    ok   loader keeps the documented folder
    {"files": 39, "checks": 318}
    All checks passed.

Re-run after the 08:39 edit to `learn.js`, same result. The count agrees with the server's own file
filter at `studio/server.py:460-462`, which serves 39 of the 40 files in `web/feat/` (the one it
skips is `_example.js`, on purpose). Both new files are in the served set and register themselves:

    web/feat/learn-signals.js:220  window.PeakCut.add("learn-signals", { after: { drawSettings(scope) { ... } } })
    web/feat/learn-arms.js:335     P.add("learn-arms", { ..., act: { laopen, lacancel, lastart, lastop, lareload } })

Passing.

### 7. No fastapi import in a module that is not an `api_` file

    $ grep -rn "^\(from fastapi\|import fastapi\)" --include="*.py" studio/ | grep -v "/api_"
    studio/asr_worker.py:17: from fastapi import FastAPI, HTTPException, Request
    studio/server.py:19: from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
    studio/server.py:20: from fastapi.concurrency import run_in_threadpool
    studio/server.py:21: from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

Both are pre-existing infrastructure, not wave 3 files: `studio/asr_worker.py` was last touched
2026-11-19 10:43 and `studio/server.py` 2026-11-20 05:00, before this wave's work started. None of
the eight new modules imports fastapi. The one mention in a new module is a comment explaining why
an import is deferred, at `studio/learn_signals.py:81`. Passing.

### 8. No em dash, no emoji, no marketing word

Scanned 25 files: the 8 new studio modules, the 2 new JS files, the 3 wired files, and all 12
reports in `docs/swarm4/wave3/`.

    files checked: 25   files with a problem: 0

Zero em dashes, zero en dashes, zero emoji (unicode category So), and zero hits for seamless,
powerful, effortless, unleash, revolutionary, game changer, cutting edge, world class, supercharge,
robust, leverage, empower, elevate, delight, blazing and magic.

The ten new files are pure ASCII. The only non-ASCII character in the wired set is one U+2026
HORIZONTAL ELLIPSIS at `web/feat/learn.js:240` ("Analysing…"), which five existing feat files
already use, so it is house style and not an emoji.

For the record, `docs/swarm4/WAVE3-BRIEF.md` itself carries six em dashes while
`docs/swarm4/CONTRACT.md:52` bans them. That is the brief's own text, predating the wave and not
code this review can change. Passing for everything wave 3 wrote.

### 9. No new dependency

`requirements.txt` is unchanged at 12 pins. Third-party names imported anywhere in `studio/` are
still only fastapi, httpx, numpy, soundfile, sqlalchemy and uvicorn, which is the set that was
already installed. Checked every new module's imports against `sys.stdlib_module_names`:

    studio/learn_signals.py   outside stdlib and package: nothing
    studio/hookscore.py       outside stdlib and package: nothing
    studio/ai_arms.py         outside stdlib and package: nothing (in-package: from . import learn)
    studio/learn_guard.py     outside stdlib and package: nothing
    studio/learn_report.py    outside stdlib and package: nothing
    studio/brand_ai.py        outside stdlib and package: nothing
    studio/prompt_text.py     outside stdlib and package: nothing
    studio/schedule_ai.py     outside stdlib and package: nothing

The two in-package imports are guarded: `studio/ai_arms.py:29-35` wraps `from . import learn` in a
try and falls back to `learn = None` with the comment "a broken engine must not stop a trial being
written down". Passing.

### 10. `tests/test_learn_signals.py`

    $ python tests/test_learn_signals.py 2>&1 | tail -3
    All checks passed. 97 ok

All four suites together, all exit 0:

    103 ok   tests/test_learn.py
     39 ok   tests/test_learn_api.py
     97 ok   tests/test_learn_signals.py
    318 checks across 39 files   tests/test_feat_files.py

---

## Critical

### C1. `studio/hookscore.py` claims the brief fixed numbers the brief never mentions

Three attributions, and one of them reaches a sentence a person reads.

    studio/hookscore.py:8    the 100, which is the promise the brief makes: plain but sound beats clever and broken.
    studio/hookscore.py:24   PENALTY_BARE_QUESTION = 45    # the brief names this as a failure on its own, so it has to cost real points
    studio/hookscore.py:29   WORDS_PER_SECOND = 2.5        # the reading rate the brief fixes; not a measurement of any person

and the sentence built from the third, at `studio/hookscore.py:179-180`:

    179   reasons.append(f"At {WORDS_PER_SECOND} words a second it takes about {seconds:.1f} seconds,"
    180                  f" past the 2 a hook must land in.")

Proof that the brief says nothing of the kind:

    $ grep -n "2\.5\|words a second\|words per second\|reading rate\|two second\|2 second\|bare question" \
            docs/swarm4/WAVE3-BRIEF.md
    (no output, exit 1)

    $ grep -rn "plain but sound\|clever and broken" docs/ studio/ | grep -v "\.pyc"
    studio/hookscore.py:8:the 100, which is the promise the brief makes: plain but sound beats clever and broken.

The brief's entire hook entry is three lines, `docs/swarm4/WAVE3-BRIEF.md:24-25` (the original carries
an em dash where this quote says [dash], which is the brief's own style and not wave 3 code):

    **A hook score** [dash] whether a phrase reads like a hook, so a hook can be judged without
    waiting for views. New file `studio/hookscore.py`.

There is no reading rate there, no two second deadline, and no mention of a bare question. The two
second figure is equally unsourced: `studio/hookscore.py:30` sets `TWO_SECONDS = 2.0`, and
`studio/hookscore.py:25-26` hard-code the same 2 and 3 again as penalty thresholds. Repo-wide,
"words a second", "words per second", "reading rate", "bare question", "plain but sound" and
"clever and broken" have no hits outside this one file and its own report.

The report carries the same error, so it cannot be used as corroboration. `hook-testing.md:42`:

    No number in the file is presented as data. `2.5 words per second` is the rate the brief fixes, written
    as a named constant with a comment saying it is the brief's rate and not a measurement of any person.

and `hook-testing.md:39-40` repeats the bare-question claim the same way.

Why this is Critical rather than Minor: `docs/swarm4/WAVE3-BRIEF.md:40` states the rule as
"**Never invent a number.** A signal with no data is a sentence saying what is missing." The file
does not merely use a judgement figure, which would be fine if labelled as one, it asserts the
brief as the source. A later reader checking that claim finds nothing, and then cannot trust the
comments that are accurate.

To be fair to the module: the weights themselves are honestly labelled at `studio/hookscore.py:18`,
"Nothing here is measured data; these are the rule weights", and `learn-guard.md:166-169` says the
same about `learn_guard.py`'s ceilings ("The ceilings are a judgement, not a measurement"). That is
the standard the three lines above should have met.

Fix, and it is a comment and two strings, no logic:
- `hookscore.py:29` and `:24` and `:8`: say PeakCut's own rule instead of the brief. For example
  "PeakCut's own reading pace, not a measurement of any person".
- `hookscore.py:179-180`: the sentence a person reads should carry the same hedge, for example
  "At PeakCut's pace of about 2.5 words a second it takes about 2.4 seconds, past the 2 a hook aims for."
- `docs/swarm4/wave3/hook-testing.md:39-42`: correct the claim it repeats.

Note the mitigating fact, which is why I do not block on this: `hookscore` is imported by nothing
(see F5), so no person sees that sentence in this build. The defect is in the source and in the
report, not on a page.

---

## Important

### I1. The hook minimum contradicts the product's own house style

`studio/hookscore.py:28` sets `MIN_WORDS, MAX_WORDS = 3, 7`, and `studio/hookscore.py:155` tells the
person so:

    155   reasons.append(f"It is {count} word{'s' if count != 1 else ''} long, and a hook needs at least 3.")

But `studio/brain.py:88`, the product's own instruction to the AI, says:

    - The hook is what was said at that moment, or, if nothing was said, the name of what happened in
      two or three words ("1 VS 3", "THE SHOT", "HE GOT ME", "CLUTCH"). Never a sentence that needs
      the game explained.

Scored live, the four examples the product itself gives:

    '1 VS 3'     -> 100 strong    It breaks none of the rules this check knows.
    'THE SHOT'   ->  75 strong    It is 2 words long, and a hook needs at least 3.
    'HE GOT ME'  -> 100 strong    It breaks none of the rules this check knows.
    'CLUTCH'     ->  75 strong    It is 1 word long, and a hook needs at least 3.

Two of the four examples the product endorses are told they are too short.

The second half of the problem is that the verdict word is too generous to carry information:

    'okay so here we go'        ->  85 strong    It opens with "okay", a filler that spends the first moment on nothing.
    'what if it was all fake'   ->  90 strong    At 2.5 words a second it takes about 2.4 seconds, past the 2 a hook must land in.

Both are labelled strong while breaking a stated rule, because the penalties (15 and 10) are smaller
than the 30 points it would take to drop below `STRONG_AT = 70`. Only a bare question (45) or a
missing anchor (25 plus something else) ever reaches "weak". The ordering is sound and monotone, so
this is not a scoring bug, it is a labelling problem: "strong" currently means "not badly broken".

Nothing a person sees today is wrong, because nothing imports this module yet. Before it is wired in:
lower `MIN_WORDS` to 2 to match `brain.py:88`, or soften the sentence to "PeakCut likes at least 3",
and either raise `STRONG_AT` or deepen the penalties so "strong" means something.

### I2. The cooldown refusal can promise a wait of "0 h 0 min"

`studio/learn.py:118-124`:

    118        wait = MIN_ROUND_SECONDS - (time.time() - float(last.get("at") or 0))
    119        if wait > 0:
    120            hours = int(wait // 3600)
    121            mins = int((wait % 3600) // 60)
    122            when = _ago(time.time() - float(last.get("at") or 0))
    123            return ("Your settings were changed " + when + ". A change needs time to show anything, "
    124                    f"so the next round can start in {hours} h {mins} min.")

Probed at the boundary:

    one second to go   -> False  Your settings were changed 5 h 59 min ago. ... so the next round can start in 0 h 0 min.
    59 seconds to go   -> False  Your settings were changed 5 h 59 min ago. ... so the next round can start in 0 h 0 min.
    61 seconds to go   -> False  Your settings were changed 5 h 58 min ago. ... so the next round can start in 0 h 1 min.
    ten minutes to go  -> False  Your settings were changed 5 h 50 min ago. ... so the next round can start in 0 h 9 min.

The gate is correct in every case: `_may_run` is False, so the round genuinely cannot start. But the
sentence a person reads offers a wait of zero, which reads like a broken clock. `learn_guard.py`
already does this well: `_wait_text` at `studio/learn_guard.py:182-185` rounds up with
`mins = int(max(0.0, float(seconds) + 59) // 60)` so it never promises an impossible moment;
`learn.py` should borrow that habit. One branch: under a minute, say "in under a minute".

No test would catch it either way. `tests/test_learn.py:216` and `tests/test_learn_api.py:184` both
only check for the phrase "next round can start".

---

## Minor

### M1. The five new route registrations have no test

    $ grep -rn "learn/signals\|learn/arms\|learn/cost" tests/
    (no output, exit 1)

`GET /api/learn/signals`, `GET|POST|DELETE /api/learn/arms` and `GET /api/learn/cost` are exercised
only by the manual smoke run in proof 5. They are written fail-soft, each wrapping its import in a
try and returning an empty shape with `MISSING` (`studio/api_learn.py:212-221` and the arms routes
at `:239-283`), so a break would be silent rather than a 500. A silent break is worth a test more
than a loud one.

### M2. Most new lines change nothing a person can reach

Measured by AST walk for `from . import <name>` and `import studio.<name>` across `studio/`:

    learn_signals    reachable   api_learn.py:212, learn.py:253
    ai_arms          reachable   api_learn.py:230, api_learn.py:255
    learn_guard      reachable   api_learn.py:295
    hookscore        NO IMPORTER ANYWHERE
    learn_report     NO IMPORTER ANYWHERE
    brand_ai         NO IMPORTER ANYWHERE
    prompt_text      NO IMPORTER ANYWHERE
    schedule_ai      NO IMPORTER ANYWHERE

That is 1481 of the 2327 new studio lines, 63 percent of the work, unreachable from the running app.
This is inside the brief's letter: item 7 is "Then three owners wire it in", and each of those five
reports says so itself (`brand-ai.md:82` "Nothing calls this yet", `pipeline-copy.md:74`). I record
it because a reader of the wave would otherwise assume wave 3 shipped a hook score and a cost
report, and it did not.

### M3. Three modules are imported by no test at all

    learn_signals   2 test files      hookscore  2      ai_arms  2
    learn_guard     2 test files      learn_report  2
    brand_ai        0 test files      prompt_text  0      schedule_ai  0

`tests/test_learn_signals.py` imports hookscore at line 40, ai_arms at 45, learn_guard at 50 and
learn_report at 55. `brand_ai.py` (364 lines), `prompt_text.py` (122) and `schedule_ai.py` (454)
have no test, which is 940 untested lines. The brief only demanded the two gates that can be run,
so this is not a violation, it is a gap worth naming before someone wires `schedule_ai` into a
scheduler, where a mistake is expensive.

### M4. A stale example in a docstring

`studio/learn_guard.py:151` illustrates the sentence with a ceiling that is not the real one:

    151   """One sentence about how much is left today, for the Improve page: "9 of 20 rounds left today".

while `studio/learn_guard.py:29` sets `MAX_CALLS_PER_DAY = 8`, and the function actually returns:

    $ python -c "from studio import learn_guard; print(learn_guard.report(''))"
    8 of 8 rounds left today, and 60,000 of 60,000 tokens.

The example is only an illustration, but 20 is exactly the number a reader of the budget code will
try to reconcile against. One character to fix.

### M5. Scratch data directories left behind in `tests/`

    tests/learnprobe        (empty)
    tests/learn-signals-data (empty)
    tests/learn-data        brand_learn_test_user.json, users/learn_test_user/learn.json
    tests/learnapi-data     brand_u_local.json, peakcut.db

They are byproducts of the test runs, the same pattern as the pre-existing `analytics-data`,
`gate-data`, `mood-data`, `overhaul-data`, `settings-data`, `trends-data` and `tmpdata`. With no
git here, nothing cleans them. Harmless, and housekeeping rather than a defect.

---

## File by file

    studio/learn_signals.py       340 lines. Compiles. Fails soft at every edge, proven with garbage
                                  input and with a real curve. Percent plumbing matches
                                  api_analytics.py:420-421. Wired into learn.py:253,257. No finding.

    studio/hookscore.py           248 lines. Compiles, fails soft, but carries C1 (three unsupported
                                  attributions to the brief) and I1 (the 3-word minimum contradicts
                                  brain.py:88, and "strong" survives most single-rule failures).

    studio/ai_arms.py             315 lines. The only constructed raises in the wave, both deliberate
                                  refusals caught into 400s at the route. In-package learn import is
                                  guarded. Wired and smoke tested. No finding.

    studio/learn_guard.py         191 lines. The brake: 8 rounds and 60000 tokens, both declared a
                                  judgement in its own report. Atomic write through tmp and
                                  replace under a lock, future-dated rows still count so moving the
                                  clock back cannot restore budget. M4 only, a stale docstring example.

    studio/learn_report.py        293 lines. Compiles, fails soft, exercised by the test file.
                                  Unreachable from the app (M2). No finding in the code.

    studio/brand_ai.py            364 lines. Compiles, 11 try blocks all handled, deep-copies brand
                                  defaults so a bad answer cannot corrupt them. No test (M3),
                                  unreachable (M2). No finding in the code.

    studio/prompt_text.py         122 lines. Four try blocks, six empty returns, all four public
                                  functions return "" rather than raising. Byte integrity checked
                                  because the inspector renders escapes ambiguously: the source has
                                  real "\n" and real "\u2039", and facts_block(["a","b"]) really
                                  returns '- a\n- b'. No test (M3), unreachable (M2). No finding.

    studio/schedule_ai.py        454 lines. Compiles, eight try blocks and nine handlers. The claim
                                  in its report that 06:00 sits outside autopilot's window is true
                                  (autopilot.py:24-25 set WIN_FROM 08:00, WIN_TO 23:00). The payload
                                  sets the owner before calling learn.run, with a measured reason in
                                  the docstring. The one literal double backslash at line 423 is
                                  correct for Windows paths. No test (M3), unreachable (M2). No finding.

    tests/test_learn_signals.py  329 lines, 97 checks, all pass. Covers four of the eight modules.
                                  Does not cover brand_ai, prompt_text or schedule_ai (M3).

    web/feat/learn-signals.js    228 lines, node --check clean, registered with PeakCut.add, in the
                                  servers 39-file set. Own esc at :19; every server string escaped.
                                  One innerHTML sink at :157 fed by an internal builder. No finding.

    web/feat/learn-arms.js       356 lines, node --check clean, registered with PeakCut.add. Own esc
                                  at :28; every server string escaped; failure text goes in through
                                  textContent at :207. Ticker guarded by try/catch. No finding.

    studio/learn.py              682 lines (wired). Dry bypass intact at :529 with the writes gated at
                                  :542, :571, :584; six hour cooldown intact at :101-108; honest path
                                  intact at :536-545 and :582-583. 103 checks pass. I2 only, the
                                  "0 h 0 min" wording.

    studio/api_learn.py          305 lines (wired). The three original routes are still there at :57,
                                  :72, :103 and still non-404 under test. Five new registrations, all
                                  fail-soft, all smoke tested live. 39 checks pass. M1 only, no tests
                                  for the new ones.

    web/feat/learn.js            372 lines (wired). Both LEAD-RECHECK items survived the wave: the
                                  preview button at :259 carries no disabled attribute, and the .did
                                  line at :235 renders only when `said` is non-empty, with the why
                                  comment at :227-228 and `said` itself at :229. The undo button added at 08:39 while I
                                  reviewed uses esc on its data-at and reaches the route at
                                  api_learn.py:103. node --check clean, 318 feat checks pass. No finding.

Standards met everywhere I measured: every public function in the eight new modules has a docstring
(35 of 35), no fastapi outside an api_ file, no new dependency, no em dash or emoji or marketing
word, line endings consistent per file (new files LF, pre-existing CRLF), and no mix within a file.

---

## What I could not verify

1. **What is actually new.** This is not a git repository, so "new since wave 2" rests on mtimes and
   on the brief's own file list. If a wave 3 agent edited a file outside its report's claim, mtime
   would show it, but I cannot tell which lines changed inside a file that predates the wave.

2. **The page as a person sees it.** I drove no browser. The two new panels were proven by
   `node --check`, by the loader's own 39-file list, by `test_feat_files.py`, and by reading the
   rendering code. I never saw them painted, so layout, empty states and the 700 ms ticker in
   `learn-arms.js` are unproven visually.

3. **Live YouTube numbers.** No channel is connected in this install, so every retention sentence was
   proven against a synthetic curve and against the empty path. The report's claim that the figures
   match `api_analytics.py` is verified at the multiplication, not against real Analytics output.

4. **A live AI round.** No key is configured, so the effect path was never exercised with a model
   answering. Everything I quote about effects comes from the no-AI path, which is also the path the
   tests use.

5. **Four heavy dependencies.** `sqlalchemy`, `psycopg`, `sherpa-onnx` and `pillow` are not importable
   in this interpreter, so any test or path needing them could not have run here, including anything
   that would touch the database layer through them.

6. **The `web/feat/learn.js` edit at 08:39.** It landed while this review was running. I re-ran the
   gates against the new bytes and read the added undo button, but I did not review it with the same
   depth as the rest of the file, and it is the one line of this review I would want a second pair of
   eyes on.

---

## Verdict

**SHIP.**

Every gate passes: the compile checks, `node --check`, all four test suites, the dry bypass, the six
hour cooldown, the honest path, the three original routes, fastapi confinement, the style ban, the
dependency rule and the escaping rule. No new module fails loudly on a bad input, no new dependency
appeared, no em dash or emoji reached a sentence a person reads, and both of the lead's hand edits
survived the wave.

The one Critical item, C1, is real and should be fixed before this wave is considered done: three
comments and one user-facing string in `studio/hookscore.py` attribute a reading rate, a two second
deadline and a bare-question rule to the brief, and the brief contains none of them. The brief's own
rule is "Never invent a number", and the file says the brief is where those numbers came from. That
is a comment and one sentence, not logic, and `hookscore` is imported by nothing, so no page is
wrong today. Fixing it costs ten minutes; leaving it costs the next reader's trust in every other
comment in the wave.

I would also fix I1 (the three word minimum against `brain.py:88`'s two) before `hookscore` is wired
into anything a person sees, and I2 (the "0 h 0 min" wait) whenever `learn.py` is next opened. Both
are small.

Nothing else I measured is wrong. The eight new modules are honest about what they do, the two new
panels escape what they print, the guard is atomic, the retention plumbing matches the analytics it
reads, and the wired files kept every promise the brief made about them.
