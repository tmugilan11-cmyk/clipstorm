# Wave 6 proof

Run 2026-11-20, 19:23 to 19:28 local time, from the repo root
`C:/Users/Asus/Documents/deepseek-harness/default-workspace/peakcut`.
Every numbered line below is a command that was run and the output it produced.
Nothing is claimed without the command next to it.

## 1. python -m py_compile on each new studio file

Wave 6 owns five backend slots. None of them landed a file, so there is nothing
new to compile. The existence check first:

1. Command: `for f in studio/api_hooks.py studio/api_brandai.py studio/api_learnreport.py studio/posttime.py studio/api_posttime.py; do if [ -e "$f" ]; then echo "EXISTS  $f"; else echo "MISSING $f"; fi; done`
   Output:
   ```
   MISSING studio/api_hooks.py
   MISSING studio/api_brandai.py
   MISSING studio/api_learnreport.py
   MISSING studio/posttime.py
   MISSING studio/api_posttime.py
   ```
2. Command: `python -m py_compile studio/api_hooks.py studio/api_brandai.py studio/api_learnreport.py studio/posttime.py studio/api_posttime.py`
   Output (stderr): `[Errno 2] No such file or directory: 'studio/api_hooks.py'`, exit code 1.
   The wave 6 backend compile gate cannot run: there are zero new studio files.
3. Command (tree-wide substitute gate, same style the brief uses in rule 1):
   `python -m compileall -q studio/`
   Output: none (quiet), exit code 0. Every studio module that exists, including
   the files other waves touched tonight, compiles clean.

## 2. node --check on each new web/feat file

Two of the six wave 6 frontend slots landed: web/feat/learn-report.js and
web/feat/review-hooks.js (last touched tonight at 19:21 and 19:20 by the fix
pass). The other four never landed.

4. Command: `node --check web/feat/learn-report.js`
   Output: none, exit code 0. Pass.
5. Command: `node --check web/feat/review-hooks.js`
   Output: none, exit code 0. Pass.
6. Command: `node --check web/feat/learn-hooks.js` (representative of the four slots that never landed)
   Output: `Error: Cannot find module 'C:\...\peakcut\web\feat\learn-hooks.js'`, `code: 'MODULE_NOT_FOUND'`, exit code 1.
   brand-ai.js, post-time.js and learn-arrows.js are also absent from web/feat/.

## 3. The four test gates

7. Command: `python tests/test_wiring.py`
   Output (stderr): `can't open file '...peakcut\tests\test_wiring.py': [Errno 2] No such file or directory`, exit code 2.
   The wiring gate does not exist. Its slot never landed the file, so this
   commanded gate cannot run and the wave wiring stays unproven by it.
8. Command: `python tests/test_feat_files.py`
   Output: `{"files": 64, "checks": 518}` then `All checks passed.`, exit code 0.
   Both landed wave 6 files pass all 8 checks each (learn-report.js and
   review-hooks.js each print 8 ok lines: parses, declares one plug-in, named
   after itself, only owner, does not write into index.html, markup rule, no
   absolute origin, no clashing id). The numbers match the fix pass report.
9. Command: `python tests/test_learn.py`
   Output: `All checks passed. 103 ok`, exit code 0.
10. Command: `python tests/test_learn_api.py`
    Output: `All checks passed. 76 ok`, exit code 0.
    Note: the brief quoted 39 checks for this suite; it has grown since the brief
    was written. 76 is the number measured now, and all are green.

## 4. grep for prompt_text

11. Command: `grep -rnI "prompt_text" studio/ --include="*.py"`
    Output: no matches, exit code 1. Zero studio source references the name.
12. Command: `grep -rn "import prompt_text\|from studio import.*prompt_text\|import studio.prompt_text" studio/ --include="*.py"`
    Output: no matches, exit code 1. No import of the module exists in studio/.
13. Command: `grep -rnI "prompt_text" .` (whole repo, text files only)
    Output: matches only under docs/: docs/swarm4/WAVE4-BRIEF.md:20,
    docs/swarm4/WAVE6-BRIEF.md:20, docs/swarm4/wave6/REVIEW.md:56, and several
    docs/swarm4/wave3/ files. Not one match in studio/ source.
14. Command: `ls -l studio/prompt_text.py`
    Output: `-rwxrwxrwx 1 Administrators None 5196 Nov 20 07:42 studio/prompt_text.py`
    Verdict, stated honestly: the name is gone from studio source (zero
    references), but the file itself is NOT gone from studio/.
    studio/prompt_text.py still exists, unchanged since 07:42 this morning, and a
    stale compiled copy sits at studio/__pycache__/prompt_text.cpython-315.pyc.
    The removal this proof was asked to show did not happen. It is true the
    module was already dead code before the wave (the brief measured 0
    importers), so nothing calls it; but "gone from studio/" only holds for
    references, not for the file.

## 5. New route files and the include lines they need

15. Command: `grep -rn "router = APIRouter" studio/*.py`
    Output: 13 route files define a router:
    api_analytics.py:35, api_auto.py:27, api_brand.py:25, api_history.py:24,
    api_learn.py:35, api_memesound.py:33, api_preview.py:29, api_review.py:19,
    api_sound.py:24, api_stats.py:23, api_style.py:25, api_text.py:32,
    api_trends.py:42.
16. Command: `grep -n "include_router" studio/server.py`
    Output: 13 lines, numbered 245 to 257: api_brand, api_preview, api_style,
    api_sound, api_stats, api_auto, api_text, api_history, api_review,
    api_analytics, api_learn, api_trends, api_memesound.
    Cross check: the 13 defined routers and the 13 included routers are the same
    set. New route files from wave 6: 0 (the four expected backend route slots
    api_hooks.py, api_brandai.py, api_learnreport.py, api_posttime.py never
    landed). Include lines needed from wave 6: 0. There is nothing for the lead
    to register after this wave.

## Verdict

Every gate that exists is green: 518 + 103 + 76 checks pass, both landed JS
files parse, the whole studio tree compiles. The wave is not fully green,
because tests/test_wiring.py does not exist so one commanded gate cannot run,
10 of the 12 wave 6 files never landed, and studio/prompt_text.py still exists
on disk.
