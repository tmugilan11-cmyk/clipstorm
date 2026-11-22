# Wave 6 review (read-only)

Reviewed 2026-11-20 by the wave-6 review slot. Nothing was fixed or edited; every claim below was
re-run against the working tree at review time.

## What landed

2 of the 12 wave-6 files exist: `web/feat/learn-report.js` and `web/feat/review-hooks.js`, plus their
two reports (`learnreport-ui.md`, `review-hooks.md`) and one screenshot. The other 10 slots never
landed a file.

## Checks run

- `node --check web/feat/learn-report.js`: pass. `node --check web/feat/review-hooks.js`: pass.
- `python -m py_compile` on the five backend slots: cannot run, the files do not exist (finding 2).
- `python tests/test_wiring.py`: cannot run, the file does not exist (finding 2). The closest
  existing gate does run: `python tests/test_feat_files.py` prints `{"files": 64, "checks": 518}`
  and "All checks passed.", exactly matching the numbers in `review-hooks.md`, and
  `learnreport-ui.md`'s earlier 63 files / 510 checks is the consistent state one file earlier
  (each file adds 8 checks).
- Route safety: both delivered files only ever GET (`/api/learn/report` at learn-report.js:142,
  `/api/learn/hooks` at review-hooks.js:58). Neither writes a brand or a clip, neither touches a
  setting, neither uses `PeakCut.page`; handlers sit in `PeakCut.add` (learn-report.js:175,
  review-hooks.js:127).
- Escaping: every server string in `learn-report.js` goes through its local `esc()`
  (learn-report.js:85, 86, 87, 88); the fixed header markup carries only the file's own words
  (learn-report.js:112-118). `review-hooks.js` renders the score through `textContent`
  (review-hooks.js:68) and escapes the failure line (review-hooks.js:76), with one caveat
  (finding 4).
- Em dash, en dash and emoji scan over both files and both reports: zero matches. Plain short
  English throughout, both reports under the 60-line budget.
- Report honesty: `GET /api/learn/report` and `GET /api/learn/hooks` really are absent from the
  server (no reference in any studio/*.py file), so both reports' "404, route not landed yet"
  claims are true. The claimed live counts (64 served, 64 in `PeakCut._order`) match the tree:
  web/feat holds 64 servable .js files. File timestamps line up with the sequence both reports tell.

## Findings

1. **CRITICAL:** `review-hooks.js` can show a fabricated score of "Hook 0" for a clip the server
   gave no number for. In JavaScript `Number(null)`, `Number("")` and `Number(false)` all return 0,
   which passes the finite-number guard, so a null or empty score survives into the cache: the
   nested-map path passes null straight through (review-hooks.js:47), the list path admits empty
   strings and booleans because `e.score != null` is true for both (review-hooks.js:39), and the
   guard only rejects non-finite results (review-hooks.js:28-32). The pill then renders "Hook 0"
   (review-hooks.js:68). This breaks the file's own promise, stated in its header: "no dashes, no
   zeros, nothing invented" (review-hooks.js:2-3), and the wave's top rule: "Never invent a number"
   (WAVE6-BRIEF.md:28). It is latent until `/api/learn/hooks` ships, but that route is this same
   wave's missing backend slot and the file advertises both payload shapes, so the first real
   payload can trip it. The guard must treat null, empty string and booleans as "no score", the
   same way it already treats NaN.

2. **IMPORTANT:** 10 of the 12 wave-6 files do not exist. Missing: studio/api_hooks.py,
   studio/api_brandai.py, studio/api_learnreport.py, studio/posttime.py, studio/api_posttime.py,
   web/feat/learn-hooks.js, web/feat/brand-ai.js, web/feat/post-time.js, web/feat/learn-arrows.js,
   tests/test_wiring.py (verified by direct file check, 2026-11-20). The wave's purpose, wiring
   brand_ai, prompt_text and schedule_ai into the pipeline (WAVE6-BRIEF.md:11-24), is unmet. No
   half-finished imports were left behind: server.py references none of the missing module names,
   so the app still boots. Two checklist gates are impossible until the slots land: py_compile on
   the backend files, and the required green run of tests/test_wiring.py.

3. **IMPORTANT:** 13 of the 15 expected wave-6 documents are missing. docs/swarm4/wave6/ holds only
   learnreport-ui.md and review-hooks.md; no audit files exist. The brief requires one report per
   slot (WAVE6-BRIEF.md:63). The two reports that did land are honest: both name their missing
   backend route as "not known yet" instead of pretending it exists, and every number they quote
   reproduces at review time.

4. **MINOR:** `review-hooks.js` calls a global `esc()` it never defines (review-hooks.js:76). It
   only resolves because index.html declares a top-level `const esc` (index.html:883) and
   plugins.js loads features as classic scripts that share the page's global scope
   (plugins.js:243-244). Every sibling feature file defines its own local esc instead
   (learn-report.js:31, learn.js:44). If index.html is ever refactored or the loader switches to
   module scripts, the failure line dies with a ReferenceError, which the catch at
   review-hooks.js:106 reduces to a console.warn, so the user-facing failure sentence would
   silently disappear.

5. **MINOR:** `learn-report.js` says "No report is saved yet" for answers that carry no shape at
   all. `textOf()` maps null, undefined and an empty object to the empty string
   (learn-report.js:68 `if (!body) return ""`, and learn-report.js:77), which renders the
   "not saved yet" note (learn-report.js:87). The file's own contract promises the opposite: an
   answer with no text field must produce the "no plain text this card can show" sentence, so
   "empty" is never claimed when the shape simply did not match (learn-report.js:56-61, and
   learnreport-ui.md:11-12).

Critical: 1
