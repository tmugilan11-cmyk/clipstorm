# Wave 3 - Proof

Prover: `agent-72` (subagent of `lead`). Date run: 2026-11-20, 09:24-10:05 (Asia/Calcutta).
Repo: the `peakcut` folder. Every command below was run from its root, in this session, and what is
quoted is the literal output, not a summary of it. Nothing was copied from another agent's report.
Where a second run disagreed with my first draft, the disagreement is written down rather than tidied
away: see the `[!]` item in section 2 about `tests/run.py`, and the note on `_wait_text` under I2.

Toolchain actually present: `Python 3.15.0`, `node v24.22.2`, system `curl`.

Two things about this environment shape the evidence and are stated up front so no line below is
overclaimed:

- This folder is **not a git repository** (`git status` exits 128 with `fatal: not a git repository`),
  so "what changed" rests on mtimes and on the reports' own file lists, never on a diff.
- `psycopg` and `sherpa_onnx` are **not importable** in this interpreter. `sqlalchemy`, `PIL`, `numpy`,
  `soundfile`, `fastapi`, `uvicorn` and `httpx` are. No check below needed the two that are missing.

One formatting note, so "literal output" is not read as more than it is: where a printed path repeats
the same long parent folder, it is shortened with `...` (for example
`...\peakcut\studio\hookscore.py`). Nothing else in any quoted block is elided or reworded; the
`[!]` items and the I2 note below record the two places where a re-run disagreed with my first draft.

---

## 1. Every new module imports

- [x] **All eight in one statement.** Command:
  ```
  python -c "import studio.learn_signals, studio.hookscore, studio.ai_arms, studio.learn_guard, \
  studio.learn_report, studio.schedule_ai, studio.brand_ai, studio.prompt_text"
  ```
  Printed **nothing**, `IMPORT EXIT=0`. Nothing was missing.

- [x] **Each one named, with the file it resolves to** (a single import statement proves the group
  parses together, not which module a name came from). Command: an `importlib.import_module` loop over
  the same eight names, printing `__file__` or the failure. Printed:
  ```
  OK   studio.learn_signals -> ...\peakcut\studio\learn_signals.py
  OK   studio.hookscore -> ...\peakcut\studio\hookscore.py
  OK   studio.ai_arms -> ...\peakcut\studio\ai_arms.py
  OK   studio.learn_guard -> ...\peakcut\studio\learn_guard.py
  OK   studio.learn_report -> ...\peakcut\studio\learn_report.py
  OK   studio.schedule_ai -> ...\peakcut\studio\schedule_ai.py
  OK   studio.brand_ai -> ...\peakcut\studio\brand_ai.py
  OK   studio.prompt_text -> ...\peakcut\studio\prompt_text.py
  missing: none
  ```
  `PROBE EXIT=0`. **No module is missing**, so there is no name to report as absent.

- [x] **The guarded sibling import in `ai_arms` is real, not accidental.** `studio/ai_arms.py:30` is
  `from . import learn` inside a `try`, with `studio/ai_arms.py:33` `import learn` as the fallback for a
  caller that put `studio/` straight on the path. It imported cleanly under both shapes here because
  the package shape is what ran.

---

## 2. Every test this wave touched passes

The five files below are the ones the wave's reports and FIXES.md name as touched or re-run. Each was
run on its own, with `out=$(python "$f" 2>&1); code=$?` so the exit code is the test's own and not the
`tail` in the pipeline's.

- [x] **`tests/test_learn_signals.py`** - `python tests/test_learn_signals.py`. Tail:
  ```
  All checks passed. 97 ok
  ```
  `EXIT=0`.

- [x] **`tests/test_learn_api.py`** - `python tests/test_learn_api.py`. Tail:
  ```
  All checks passed. 76 ok
  ```
  `EXIT=0`. This is the count FIXES.md records as having moved 39 -> 76 through the M1 work.

- [x] **`tests/test_learn.py`** - `python tests/test_learn.py`. Tail:
  ```
  All checks passed. 103 ok
  ```
  `EXIT=0`.

- [x] **`tests/test_feat_files.py`** - `python tests/test_feat_files.py`. Tail (4 lines):
  ```
  ok   loader keeps the documented folder
  {"files": 39, "checks": 318}
  All checks passed.
  ```
  `EXIT=0`.

- [x] **`tests/test_menu_pages.py`** - `python tests/test_menu_pages.py`. Tail:
  ```
  ok   menu-pages.js draws its page

  All checks passed. 144 ok
  ```
  `EXIT=0`.

- [x] **The new WAVE3 checks inside `test_learn_api.py` really execute**, not just sit in the file.
  That file prints one total and no per-check names, so a passing total alone would not prove the five
  new route checks ran. Command:
  ```
  python -m trace --count --coverdir="$(cygpath -w "$(mktemp -d)")" tests/test_learn_api.py
  grep -n "WAVE3" <that folder>/test_learn_api.cover
  ```
  Printed `TRACE EXIT=0` / `All checks passed. 76 ok`, and the cover file marks both new check lines as
  executed, five times each, once per route in the loop at `tests/test_learn_api.py:242-247`:
  ```
  246:    5:         check(f"WAVE3 {method.upper()} {path} is not a missing route", r.status_code != 404)
  247:    5:         check(f"WAVE3 {method.upper()} {path} never answers 500 with the AI off", r.status_code < 500)
  ```
  Five routes (signals get, arms get/post/delete, cost get) x two checks = the ten checks behind the
  count going up.

- [!] **The aggregate runner, `python tests/run.py`, exits 1, and the two groups it names are not
  this wave's.** This is a caveat rather than a tick, because the runner does not cover the whole wave
  (see the next item). Measured with the exit code captured before any pipe:
  ```
  out=$(python tests/run.py 2>&1); c=$?; echo "REAL RUN EXIT=$c"
  -> REAL RUN EXIT=1
  -> FAILED: queue under load, the new-version notice
  ```
  Its two failing sections, quoted:
  ```
  === queue under load ===
    FAIL it sees a fully loaded processor   {'cpu': 37, 'ram_free_gb': 7.5, 'disk_free_gb': 616.2, 'busy': False, 'busy_cpu': 82.0}
    1 failed
    32 checks passed

  === the new-version notice ===
    FAIL this folder's own version is found   got 0
    FAIL the version PeakCut started on is remembered   got 0
    FAIL ...and only the one small question was asked   got []
    Traceback (most recent call last):
      File "C:\Users\Asus\...\peakcut\tests\test_updates.py", line 60, in <module>
        check("it goes to the address git itself uses, not the API", asked[0], f"https://github.com/{updates.REPO}.git/info/refs")
                                                                     ~~~~~^^^
    IndexError: list index out of range
    5 checks passed
  ```
  **Correction I had to make to my own first draft:** I originally reported that this runner "exits 0
  after printing FAILED". That was wrong. I had read `$?` after a pipe into `tail`, which reports
  `tail`'s status, not the runner's. Re-measured without the pipe it is a clean `EXIT=1`, and the
  negative path is honoured in source (`tests/run.py`, tail: `return 1 if failed else 0` under
  `sys.exit(main())`).

  The two failures are pre-existing and environmental, and **wave 3 did not cause them**: a `grep -l`
  for `learn_signals|hookscore|ai_arms|learn_guard|learn_report|schedule_ai|brand_ai|prompt_text|api_learn`
  across both files exits 1, so **neither names a wave 3 module**; and both files predate every wave 3
  edit (`tests/test_load_queue.py` and `tests/test_updates.py` are `2026-11-19T10:43:34`, while every
  file this wave touched is `2026-11-20`). Mechanically:
  - `test_load_queue.py:45` `check("it sees a fully loaded processor", hot["cpu"] > 80 and hot["busy"], ...)`
    starts one burner per core, sleeps 18s, then wants `cpu > 80`. On this box it reads 37 against a
    smoothed load average while `busy_cpu` is 82, a timing check on this machine's scheduler, not on
    any wave 3 file. `learn-two-arms.md:110-121` reports the same reading and the same conclusion.
  - `test_updates.py` reads a 40-character git commit. `ls -d .git` -> `No such file or directory`, and
    `python -c "from studio import updates; print(len(updates.RUNNING))"` -> `0`. The folder is not a
    git checkout, so there is no commit to read; `learn-two-arms.md:112-116` says the same.
  - `test_abuse.py` is **not** broken: I had invoked it wrongly. Its contract is
    `test_abuse.py <base url> <project root>` (`tests/test_abuse.py:6` `BASE = sys.argv[1]`). With no
    arguments it raises `IndexError: list index out of range` (EXIT=1); given a Windows path where the
    base URL belongs it raises `httpx.UnsupportedProtocol: Request URL has an unsupported protocol
    'c://'`. Under `tests/run.py`, which passes a real base URL (`tests/run.py:49`), that section prints
    `ALL PASSED` / `40 checks passed`. My earlier `c://` line was a mis-invocation, not a defect.

- [!] **The aggregate runner does not contain this wave's newest test.** `tests/run.py` was last written
  `2026-11-20T04:06`, before three test files existed, so it never runs them:
  ```
  comm -13 <(run.py's test list) <(ls tests/*.py)
  -> test_insights_pages.py
  -> test_learn_signals.py
  -> test_trends_api.py
  ```
  `test_learn_signals.py` is 97 of this wave's checks and is one of the five gates below, so a green
  `run.py` would not have been evidence of the wave passing even if it had been green. That is why the
  five gates are run and quoted directly instead.

---

## 3. `studio.server` still imports, and every file in `studio/` compiles

- [x] **The server imports.** Command:
  ```
  python -c "import studio.server; print('studio.server OK', studio.server.__file__)"
  ```
  Printed:
  ```
  studio.server OK C:\...\peakcut\studio\server.py
  ```
  `SERVER IMPORT EXIT=0`.

- [x] **Every file in `studio/` compiles.** Command: a `py_compile.compile(..., doraise=True)` loop over
  `sorted(pathlib.Path('studio').glob('*.py'))`, each into its own temporary `.pyc`. Printed:
  ```
  studio/*.py files: 73
  compiled ok: 73
  failed: 0
  ```
  `COMPILE-ALL EXIT=0`. No file failed, so there is no exception text to quote.

- [x] **The same, through the plain compiler entry point.** `python -m py_compile $(ls studio/*.py)`
  printed nothing, `PY_COMPILE EXIT=0`.

- [x] **The app object is a real FastAPI app with the routes attached.**
  ```
  app type: FastAPI
  routes: 112
  ```
  `EXIT=0`. The learn router is not reachable by `app.routes` path-walking because it is an
  `_IncludedRouter`, so the routes were counted at the router itself:
  ```
  api_learn.router routes: 8
  ['GET'] /api/learn/state          ['POST'] /api/learn/run
  ['POST'] /api/learn/undo          ['GET'] /api/learn/signals
  ['GET'] /api/learn/arms           ['POST'] /api/learn/arms
  ['DELETE'] /api/learn/arms        ['GET'] /api/learn/cost
  ```
  That is the three original routes plus the five this wave added, all registered.

- [x] **The three new JS files parse.** `node --check` on each:
  ```
  node --check web/feat/learn-signals.js EXIT=0
  node --check web/feat/learn-arms.js    EXIT=0
  node --check web/feat/learn.js         EXIT=0
  ```

---

## 4. The live routes answer

The server was **started for real on port 8799** with a throwaway data folder, so this is the live
evidence the task asked for and not a substitute for it.

- [x] **Throwaway data folder, made with `cygpath -w`.** Command:
  ```
  mkdir -p .proof-data
  cygpath -w "$(cd .proof-data && pwd)"
  ```
  Printed `C:\Users\Asus\Documents\deepseek-harness\default-workspace\peakcut\.proof-data`.

- [x] **Started with both variables set**, as a background job:
  ```
  export PEAKCUT_PORT=8799
  export PEAKCUT_DATA="$(cygpath -w "$(cd .proof-data && pwd)")"
  python -m studio.server > .proof-server.log 2>&1
  ```
  Log line 1 is **not** the banner: it is a FastAPI `on_event is deprecated` `DeprecationWarning`
  from `studio/server.py:55` (pre-existing, not a wave 3 file). The banner is on line 16:
  ```
  grep -n "PeakCut is running" .proof-server.log
  -> 16:  PeakCut is running:  http://127.0.0.1:8799
  ```

- [x] **`/healthz` answered on the first poll.** Command: a bounded `curl` poll loop. Printed:
  ```
  healthz ready on attempt 1: HTTP 200
  {"ok":true}
  ```

- [x] **`GET /api/learn/state`** -> `HTTP 200`, body:
  ```
  {"rounds":[],"current":null,"can_run":false,"why_not":"The AI is not set up, so PeakCut cannot read the numbers for you yet. Add a key under Settings, AI.","content":{"clips":0,"lines":["No clips have been made yet, so there is no content to compare."],"per_style":{},"per_len":{}},"settings":{"style":"hormozi","hook_words":"","captions_always":true,"clip_len":30,"sound":""}}
  ```

- [x] **`GET /api/learn/signals`** -> `HTTP 200`, body:
  ```
  {"hook":"","length":"","drop":{"at":null,"kept":null},"points":0}
  ```

- [x] **`GET /api/learn/arms`** -> `HTTP 200`, body:
  ```
  {"trial":null}
  ```

- [x] **`GET /api/learn/cost`** -> `HTTP 200`, body:
  ```
  {"calls":0,"tokens":0,"at":0.0,"report":"8 of 8 rounds left today, and 60,000 of 60,000 tokens."}
  ```
  All four answered `type=application/json`. These are the empty-install shapes the review's
  "What I could not verify" item 4 predicted, and the cost sentence is the one M4 was about, now
  agreeing with `MAX_CALLS_PER_DAY = 8`.

- [x] **A bad query parameter does not become a 500.** `signals?days=7` and `signals?days=abc` both
  `HTTP 200` with the same empty shape `{"hook":"","length":"","drop":{"at":null,"kept":null},"points":0}`.

- [x] **The arms route really writes, reads back, and deletes.** Not just a GET that returns null:
  ```
  POST   {"target":"style","value":"bold","other":"hook_words","other_value":"short"}
         HTTP 200 {"trial":{"at":1795147555.7244475,"target":"style","value":"bold","other":"hook_words","other_value":"short","arm":"a","runs":[]}}
  GET    HTTP 200 {"trial":{"arm":"a","at":1795147555.7244475,"other":"hook_words","other_value":"short","runs":[],"target":"style","value":"bold"}}
  DELETE HTTP 200 {"trial":null}
  GET    HTTP 200 {"trial":null}
  ```
  The GET returns the same trial with keys reordered, which is the JSON object coming back off disk.

- [x] **The two deliberate refusals are sentences, with 400 and not 500.** `POST /api/learn/arms`:
  ```
  {"target":"nonsense"}
    HTTP 400 {"detail":"PeakCut does not change a setting called nonsense. The settings it can try are: style, hook_words, clip_len, sound, captions_always."}
  {"target":"style","other":"style"}
    HTTP 400 {"detail":"A trial needs two different settings. The same setting twice cannot say which change did it."}
  ```
  These are the exact two `ValueError`s at `studio/ai_arms.py:96` and `:99`, caught at
  `studio/api_learn.py:261-262` and turned into 400s.

- [x] **The writes landed in the throwaway folder, not the repo's `data/`.** The throwaway folder holds
  `fonts models peakcut.db peakcut.db-shm peakcut.db-wal posts.json tmp users`, and its database was
  touched at `09:26`. The repo's own `data/` mtime is `09:06`, **before** this run, so the live server
  wrote nothing into the repo. This is the PEAKCUT_DATA redirection working, checked rather than
  assumed.

- [x] **Stopped, and proven stopped.** After `job_kill`:
  ```
  curl --max-time 3 http://127.0.0.1:8799/healthz  ->  HTTP 000   (curl exit 7, connection refused)
  netstat -ano | grep -c ':8799.*LISTENING'        ->  0
  ```
  No listener, no orphan. The throwaway folder was deleted afterwards.

---

## 5. Every claim in REVIEW.md has a fix in FIXES.md or an explanation

REVIEW.md carries exactly **eight** findings, at `REVIEW.md:270` (C1), `:337` (I1), `:373` (I2),
`:405` (M1), `:416` (M2), `:435` (M3), `:447` (M4), `:461` (M5). FIXES.md has a section for every one
of them, at `FIXES.md:27`, `:91`, `:169`, `:226`, `:260`, `:301`, `:322`, `:349`, and closes with
`Findings I did not change, and why` (`FIXES.md:407`) and a per-finding table (`FIXES.md:488`).
**All eight are mapped. Six were fixed; two (M2, M3) are deliberately not fixed and are explained.**
I did not take that mapping on trust - each one was re-run against the tree:

- [x] **C1 (critical) - fixed.** The claim was that `hookscore.py` attributed three numbers to the brief
  that the brief never states. Two checks:
  ```
  grep -n "2\.5\|words a second\|words per second\|reading rate\|two second\|2 second\|bare question" \
       docs/swarm4/WAVE3-BRIEF.md
  -> no output, EXIT=1            (the brief really does not contain them)

  grep -n "brief" studio/hookscore.py
  -> no output, EXIT=1            (no attribution survives in the file)
  ```
  The comments now claim only PeakCut's own preference: `studio/hookscore.py:25`
  `PENALTY_BARE_QUESTION = 45    # PeakCut treats this as a failure on its own, so it has to cost real
  points`, and `:33-34` `WORDS_PER_SECOND = 2.5  # PeakCut's own reading pace... not a measurement of
  any person`. The one page-facing sentence at `:186-188` is hedged, and prints live as:
  ```
  At PeakCut's own pace of 2.5 words a second, this takes about 2.4 seconds to say, and PeakCut wants the first line inside 2.
  ```
  Re-running FIXES' own proof command `grep -rn "the brief" studio/hookscore.py studio/learn.py
  studio/learn_guard.py docs/swarm4/wave3/hook-testing.md` returns exactly the two hits FIXES documents
  (`hook-testing.md:45`, which denies an attribution, and `:95`, which is about file ownership). **Fixed.**

- [x] **I1 (important) - fixed.** The claim was that a 3-word minimum contradicted `studio/brain.py:88`,
  whose own examples are two words. `studio/hookscore.py:32` now reads `MIN_WORDS, MAX_WORDS = 2, 7`
  and `:39` `STRONG_AT, WORKABLE_AT = 85, 40`. Scored live, the product's own four examples:
  ```
  '1 VS 3'      100 strong    ['It breaks none of the rules this check knows.']
  'THE SHOT'    100 strong    ['It breaks none of the rules this check knows.']
  'HE GOT ME'   100 strong    ['It breaks none of the rules this check knows.']
  'CLUTCH'       75 workable  ['It is 1 word long, under the 2 PeakCut reads as a hook.']
  ```
  All three of the review's broken cases now read `strong`; the single word that the review left as a
  judgement call is `workable`, not `strong`. The second half of I1 - that one fault should not leave a
  phrase labelled `strong` - also holds:
  ```
  'okay so here we go'                       80 workable  (one filler)
  'what if it was all fake'                  80 workable  (one pace sentence)
  'one two three four five six seven eight'  62 workable  (two faults)
  'one two three four five six seven eight nine'  54 workable
  ```
  One stated fault now drops the phrase out of `strong`. **Fixed.**

- [x] **I2 (important) - fixed.** The claim was that the cooldown refusal could promise "0 h 0 min".
  Re-ran FIXES' own reproduction, which is the screen path `_why_not` with a round stamped so that the
  given number of seconds remains:
  ```
  wait=   0.4 -> 'Your settings were changed 5 h 59 min ago. A change needs time to show anything,
                  so the next round can start in less than a minute.'
  wait=    45 -> '... so the next round can start in 1 min.'
  wait=    61 -> '... so the next round can start in 1 min.'
  wait=  7200 -> '... so the next round can start in 2 h.'
  ```
  Same four sentences as `FIXES.md:216-219`, and **no "0 h 0 min" is reachable**. The helper itself is
  `_wait_text` (`studio/learn.py:126`), `mins = int(max(0.0, float(seconds) + 59) // 60)`, which rounds
  to the nearest whole minute and never returns a bare `0 min`:
  ```
  _wait_text(0.4)   -> 'less than a minute'
  _wait_text(59.9)  -> '1 min'
  _wait_text(61.0)  -> '2 min'
  _wait_text(119.9) -> '2 min'
  _wait_text(7200)  -> '2 h'
  ```
  The one thing I will not overclaim: the docstring says "rounded up so it never promises a moment that
  is still refused", and across 2990 probe points from 1.0 s to 300.0 s it is early 36 times, by at most
  0.6 s, in the sixth-of-a-minute band just past each whole minute (`_wait_text(60.1)` -> `'1 min'`).
  That is a sub-second artefact of nearest-minute wording, it is not the I2 finding, and no user can act
  on it; the finding - a refusal that read "0 h 0 min" - is gone. The gate itself is
  untouched and still correct, proven with the AI gate stubbed so the time rule is isolated:
  ```
  no rounds ever             _may_run = True
  just now                   _may_run = False
  1 s short of six hours     _may_run = False
  exactly six hours          _may_run = True
  six hours plus one second  _may_run = True
  ```
  `MIN_ROUND_SECONDS = 21600 = 6.0 h`. **Fixed**, and the sentence the tests pin still reads
  `"next round can start"` (`tests/test_learn.py:216`, `tests/test_learn_api.py:188`).

- [x] **M1 (minor) - fixed.** The claim was that the five new routes had no test. `tests/test_learn_api.py:242-247`
  loops all five, with `delete()` added to `_Caller` at `:66-68`. The arms round trip is covered beyond
  existence - `:249-300` checks the trial's shape, both settings, both values, the `arm: "a"` start, the
  read-back after save, the delete, and that reading after the delete says there is none. Count
  39 -> 76, and section 2 above proves those lines execute rather than merely exist. **Fixed.**

- [x] **M4 (minor) - fixed.** The claim was a stale docstring example. `studio/learn_guard.py:151`
  now illustrates with the real ceiling:
  ```
  """One sentence about how much is left today, for the Improve page: "8 of 8 rounds left today".
  ```
  and the function actually returns `8 of 8 rounds left today, and 60,000 of 60,000 tokens.`, which
  matches `MAX_CALLS_PER_DAY = 8` at `:29`. The live route returned the same sentence (section 4). **Fixed.**

- [x] **M5 (minor) - fixed at the cause.** The claim was scratch data folders left in `tests/`.
  `.gitignore` now ends with a `tests/*-data/` rule plus `tests/tmpdata/` and `tests/learnprobe/`
  (`:37`). Every folder the review named is covered by matching rules:
  ```
  tests/learnprobe         -> tests/learnprobe/
  tests/learn-signals-data -> tests/*-data/
  tests/learn-data         -> tests/*-data/
  tests/learnapi-data      -> tests/*-data/
  ...and the seven pre-existing ones (analytics-data, gate-data, mood-data, overhaul-data,
  settings-data, tmpdata, trends-data) match too.
  ```
  The review called these "harmless... housekeeping rather than a defect", and FIXES chose an ignore
  rule over deletion, which is the option that makes the next test run leave the tree clean. **Fixed.**

- [x] **M2 (minor) - not fixed, and correctly explained.** The claim was that five of eight new modules
  are unreachable from the app. Re-measured:
  ```
  learn_signals <- studio/api_learn.py studio/learn.py
  hookscore     <- (tests only)
  ai_arms       <- studio/api_learn.py
  learn_guard   <- studio/api_learn.py
  learn_report  <- (tests only)
  schedule_ai   <- NONE
  brand_ai      <- NONE
  prompt_text   <- NONE
  ```
  That is **the review's claim exactly, still true**. FIXES agrees it is real, records it as not a
  defect of the code (the brief's item 7 assigns the wiring to the next owners), and writes down the
  exact change the next step needs. Matches `FIXES.md:407`'s statement that it is "record-only". This is
  an **explanation, not a fix**, and it is honest about being one.

- [x] **M3 (minor) - not fixed, and correctly explained.** The claim was that three modules are imported
  by no test. Re-measured: `learn_signals`, `hookscore`, `ai_arms`, `learn_guard`, `learn_report` each
  appear in `tests/test_learn_signals.py`; `brand_ai`, `prompt_text` and `schedule_ai` appear in **no**
  test file. Still true, same as M2. FIXES records the 940 untested lines and when they should get tests.
  An **explanation, not a fix**.

- [x] **No finding was rejected, and no finding was silently dropped.** `FIXES.md:407` opens "None of
  the eight findings was wrong." Cross-checking the two documents, each finding has either a code change
  (C1, I1, I2, M1, M4, M5) or a written reason for leaving it (M2, M3). There is no ninth claim in
  REVIEW.md's finding list left unmapped.

- [x] **The review's non-finding claims still hold after the edits**, checked because a fix can quietly
  break a pass. `studio/learn.py`'s dry bypass is intact at `:539` `if not dry and not _may_run(data):`
  (the review cites `:529`, which moved when I2 added lines - the code is the same, the line number is
  not, and FIXES records the move), writes gated at `:552`, `:581`, `:594`, honest path at `:551`
  (`"effect": "Nothing was changed, so there is no effect to look for."`) and `:593`
  (`"Not known yet. The next round compares these numbers against the ones above."`). A dry preview on
  isolated data returned `applied: []` and wrote **no** `learn.json`. Both LEAD-RECHECK items survived
  the wave: `web/feat/learn.js:259` is `<button class="btn sm" data-act="lrndry">What would it change?</button>`
  with no `disabled`, and the `.did` line at `:229`/`:235` renders only when `said` is non-empty.

- [x] **The standards the review said were met are still met.** `grep` for fastapi across the eight new
  modules exits 1 (none), and outside the `api_` files it appears only in `studio/asr_worker.py:17` and
  `studio/server.py:19-21` - all pre-existing. `requirements.txt` still holds exactly **12** pins, so no
  dependency was added. A style scan of the 15 wave files for em dash U+2014, en dash U+2013, `So`-category
  emoji and 16 marketing words printed `files checked: 15  files with a problem: 0`.

---

## Verdict

**PASS.**

Every gate this task asked for passes, and each was run rather than reasoned about:

1. All eight new modules import, none missing (section 1).
2. All five touched test files pass, exit 0, and the ten new route checks are proven to execute rather
   than merely exist (section 2).
3. `studio.server` imports and all 73 files in `studio/` compile, 0 failures (section 3).
4. The server **started on 8799** against a throwaway `PEAKCUT_DATA` made with `cygpath -w`, answered
   `/healthz` on the first poll, returned real bodies on all four learn routes, round-tripped a trial
   through save/read/delete, refused two bad inputs with 400 sentences, wrote nothing into the repo's
   `data/`, and stopped with no listener left behind (section 4).
5. All eight REVIEW.md findings have a FIXES.md section: six fixed and re-verified here, two (M2, M3)
   deliberately left as code with a written explanation. No claim is unmapped (section 5).

Three qualifications, stated so the pass is not read as more than it is:

- **M2 and M3 are explained, not fixed.** 63 percent of the new studio lines are still unreachable from
  the running app, and 940 lines still have no test. That is inside the brief's letter, and FIXES says
  so plainly, but a reader of this wave should not read "PASS" as "the hook score is live". It is not.
- **`python tests/run.py` is not a usable gate for this wave.** It exits 1, correctly, on two
  pre-existing environmental failures (`queue under load`, `the new-version notice`), and separately it
  does not yet run `tests/test_learn_signals.py` at all. The five named files are the wave's gates and
  they were run directly. Updating the runner belongs to whoever owns `tests/run.py`.
- **Two things remain unprovable in this environment**, and no command here closes them: there is no
  git history, so "what changed" is mtime-and-report evidence; and `psycopg`/`sherpa_onnx` are not
  installed, so nothing that needs them could have run. Neither is needed by any check above.

The wave's own share of the work is sound. The one Critical finding was a set of unsourced comments and
a single page-facing sentence, and it is genuinely gone: the brief contains none of the three numbers,
`hookscore.py` no longer claims it does, and the sentence a person reads now says "PeakCut's own pace"
instead of naming a deadline the product never set. The two Important items are fixed in both halves
each - the minimum now matches `brain.py`'s own examples, one fault now drops a verdict out of `strong`,
and the cooldown can no longer promise a wait of zero.

Scope of that statement, so it is not read wider than it goes: I re-ran the proof commands behind **C1,
I1, I2, M1, M4 and M5**, plus the standards checks, and the outputs in section 5 are mine, not quoted
from FIXES. I did not re-execute every command FIXES.md contains line by line; where I did reproduce
them, one sub-second difference in `_wait_text` is recorded under I2 above.
