# Wave 6 — the AI into the pipeline

Read this first, then write. It is short and every line is a rule.

## What exists already, and what is missing

The Improve engine works. `studio/learn.py` reads the numbers, asks the AI what to change, and writes at most two
settings (`style`, `hook_words`, `clip_len`, `sound`, `captions_always`). `studio/brain.py` already carries
`hook_words` into the clip-finding prompt through `_hook_note` and `_rules`.

Wave 3 built five modules that do real work and that almost nothing calls. Measured importer counts:

```
hookscore      1 importer   (a test)
brand_ai       0 importers  <-- writes the brand, nothing uses it
ai_arms        2 importers  (a route and a test)
learn_signals  3 importers
learn_guard    2 importers
learn_report   1 importer
prompt_text    0 importers  <-- duplicate of brain._hook_note, byte-identical output
schedule_ai    0 importers  <-- now reached by GET /api/schedule/round
```

This wave connects the work to the pipeline. A module that is never called is not a feature.

## The rule that matters most

**Never invent a number.** Every value you feed into a prompt, a setting or a sentence must come from
`learn.py`, `api_analytics.py`, `api_stats.py`, `hookscore.py`, or the clip files themselves. If there is no data,
the honest answer is "not known yet", and that is what the page must say.

## Files you may own

Backend slots own one `.py` file each in `studio/`. UI slots own one `.js` file each in `web/feat/`. Test slots own
one file in `tests/`. **Never edit** `web/index.html`, `web/plugins.js`, `studio/server.py`, or another slot's file.
If your work needs a router included in `server.py`, write the router and say in your report that one line is
needed, with the exact line.

## Rules

1. `python -c "import studio.<your module>"` must pass, and `python -m compileall -q studio/<file>.py` must be quiet.
2. `python tests/test_feat_files.py` must still say "All checks passed." if you wrote a `.js` file, and
   `node --check` must pass on it.
3. Escape every server string with `esc()` before it goes into HTML. Handlers live in `PeakCut.add`, never in
   `PeakCut.page`.
4. Plain English, short sentences. No emoji. **No em dash.**
5. Never swallow a failure. No empty `catch {}`, no bare `except: pass`. A refusal is a sentence, not a crash.
6. A setting the AI changes must be one that actually reaches a render. `jobs._brand_prefs` carries `style`,
   `captions`, `clip_len` (as `max_len`) and `sound`; `brain._rules` carries `hook_words`. Anything else would be
   a claim with no effect.
7. The six hour cooldown, `MAX_ROUNDS = 20`, `MIN_SAMPLE_VIEWS = 50` and the words "changes at most two settings"
   must keep working. `tests/test_learn.py` (103 checks) and `tests/test_learn_api.py` (39 checks) both assert
   sentences that people read; read them before you change a sentence.
8. No new dependency.

## Your budget

**25 minutes.** Read only the two or three files you need, then write. Ship a working file; write what is left in
your report.

## Report

Write `peakcut/docs/swarm4/wave6/<slug>.md` under 60 lines: what you added, the file you own, the import check, what
you measured with real numbers, what is still missing, and any one-line edit another file needs.

## Prove it

Reading the code is not proof. Run the module. Print the value it produced. If you changed what reaches a render,
show the setting arriving: `jobs._brand_prefs("u_local")` before and after, or the prompt string containing the
hook note. Numbers, not adjectives.
