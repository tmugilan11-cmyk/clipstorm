# Wave 6 fixes

Fix pass over docs/swarm4/wave6/REVIEW.md, 2026-11-20. Every CRITICAL and IMPORTANT finding was
addressed in the file that owns it, or recorded here with the reason it cannot be fixed in this
pass. Only the owning files were touched: web/feat/review-hooks.js and web/feat/learn-report.js.
Nothing was edited in web/index.html, web/plugins.js, studio/server.py, studio/learn.py or
studio/jobs.py.

| # | Severity | File | Finding | Result | What was done, or why not |
|---|---|---|---|---|---|
| 1 | CRITICAL | web/feat/review-hooks.js | `Number()` coerces null, empty string and false into a fake 0, so a clip the server gave no score for could show a pill "Hook 0" | fixed | The score guard `num()` now returns null for null, undefined, booleans, and empty or blank strings before `Number()` runs, the same way it already rejected NaN. A real number from the server, including a real 0, still shows; numeric strings like "85" still work. The owning gate was re-run green and the guard was proven with a node check: null, "", "   ", false, true, undefined, NaN and Infinity all drop; 85, "85", 4.5 and 0 survive. |
| 2 | IMPORTANT | 10 missing files | studio/api_hooks.py, studio/api_brandai.py, studio/api_learnreport.py, studio/posttime.py, studio/api_posttime.py, web/feat/learn-hooks.js, web/feat/brand-ai.js, web/feat/post-time.js, web/feat/learn-arrows.js, tests/test_wiring.py do not exist | recorded-not-fixed | These slots never landed a file, so there is nothing to fix; writing them is implementation work that belongs to those slots, not a fix pass. Wiring the backend modules would need one line in studio/server.py, which this pass is forbidden to touch. Verified today by direct file check: none of the ten paths exist, and server.py references none of the missing names, so the app still boots. Because tests/test_wiring.py is one of the missing files, the wiring gate cannot run: `python tests/test_wiring.py` fails with "[Errno 2] No such file or directory". The wiring stays unverified. |
| 3 | IMPORTANT | docs/swarm4/wave6/ | 13 of the 15 expected wave-6 documents are missing; only learnreport-ui.md and review-hooks.md landed | recorded-not-fixed | A report belongs to the slot that shipped the file it reports on. Writing audit papers for files that do not exist would fabricate records, against the wave's own honesty rule. The two landed reports are honest and reproduce. This FIXES.md is the fix pass report. |
| 4 | MINOR | web/feat/review-hooks.js | quietLine() calls a global `esc()` the file never defines; it only resolves through index.html's top-level const and would die silently inside the catch if the page changed | fixed (minor, fixed alongside finding 1 in the same owned file) | The file now defines its own local `esc()`, the same helper shape its sibling features carry (learn-report.js, learn.js). The failure line no longer depends on the page's global. Gate re-run green. |
| 5 | MINOR | web/feat/learn-report.js | textOf() mapped a missing body and an object with no text key to the empty string, so the card said "No report is saved yet" when the answer simply had no shape | fixed (minor, fixed alongside the owned-file pass) | Both paths now return null, which renders the honest sentence "The report arrived without plain text this card can show." Only a real string, including an empty one, can say "not saved yet". Proven with a node check over 15 payload shapes; the owning gate was re-run green. |

## Gates after the pass

- `node --check web/feat/review-hooks.js`: pass.
- `node --check web/feat/learn-report.js`: pass.
- `python tests/test_feat_files.py`: `{"files": 64, "checks": 518}`, then "All checks passed."
- `python tests/test_wiring.py`: cannot run, the file does not exist (finding 2).

The file check counts did not move (64 files, 518 checks, same as the review's numbers), because
both fixes stayed inside the two files that already landed and added no plug-in.
