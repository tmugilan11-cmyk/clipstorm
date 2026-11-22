# Wave 3 review: what I changed

Fixer's pass over `docs/swarm4/wave3/REVIEW.md`. The review's verdict was SHIP with one critical, two
important and five minor findings. Below is one section per finding: what I did, where, and the literal
output that proves it.

The review skill I ran first was `code-review` (the two-axis standards/spec review). This is not a git
repo (`docs/swarm3/CONTRACT.md:54` says not to run git), so its "pin a fixed point" step is satisfied by
the wave brief plus the eleven owner reports in this folder as the change set, not by a commit range.
(The other files here are `REVIEW.md`, `LEAD-RECHECK.md` and this one.)

Files I edited, all inside this wave:

    studio/hookscore.py            C1, I1
    studio/learn.py                I2
    studio/learn_guard.py          M4
    tests/test_learn_api.py        M1
    docs/swarm4/wave3/hook-testing.md   C1, I1 (the report that repeats the attributions)
    .gitignore                     M5

I did not touch `web/index.html`. Every other file I edited is either a wave 3 module, the wave 3 report
that carries the same defect, the test file that covers these routes, or the repo's ignore list for the
M5 housekeeping finding.

---

## C1 (critical). Three numbers attributed to the brief that the brief never states

**Agreed, and fixed.** The finding is right, and I checked it independently rather than taking it on
trust. The wave brief does not contain the reading rate, the two second deadline, or the bare question
rule:

    $ cd peakcut && grep -n "2\.5\|words a second\|words per second\|reading rate\|two second\|2 second\|bare question" docs/swarm4/WAVE3-BRIEF.md; echo "EXIT=$?"
    EXIT=1

So "the promise the brief makes", "the brief names this as a failure", "the reading rate the brief fixes"
and the page-facing "past the 2 a hook must land in" were all claims about a document that says none of
it. That is the exact failure the brief's own rules forbid ("Never invent a number", and a signal with no
data must be a sentence saying what is missing).

What changed, with the new text:

- `studio/hookscore.py:7-9` (module docstring) now says the preference is PeakCut's own, and that the
  rules are PeakCut's and not measured or quoted:

      the 100, because that is PeakCut's own preference: plain but sound beats clever and broken. The rules
      below are PeakCut's, not anything measured or quoted: no number here comes from data.

- `studio/hookscore.py:25` the bare-question weight now reads:

      PENALTY_BARE_QUESTION = 45    # PeakCut treats this as a failure on its own, so it has to cost real points

- `studio/hookscore.py:33-34` the reading pace now reads:

      WORDS_PER_SECOND = 2.5        # PeakCut's own reading pace, chosen so a first line lands in time;
                                    # not a measurement of any person

- `studio/hookscore.py:186-188` the sentence a person actually reads is now hedged as PeakCut's own rule
  instead of a fixed deadline the brief handed down:

      reasons.append(f"At PeakCut's own pace of {WORDS_PER_SECOND} words a second, this takes about "
                     f"{seconds:.1f} seconds to say, and PeakCut wants the first line inside "
                     f"{TWO_SECONDS:.0f}.")

- `docs/swarm4/wave3/hook-testing.md:45-48` the report that repeated the attribution now says:

      No number in the file is presented as data, and none is attributed to the brief. `2.5 words per second` is
      PeakCut's own reading pace, written as a named constant with a comment saying it is that pace and not a
      measurement of any person. The same goes for every weight and for `2 seconds`: they are PeakCut's rules,
      chosen and written down here, not quoted from anywhere and not measured from viewers.

Proof that nothing in the edited files still claims the brief says any of it:

    $ cd peakcut && grep -rn "the brief" studio/hookscore.py studio/learn.py studio/learn_guard.py docs/swarm4/wave3/hook-testing.md; echo "EXIT=$?"
    docs/swarm4/wave3/hook-testing.md:45:No number in the file is presented as data, and none is attributed to the brief. `2.5 words per second` is
    docs/swarm4/wave3/hook-testing.md:95:  files belong to the wire agents in this wave, and the brief says nobody else touches them. `score`,
    EXIT=0

Both remaining hits are not number attributions. The first is the sentence that explicitly denies one, and
the second is the true statement that the brief assigns file ownership.

The sentence a person reads, after the fix:

    $ cd peakcut && python -c "
    from studio import hookscore
    print(hookscore.score('what if it was all fake')['reasons'][0])"
    At PeakCut's own pace of 2.5 words a second, this takes about 2.4 seconds to say, and PeakCut wants the first line inside 2.

---

## I1 (important). A three-word minimum that contradicts `brain.py`, and a "strong" that survives one real fault

**Agreed on both halves, and fixed.** The contradiction is provable: `studio/brain.py:87-90` gives the
prompt's own examples of a hook, and they are two words, not three or more:

    - The hook is what was said at that moment, or, if nothing was said, the name of what happened in two or
      three words ("1 VS 3", "THE SHOT", "HE GOT ME", "CLUTCH"). Never a sentence that needs explanation.

Before the fix the scorer told that exact shape it was wrong:

    $ cd peakcut && python - <<'PY'
    from studio import hookscore as h
    for p in ("THE SHOT", "CLUTCH"):
        r = h.score(p); print(f"{p!r} {r['score']} {r['verdict']} {r['reasons']}")
    PY
    'THE SHOT' 75 strong ['It is 2 words long, and a hook needs at least 3.']
    'CLUTCH' 75 strong ['It is 1 word long, and a hook needs at least 3.']

Two words was the shape `brain.py` names first, and the scorer penalised it.

What changed:

- `studio/hookscore.py:32` `MIN_WORDS, MAX_WORDS = 2, 7`, so the shape `brain.py` asks for is no longer
  charged. The comment at `:29-31` says why, and why a single word still costs something.
- `studio/hookscore.py:162` the reason sentence now says `under the 2 PeakCut reads as a hook` instead of
  asserting a three word rule.
- The second half of the finding was that `strong` meant "not badly broken": the largest penalties that
  could apply to a phrase that still had an anchor, a clean opening and no bare question were 15 and 10,
  both under the 30 needed to fall below `STRONG_AT = 70`, so a filler opening or a slow line still read
  `strong`. I raised the bar instead of softening the word, because a page that says "strong" should mean
  it. `studio/hookscore.py:39` is now `STRONG_AT, WORKABLE_AT = 85, 40`, and the two weights that could
  hide under it were raised to match: `PENALTY_FILLER_OPEN = 20` at `:24` and `PENALTY_SLOW = 20` at
  `:26`. Any single real fault now costs at least 20, which is more than 15, so one fault drops the
  verdict out of strong.

Proof, same phrases after the fix:

    $ cd peakcut && python - <<'PY'
    from studio import hookscore as h
    print("MIN_WORDS,MAX_WORDS =", h.MIN_WORDS, h.MAX_WORDS, "| STRONG_AT", h.STRONG_AT)
    for p in ("1 VS 3", "THE SHOT", "HE GOT ME", "CLUTCH", "you lose the rent money",
              "okay so here we go", "what if it was all fake", "why would anyone watch this"):
        r = h.score(p); print(f"{p!r:26} -> {r['score']:3} {r['verdict']:9} {r['reasons']}")
    PY
    MIN_WORDS,MAX_WORDS = 2 7 | STRONG_AT 85
    '1 VS 3'                   -> 100 strong    ['It breaks none of the rules this check knows.']
    'THE SHOT'                 -> 100 strong    ['It breaks none of the rules this check knows.']
    'HE GOT ME'                -> 100 strong    ['It breaks none of the rules this check knows.']
    'CLUTCH'                   ->  75 workable  ['It is 1 word long, under the 2 PeakCut reads as a hook.']
    'you lose the rent money'  -> 100 strong    ['It breaks none of the rules this check knows.']
    'okay so here we go'       ->  80 workable  ['It opens with "okay", a filler that spends the first moment on nothing.']
    'what if it was all fake'  ->  80 workable  [... 2.4 seconds ...]
    'why would anyone watch this' -> 100 strong ['It breaks none of the rules this check knows.']

The three shapes `brain.py` names now score 100 and read strong; the single word reads workable rather
than being called too short, which matches `brain.py` listing "CLUTCH" as a hook it would accept.

`docs/swarm4/wave3/hook-testing.md` was updated to match: the rule table at `:26` and `:31`, the verdict
line at `:33` (now 85), the sample block at `:61-80`, and a note at `:82-85`. The sample block in that
report was re-run rather than edited by hand:

    '' 0 weak
    'So' 30 weak
    'What happened?' 55 workable
    'Do you like it?' 55 workable
    'He lost the house in one bet' 80 workable
    'You lose the account tonight' 100 strong
    ['You lose the account tonight', 'He lost the house in one bet', 'What happened?']

Note that `He lost the house in one bet` moved from `90 strong` to `80 workable`. That is the intended
effect of the raised bar: it opens on "He", names a real consequence, but runs long, and one real fault
should not read as strong.

Nothing outside this wave needed to change. Nothing in `studio/` imports `hookscore` yet, so no page is
affected by the weight change; `tests/test_learn_signals.py` is the only caller.

---

## I2 (important). The cooldown refusal could say "0 h 0 min"

**Agreed, and fixed.** Reproduced first, on the code as reviewed:

    $ cd peakcut && python - <<'PY'
    import time
    from studio import learn
    learn.ai.ready = lambda: True
    now = time.time()
    for wait in (0.4, 45, 7200):
        data = {"rounds": [{"at": now - (learn.MIN_ROUND_SECONDS - wait)}]}
        print(f"wait={wait!r:>6} -> {learn._why_not(data)!r}")
    PY
    wait=   0.4 -> 'Your settings were changed 5 h 59 min ago. A change needs time to show anything, so the next round can start in 0 h 0 min.'
    wait=    45 -> 'Your settings were changed 5 h 59 min ago. A change needs time to show anything, so the next round can start in 0 h 0 min.'
    wait=  7200 -> 'Your settings were changed 4 h ago. A change needs time to show anything, so the next round can start in 1 h 59 min.'

The first two are worse than cosmetic: they tell a person the wait is over while `_may_run` still refuses,
which is the one thing a refusal sentence must not do.

What changed: `studio/learn.py:119-122` now calls a rounding helper, and that helper is defined at
`studio/learn.py:126-135` as `_wait_text`, the same rule `learn_guard.py:182-191` already used (round up
to the next minute, so a refusal never names a moment that is still refused, and say "less than a
minute" rather than "0 min"). I put the helper in `learn.py` instead of importing it from
`learn_guard.py` on purpose: `learn_guard` is the optional second brake, and `learn.py` must not gain a
hard import on it (`docs/swarm3/CONTRACT.md` keeps the brake soft so a missing file cannot stop the
Improve page).

    last = data["rounds"][-1] if data["rounds"] else None
    if last:
        wait = MIN_ROUND_SECONDS - (time.time() - float(last.get("at") or 0))
        if wait > 0:
            when = _ago(time.time() - float(last.get("at") or 0))
            return ("Your settings were changed " + when + ". A change needs time to show anything, "
                    f"so the next round can start in {_wait_text(wait)}.")

Proof, the same reproduction after the fix:

    $ cd peakcut && python - <<'PY'
    import time
    from studio import learn
    learn.ai.ready = lambda: True
    now = time.time()
    for wait in (0.4, 45, 61, 7200):
        data = {"rounds": [{"at": now - (learn.MIN_ROUND_SECONDS - wait)}]}
        print(f"wait={wait!r:>6} -> {learn._why_not(data)!r}")
    PY
    wait=   0.4 -> 'Your settings were changed 5 h 59 min ago. A change needs time to show anything, so the next round can start in less than a minute.'
    wait=    45 -> 'Your settings were changed 5 h 59 min ago. A change needs time to show anything, so the next round can start in 1 min.'
    wait=    61 -> 'Your settings were changed 5 h 58 min ago. A change needs time to show anything, so the next round can start in 1 min.'
    wait=  7200 -> 'Your settings were changed 4 h ago. A change needs time to show anything, so the next round can start in 2 h.'

No "0 h 0 min" is reachable now, and the sentence still contains "next round can start", which is what
`tests/test_learn.py:216` and `tests/test_learn_api.py` pin.

---

## M1 (minor). Five new routes with no test

**Agreed, and fixed.** The review's evidence was right; the routes existed but nothing called them:

    $ cd peakcut && grep -rn "learn/signals\|learn/arms\|learn/cost" tests/
    (no output)

That is exactly the gap that lets a route register under a path the page does not agree with. I added
the tests to `tests/test_learn_api.py` rather than a new file, because that file already builds the
signed-in client and the `check()` counter.

What changed:

- `tests/test_learn_api.py:66-68` adds `delete` to the `_Caller` harness, which only had `get` and
  `post`, so a DELETE route could not be called at all.
- `tests/test_learn_api.py:235-307` adds a "wave 3: the five new routes" section. For each of
  `GET /api/learn/signals`, `GET /api/learn/arms`, `POST /api/learn/arms`, `DELETE /api/learn/arms` and
  `GET /api/learn/cost` it checks the route is not a 404 and never answers 500 with the AI switched off,
  then checks the shape the page draws: signals always carries `hook`, `length`, `drop` and `points` with
  `drop` holding `at` and `kept`; arms says `trial: None` rather than inventing one; arms refuses an
  unknown setting with 400 and a sentence; arms refuses the same setting twice; a real trial round-trips
  through save, read and delete; and cost counts `calls` and `tokens` and carries a report sentence
  naming the rounds left.

Proof, the new checks running:

    $ cd peakcut && python tests/test_learn_api.py 2>&1 | tail -3

    All checks passed. 76 ok

The count went from 39 to 76 because of these checks. Before this change the same file measured 39.

---

## M2 (minor). Five of eight new modules are not reachable from the app

**Agreed as a fact, and deliberately not fixed here.** I verified it myself:

    $ cd peakcut && for m in hookscore learn_report brand_ai prompt_text schedule_ai; do
        echo "$m <- studio: $(grep -rln "\b$m\b" studio/*.py | grep -v "studio/$m.py" | tr '\n' ' ')"; done
    hookscore <- studio:
    learn_report <- studio:
    brand_ai <- studio:
    prompt_text <- studio:
    schedule_ai <- studio:

Each line is empty after the colon, which is the point: no file in `studio/` names any of the five.

Compared with the three that are wired:

    learn_signals <- studio: studio/api_learn.py studio/learn.py
    ai_arms       <- studio: studio/api_learn.py
    learn_guard   <- studio: studio/api_learn.py

The review calls this record-only and inside the brief's letter, and it is right. The brief's item 7 is
"Then three owners wire it in", so the wiring is scheduled work in a later step, and the modules are
not defects: they compile, they fail soft, and two of them (`hookscore`, `learn_report`) are exercised
by `tests/test_learn_signals.py`.

The exact change the wiring step needs, so it is written down rather than remembered:

1. `studio/api_learn.py` needs a `GET /api/learn/report` route that calls `learn_report.build(uid)` in
   `run_in_threadpool` and returns its dict, next to the existing cost route at `:286`; the page section
   that draws it goes in `web/feat/learn.js`.
2. `studio/hookscore.py` is reached through `learn.py`'s round, not a route of its own: `learn.run` would
   call `hookscore.score` on each candidate hook before asking the AI, so the score is visible before a
   view count exists. That is a change in `learn.py`, which the wire agents own.
3. `brand_ai.py`, `prompt_text.py` and `schedule_ai.py` have no route and no owner named in the wave 3
   brief at all. They need a decision about which page shows them before a route is worth writing.

I left all five modules untouched, because editing them here would be the same "write it and leave it
unreachable" that the finding is about, one step further along.

---

## M3 (minor). 940 lines with no test

**Agreed as a fact, and left alone with the reason written down.** The line counts are confirmed:

    $ cd peakcut && wc -l studio/brand_ai.py studio/prompt_text.py studio/schedule_ai.py
      364 studio/brand_ai.py
      122 studio/prompt_text.py
      454 studio/schedule_ai.py

That is 940 lines, and the review is right that the wave brief only demanded runnable gates for
`hookscore` and `learn_signals`. `hookscore` and `learn_report` do have coverage through
`tests/test_learn_signals.py:318` and `:321`; these three do not.

I did not write tests for them in this pass, and the report says so plainly rather than leaving it
implied. The reason is scope, not difficulty: `tests/test_learn_signals.py` is the wave's gate file and
adding three sections to it here would put new assertions under a different owner without a review.
The next step that gives these modules a caller (M2 above) should bring their tests with it, because a
test written against a caller is worth more than a test written against an unused function.

---

## M4 (minor). A docstring example that contradicts the constant

**Agreed, and fixed.** Reproduced:

    $ cd peakcut && python -c "from studio import learn_guard as g; print(g.report('u_local'))"
    8 of 8 rounds left today, and 60,000 of 60,000 tokens.
    $ cd peakcut && sed -n '151p' studio/learn_guard.py
        """One sentence about how much is left today, for the Improve page: "9 of 20 rounds left today".

The code says 8 of 8 and the example said 9 of 20, which is unreachable: `MAX_CALLS_PER_DAY = 8` at
`studio/learn_guard.py:29`.

What changed: `studio/learn_guard.py:151` now reads

    """One sentence about how much is left today, for the Improve page: "8 of 8 rounds left today".

Proof after the fix:

    $ cd peakcut && sed -n '151p' studio/learn_guard.py
        """One sentence about how much is left today, for the Improve page: "8 of 8 rounds left today".
    $ cd peakcut && python -c "from studio import learn_guard as g; print(g.report('u_local'))"
    8 of 8 rounds left today, and 60,000 of 60,000 tokens.

No test pins the docstring, and none needed to change.

---

## M5 (minor). Scratch data directories left in `tests/`

**Agreed as housekeeping, and handled at the cause rather than by deleting files.** The directories are
real:

    $ cd peakcut && ls -d tests/*-data tests/tmpdata
    tests/analytics-data
    tests/gate-data
    tests/learn-data
    tests/learn-signals-data
    tests/learnapi-data
    tests/mood-data
    tests/overhaul-data
    tests/settings-data
    tests/tmpdata
    tests/trends-data

That is ten from that glob, and `tests/learnprobe` is an eleventh that `tests/*-data` misses because its
name has no `-data` in it. So the total is eleven: the review's four (`learnprobe`, `learn-data`,
`learn-signals-data`, `learnapi-data`) plus the seven that predate the wave. `learnprobe` is not empty
any more: it holds `fonts`, `models`, `tmp` and `users`, and nothing in the repo names it now:

    $ cd peakcut && grep -rn "learnprobe" --include=*.py . | grep -v __pycache__; echo "EXIT=$?"
    EXIT=1

It is left over from an earlier probe and is not recreated by the suites, so it is the one of the
eleven that could simply be deleted by hand. I did not delete it: this task is about the code the review
names, and a stray folder is not worth a `rm` nobody asked for.

Three of the remaining ten are made by this wave's test files:

    $ cd peakcut && grep -rn "_DATA = HERE" tests/test_learn.py tests/test_learn_api.py tests/test_learn_signals.py
    tests/test_learn.py:27:_DATA = HERE / "learn-data"
    tests/test_learn_api.py:24:_DATA = HERE / "learnapi-data"
    tests/test_learn_signals.py:25:_DATA = HERE / "learn-signals-data"

The rest predate this wave, so this is not a wave 3 regression, and the review says as much. Because
three of them are this wave's, and the three files above create theirs deliberately, the fix belongs at
the ignore rule rather than at the tests.

Deleting the live ones would be undone the next time the suites run, so I added the rule instead, in
`.gitignore`, and I included `learnprobe` by name so the stray one is covered too:

    $ cd peakcut && tail -6 .gitignore
    .pytest_cache/

    # ---- throwaway data folders the test files create
    tests/*-data/
    tests/tmpdata/
    tests/learnprobe/

That covers all eleven, keeps the pattern visible next to the other ignore rules, and means a future
`git init` here cannot commit them by accident. I did not change the test files to write elsewhere:
they already set `PEAKCUT_DATA` into `tests/` on purpose, so a run cannot touch a real install's data
folder, and moving that would trade a housekeeping smell for a safety one.

---

## Findings I did not change, and why

None of the eight findings was wrong. I checked each against the tree before touching anything, and the
only one I deliberately left as code is M2's five unreachable modules and M3's untested lines, both of
which the review itself files as record-only rather than as defects. Both are answered above with the
exact change the next step needs.

One thing the review did not flag, which I noticed while fixing C1 and did not act on further than
correcting the number: the wave 3 report `docs/swarm4/wave3/hook-testing.md` described the `So` phrase at
`:40-41` as scoring 35 after the anchor rule, and the real score after the threshold change is 30. I
changed that one figure to `30`, because it is a claim a reader can check with one line, and re-ran the
phrase to confirm it before writing it down:

    $ cd peakcut && python -c "from studio import hookscore as h; print(h.score('So')['score'], h.score('So')['verdict'])"
    30 weak

I did not invent a replacement for the "65 before the rule" half of that sentence, because that number
describes a version of the code that no longer exists and cannot be re-measured.

Re-running that report's sample block turned up a second thing the review did not flag, and this one was
worse than a stale figure: the block printed a `suggest` line under a stub `$ python -c "..."` command,
and the list it showed was not what the code returns. The real answer for the three phrases it asked for
is the three highest scores, not the two it printed:

    $ cd peakcut && python - <<'PY'
    from studio import hookscore as h
    given = ["", "So", "What happened?", "Do you like it?",
             "He lost the house in one bet", "You lose the account tonight"]
    print(h.suggest(given, 3))
    PY
    ['You lose the account tonight', 'He lost the house in one bet', 'What happened?']

I replaced the stub with the full reproducing script and pasted its real output, so the block in
`hook-testing.md:63-80` is now copy-run true rather than illustrative. That is a documentation fix only;
no code was involved, and `hookscore.suggest` was already correct.

---

## The suites, run after every change

    $ cd peakcut && python tests/test_learn.py
    All checks passed. 103 ok

    $ cd peakcut && python tests/test_learn_api.py
    All checks passed. 76 ok

    $ cd peakcut && python tests/test_learn_signals.py
    All checks passed. 97 ok

    $ cd peakcut && python tests/test_feat_files.py
    {"files": 39, "checks": 318}
    All checks passed.

    $ cd peakcut && python tests/test_menu_pages.py
    All checks passed. 144 ok

All five exited 0. `test_learn`, `test_learn_signals`, `test_feat_files` and `test_menu_pages` are the
same counts as before the pass (103, 97, 39 files / 318 checks, 144). `test_learn_api` moved from 39 to
76 because of the new wave 3 route checks, which is the M1 work showing up as evidence.

Compile and dash checks on the edited files:

    $ cd peakcut && python -m py_compile studio/hookscore.py studio/learn.py studio/learn_guard.py tests/test_learn_api.py; echo "COMPILE EXIT=$?"
    COMPILE EXIT=0
    $ cd peakcut && node --check web/feat/learn.js; echo "NODE EXIT=$?"
    NODE EXIT=0
    $ cd peakcut && python - <<'PY'
    import pathlib
    for f in ("studio/hookscore.py", "studio/learn.py", "studio/learn_guard.py",
              "tests/test_learn_api.py", "docs/swarm4/wave3/hook-testing.md"):
        t = pathlib.Path(f).read_text(encoding="utf-8")
        print(f, [c for c in ("\u2014", "\u2013") if c in t] or "no dashes")
    PY
    studio/hookscore.py ['no dashes']
    studio/learn.py ['no dashes']
    studio/learn_guard.py ['no dashes']
    tests/test_learn_api.py ['no dashes']
    docs/swarm4/wave3/hook-testing.md ['no dashes']

---

## Summary, finding by finding

| Finding | Severity | What I did | Where |
|---|---|---|---|
| C1 | critical | Replaced the three brief attributions with PeakCut's own rule, and hedged the sentence a person reads | `studio/hookscore.py:7-9`, `:25`, `:33-34`, `:186-188`; `hook-testing.md:45-48` |
| I1 | important | Two words is now a hook; the filler and slow penalties and the strong threshold raised so one fault drops the verdict | `studio/hookscore.py:24`, `:26`, `:29-32`, `:39`, `:162`; `hook-testing.md:26`, `:31`, `:33`, `:61-85` |
| I2 | important | Cooldown wait is rounded up through one helper, so "0 h 0 min" is unreachable | `studio/learn.py:119-122`, helper at `:126-135` |
| M1 | minor | Five new routes now tested: existence, no 500, shape, and the arms save/read/delete round trip | `tests/test_learn_api.py:66-68`, `:235-307` |
| M2 | minor | Confirmed, not changed. The exact wiring change is written down above | `studio/api_learn.py` (next step) |
| M3 | minor | Confirmed, not changed. 940 untested lines, why, and when they should get tests | `studio/brand_ai.py`, `prompt_text.py`, `schedule_ai.py` |
| M4 | minor | Docstring example now matches the constant | `studio/learn_guard.py:151` |
| M5 | minor | Scratch dirs ignored at the cause, not deleted | `.gitignore` |
