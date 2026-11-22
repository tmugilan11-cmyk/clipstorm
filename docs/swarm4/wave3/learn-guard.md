# learn-guard: the brake on Improve rounds

Skill loaded: `python-patterns`.

## What I built

`studio/learn_guard.py`, the module that stops a round of Improve from spending too much of the
operator's own AI budget.

It holds two ceilings for one person over a rolling 24 hours:

- `MAX_CALLS_PER_DAY = 8`. `studio/learn.py` already refuses a second round inside six hours, which
  is at most four rounds a day. Eight is twice that, so a person who takes every round the moment it
  is offered is never refused. A loop that ignores the six hour wait still stops the same morning
  instead of running until the key has no credit left.
- `MAX_TOKENS_PER_DAY = 60_000`. One round sends a dozen sentences about the channel and reads back
  a small JSON answer, which is a few thousand tokens on a small model. Eight of those stay well
  under 40,000, so 60,000 never refuses an honest day. It does stop the shapes that cost real money:
  a model that writes pages, or `brain.ask_ai` retrying three times on every model after a rate
  limit.

Both ceilings look back over the last 24 hours rather than resetting at midnight, so a budget never
comes back in the middle of a working night.

The four functions the brief asked for:

- `spent(uid)` -> `{"calls": int, "tokens": int, "at": float}`, the rounds inside the last 24 hours.
  `at` is when the newest one ran, or `0.0` when there was none.
- `allow(uid)` -> `{"ok": bool, "why": str}`. `ok` is False only when a ceiling is used up, and `why`
  is then one sentence naming that ceiling and how long until it frees. It answers True when the
  record cannot be read: a record PeakCut cannot see cannot prove a ceiling was reached, and the AI
  key's own quota is still the backstop.
- `note(uid, tokens)` -> records one round at the current time with the tokens it reported.
- `report(uid)` -> one sentence for the page, such as
  `5 of 8 rounds left today, and 54,000 of 60,000 tokens.`

## The file I own

`studio/learn_guard.py`. I edited no other file. I did not touch `web/index.html`.

### Where a round is recorded, and why there

The brief said to write into the place `usage.py` already keeps its numbers if that is clean, and
otherwise a small JSON file under `config.DATA_DIR`. **I chose the small JSON file**, one per person,
at `config.user_dir(uid) / "learn_spend.json"`.

The reason is that the numbers are already there. `brain.ask_ai` in `studio/brain.py` calls
`usage.record(sent, wrote, purpose)` on every AI call, so each round's tokens are already a row in
the `usage` table and already shown on the AI usage page. Writing a second row for the same round
would show the operator one call twice and double the token total on that page. And if I instead
summed the round's own rows back out of `usage`, I would be counting every other AI call PeakCut
makes in the same 24 hours, which is not what a round budget means.

The separate file also gives two things the shared table cannot:

- One file per person, so two people running a round at the same moment cannot lose each other's
  count.
- A round is one line here, not three, even though `brain.ask_ai` may try several models before one
  answers. A retry is the same round, and it should not eat three of the eight.

`usage.py` needs no change for this, so there is nothing to ask its owner for.

### Failing soft

Every public function catches its own failures and returns the quiet answer. A record that cannot be
read reads as "nothing has been spent", which is the same rule `learn.py` applies to its own log: a
record of spending must never be the thing that stops a page from drawing. `note` swallows a write
failure too, because a round that already happened must not fail after the fact.

A user id that `config.user_dir` refuses (it only accepts 6 to 40 letters, digits and underscores)
does not raise out of any of them. `config.user_dir` raises `ValueError`, and the guard turns that
into zeros. This matters because the guard makes no assumption that its caller has a signed-in
session.

## The exact command I ran and its literal output

```
$ cd peakcut && python -m py_compile studio/learn_guard.py && echo "PY OK"
PY OK
```

Behaviour, against a scratch data folder set through `PEAKCUT_DATA`:

```
$ cd peakcut && python - <<'PY'
import os, shutil
from pathlib import Path
scratch = Path("tests/_guard_report").resolve()
shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
os.environ["PEAKCUT_DATA"] = str(scratch)
os.environ.setdefault("PEAKCUT_ACCOUNTS", "0")
from studio import learn_guard as g
u = "guard_report_user"
print("limits", g.MAX_CALLS_PER_DAY, g.MAX_TOKENS_PER_DAY)
print("spent ", g.spent(u))
print("allow ", g.allow(u))
print("report", g.report(u))
g.note(u, 4200); g.note(u, 4200)
print("spent ", g.spent(u))
print("report", g.report(u))
for i in range(6): g.note(u, 100)
print("allow ", g.allow(u))
print("report", g.report(u))
shutil.rmtree(scratch, ignore_errors=True)
PY
limits 8 60000
spent  {'calls': 0, 'tokens': 0, 'at': 0.0}
allow  {'ok': True, 'why': ''}
report 8 of 8 rounds left today, and 60,000 of 60,000 tokens.
spent  {'calls': 2, 'tokens': 8400, 'at': 1795137844.8577404}
report 6 of 8 rounds left today, and 51,600 of 60,000 tokens.
allow  {'ok': False, 'why': 'PeakCut has used all 8 rounds allowed in the last 24 hours. The next one can start in 24 h, when the oldest round falls outside that window.'}
report No rounds left today. The next one can start in 24 h.
```

The other cases I ran, each with the value it printed:

| Case | Printed |
|---|---|
| A broken record file (`<<<not json`) | `spent {'calls': 0, 'tokens': 0, 'at': 0.0}` and `allow {'ok': True, 'why': ''}` |
| A user id of two characters, refused by `config.user_dir` | `spent {'calls': 0, 'tokens': 0, 'at': 0.0}`, `allow {'ok': True, 'why': ''}`, `report 8 of 8 rounds left today, and 60,000 of 60,000 tokens.`, `note` returned `None` |
| `note(uid, "nonsense")` | the round is still recorded, with `tokens` 0, so a bad token count cannot make a round free |
| A row dated 25 hours ago | `{'calls': 0, 'tokens': 0, 'at': 0.0}`, so yesterday's rounds stop counting |
| A row dated in the future | still counts, so moving the clock back cannot hand a spent budget back |
| Reaching the token ceiling first | `allow {'ok': False, 'why': 'PeakCut has used all 60,000 tokens allowed in the last 24 hours. The next round can start in 24 h, when earlier rounds fall outside that window.'}` and `report No round can run today: the 60,000 token budget is used up, with 7 of 8 rounds still unused. The next one can start in 24 h.` |

Static checks on the file itself, all printed by a script:

```
functions: ['_file', '_rows', '_recent', 'spent', 'allow', 'note', 'report', '_tokens_clear_at', '_wait_text']
imports: ['None', '__future__', 'json', 'pathlib', 'threading', 'time']
em dash: False | non-ascii: []
mentions fastapi: False
lines: 191
```

`imports` lists `__future__`, `json`, `threading`, `time` and `pathlib` from the standard library
plus `config` from this package. There is no third-party import, so nothing new was added. The
`None` in that list is my own measurement script picking up the `from . import config` line, which
has no module name of its own.

I also ran the repository gate, `python tests/run.py`. It reported two failures, and neither is in
my file:

- `tests/test_abuse.py` failed with
  `AssertionError: {"detail":"There is already an account with that email. Sign in instead."}`. The
  test data folder already holds the account from an earlier run, so the sign-up step it expects to
  succeed is refused. Nothing in that file mentions `learn_guard`.
- `=== queue under load ===` printed
  `FAIL it sees a fully loaded processor   {'cpu': 42, 'ram_free_gb': 6.1, 'disk_free_gb': 611.1, 'busy': False, 'busy_cpu': 82.0}`.
  That is a timing check on the machine's load average, and it is sensitive to what else the machine
  is doing. A grep across `tests/` shows `learn_guard` appears in no test file at all, and it is
  imported by no module in `studio/` yet, because wiring it into `learn.py` belongs to another owner
  in this wave.

## What I could not do

- **Nothing calls this yet.** The brief gives the wiring to a different owner (`studio/learn.py` is
  owned by a wire agent), so `allow` is not consulted before a round starts and `note` is not called
  after one. Until that happens this module is a correct, tested set of four functions that stop
  nothing. What the wire owner needs to add is below.
- **I could not test it after a real round.** There is no AI key on this machine, so I could not run
  `learn.run`, read the tokens it actually reports, and record that. Every token figure above is one
  I passed in myself. The real figure will come from the `tokens` key that `brain.ask_ai` already
  returns into the round as `out["tokens"]` at `studio/learn.py:535`.
- **The ceilings are a judgement, not a measurement.** I have no recorded round costs to size them
  from, so 8 and 60,000 are reasoned from the six hour wait and from "a few thousand tokens a
  round", not fitted to observed data. If a real round turns out to cost far more than a few
  thousand tokens, `MAX_TOKENS_PER_DAY` is the line to change, and it is a one line change.

## What the wire owner needs to add, in files I do not own

These are the changes I did not make. Each is small.

1. `studio/learn.py`, in `run()` at line 477, before the round does any work: call
   `learn_guard.allow(ctx.uid())`, and if `ok` is False, raise `ValueError(why)` so the existing
   error path shows the sentence. Do this for `dry` rounds too. A preview costs a real AI call at
   line 507 and the brief's guard is about spending, not about changing settings.
2. `studio/learn.py`, after `brain.ask_ai` returns at line 507: call
   `learn_guard.note(ctx.uid(), tokens)`. `tokens` is already the third value that line unpacks.
3. `studio/api_learn.py` and `web/feat/learn.js`, if the page should show the sentence: put
   `learn_guard.report(ctx.uid())` into the `GET /api/learn/state` answer and draw it beside the
   button.
4. The guard counts a round as one call however many models `brain.ask_ai` tried, which is what I
   intended. If the wire owner would rather count each attempt, that is a change in `learn.py`, not
   here.
