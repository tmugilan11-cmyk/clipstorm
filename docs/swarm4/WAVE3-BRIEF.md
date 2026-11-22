# Wave 3 brief: the AI reads deeper

Wave 2 is closed: `docs/swarm4/wave2/SIGNOFF.md`. Read `docs/swarm4/CONTRACT.md`,
`docs/swarm3/CONTRACT.md` and `web/feat/heard.js` before you write anything.

## What exists, so you do not rebuild it

`studio/learn.py` (639 lines) already does: `facts(days)` -> channel lines; `content(days)`
-> what PeakCut's own clips say (look, length, hooks, sounds, views); `measure(days)` and
`compare(before, after)` -> "Views up 50 percent, from 1000 to 1500."; `run(days, dry)` ->
one round that asks the AI and applies at most two settings; `undo(at)`; a 6 hour cooldown that
does NOT apply to `dry`.

`studio/api_learn.py` (114 lines): `GET /api/learn/state`, `POST /api/learn/run`,
`POST /api/learn/undo`. `web/feat/learn.js` (290 lines) is the Improve page.

`the five settings`: `style`, `hook_words`, `clip_len`, `sound`, `captions_always`.
`MIN_SAMPLE_VIEWS = 50`, `MIN_ROUND_SECONDS = 6h`, `MAX_ROUNDS = 20`.

## What wave 3 adds

1. **Signals from the retention curve** — where people actually stop watching, turned into a
   sentence about the hook and the length. New file `studio/learn_signals.py`.
2. **A hook score** — whether a phrase reads like a hook, so a hook can be judged without
   waiting for views. New file `studio/hookscore.py`.
3. **Arms** — two settings tried in turn, so a round can say which one worked. New file
   `studio/ai_arms.py`.
4. **A guard** — how much a round may cost and how often it may spend. New file
   `studio/learn_guard.py`.
5. **A report** — the round's story in one shape the page can draw. New file
   `studio/learn_report.py`.
6. **Two new panels on Improve** — `web/feat/learn-signals.js`, `web/feat/learn-arms.js`.
7. Then three owners wire it in: `studio/learn.py`, `studio/api_learn.py`, `web/feat/learn.js`.
8. Tests, docs, review, fix, prove.

## Rules that decide whether your work survives

- **One file, one owner.** Never edit a file another agent owns in the same wave. The three
  wire agents own `learn.py`, `api_learn.py`, `learn.js` and nobody else touches those.
- **Never invent a number.** A signal with no data is a sentence saying what is missing.
- **No new dependency.** NumPy, stdlib, FastAPI and what is already installed. Nothing else.
- **Fail soft.** A missing module or a bad answer must not stop a round.
- Every public function gets a plain-English docstring; comments explain WHY.
- Plain English, no em dash, no emoji, no marketing words.
- Run `node --check` on JS, `python -m py_compile` on Python, and the two gates you can run.
- Report to `docs/swarm4/wave3/<slug>.md`: what you built, the file you own, the exact command
  you ran and what it printed, and anything you could not do.
