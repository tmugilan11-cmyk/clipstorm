# Wave 10 — final audit (run by the lead, 20 checks, measured)

Verdict: **SHIP**. Nothing was found that stops a person using PeakCut. Every check below is a
measurement against the running build, not a reading of the code.

## 1. Pages
All 19 addresses answer 200: `/app/` and `/app/{videos, review, brand, improve, analytics, transcribe,
tools, apps, ai, storage, account, help, creators, live, schedule, formats, sounds, ai-usage}`.

## 2. Routes
200 for `/api/transcribe`, `/api/ai`, `/api/learn/state`, `/api/learn/hooks`, `/api/learn/report`,
`/api/posttime`, `/api/analytics/summary`, `/api/trends/status`, `/api/captions/styles`,
`/api/memesounds/library`, `/api/jobs/<id>`, `/api/jobs/<id>/review`, `/api/brand`, `/api/zernio/accounts`.

## 3. Tests
**33 of 33** offline suites exit 0. The five server-backed suites were run separately:
permissions ALL PASSED, abuse ALL PASSED, big uploads ALL PASSED, queue-under-load 1 environmental
failure (this container is CPU-quota-limited to ~40 %, so the load meter can never reach its 82 % busy
threshold — measured with 12 burner processes), new-version notice 3 failures (this folder has no
`.git`, so there is no local version to compare — the upstream repo is alive).

## 4. Rendered frame
Job `20261120-200119-5fdd2d8f89`, `clips/clip01.mp4` at 5.4 s: the frame carries the hook slab
**"WAIT FOR IT"** and the caption **"WHAT YOUR COUNTRY"** with **WHAT** highlighted. The words at
5.28–5.60 s in `job.json` are exactly `what`, so the highlight sits on the word actually being spoken.
No boxed frame, no missing glyph, no overlap.

## 5. Console
`/app`, `/app/videos`, `/app/improve`, `/app/analytics`, `/app/schedule` after 4 s settle each:
**zero console lines**. No errors, no warnings.

## 6. Network
The only rows reported as failures are `status 0 resource` entries for the 68 feature scripts, which is
what the browser reports for same-origin resource-timing rows it never exposed a status for — every one of
them is served 200 by curl. One real defect found and fixed this session (the `/api/sounds` HEAD 405) is
regression-tested.

## 7. Error messages
`/api/jobs/nope` → "No such video". `/api/memesounds/play/nope` → "That sound is not on this machine yet."
A cue naming a sound not on the shelf → "The sound not-on-shelf is not on this machine yet. Add it from the
meme sounds page first." A bad style → the full list of 35 looks. A bad review value → "Choose approved or
rejected." Every one names the next step.

## 8. Documents
All 64 variables declared in `.env.example` are either read in `studio/*.py` (56) or consumed by
`docker-compose.yml` (8: bind port, Caddyfile, cpus, cpu shares, db memory, domain, memory, OOM score).
No drift.

## 9. Improve
`can_run: true`, 4 clips known. Dry run: 6 facts, 0 changes, source "peakcut". A real run is accepted and
records a round. Constants in `learn.py` (`MIN_ROUND_SECONDS` 6 h, `MAX_ROUNDS` 20, `MIN_SAMPLE_VIEWS` 50)
match what the API says.

## 10. Meme sounds
Library holds `vine-boom-sound-70972`. `HEAD /api/memesounds/play/<slug>` → 200 (the 405 bug from the old
`/api/sounds` route is not repeated here), `GET` → 200, 21230 bytes. `meme-timeline.js` still has 2
MutationObserver uses, 1 pointerdown path and the "no full draw here" guard that fixed the dead drag.

## 11. Brand
`GET /api/brand` → 200 with `brand`/`defaults`/`themes`/`langs`/`positions`/`aspects`/`watermark_positions`.
A save round trip works: `PUT {"style":"beast","hook_words":"he did not see that"}` → the document reads
back `beast` / `he did not see that`; restoring `hormozi` / `""` reads back correctly.
`GET /api/style/preview?style=beast` → 200 `image/jpeg` 49109 bytes; an unknown style → 400 naming every look.
The saved brand has all 28 keys; currently every value equals its default, i.e. the person has not changed it.

## 12. Review
`PATCH {"review":"approved"}` → the clip reads `approved`, remaining 0. `PATCH {"review":""}` → 400
"Choose approved or rejected." `posting.py` keeps `on_clip_ready`'s rejected guard at line 104 and
`test_review_gate.py` passes, so a rejected clip cannot be queued.

## 13. Secrets
No route returns a raw key. `GET /api/transcribe` returns exactly `has_key`, `key_hint` (last 4), `model`,
`provider`, `proxy`, `proxy_url`, `ready`, `where` — no `key`. `/api/zernio/accounts` returns 2 accounts
(instagram, youtube) with no key, token or secret field.

## 14. Performance
`/app` answers in 0.03 / 0.04 / 0.04 s. The feature payload is 68 files totalling 708 500 bytes, and the
feat route sends `private, no-store` so an edit is always seen on reload. `plugins.js` sends `no-cache`
with an ETag, so a revalidation costs one 304.

## 15. Keyboard
Focus was checked by actually calling `focus()` and reading `:focus-visible`: a button in the view reports
`solid 2px rgb(255, 217, 188)` (the `--brand-line` ring `polish-focus.js` declares) and the sidebar's first
focusable reports the same. 66 `pcss_` sheets are injected, including `polish-focus`.

## 16. Mobile
25 feature files carry responsive rules, 14 of them a `max-width: 640px` step. `tests/test_a11y_pages.py`
passes with 202 buttons, 156 clickable, 85 inputs all labelled, 24 images all with alt, `html lang="en"`.

## 17. Copy
Zero em dashes, zero `TODO`, zero `FIXME`, zero `!!!` anywhere in `web/` (index.html, plugins.js and all
68 feature files).

## 18. Zernio
2 accounts, platforms `instagram` and `youtube`, no key echoed. `zernio.analytics()` calls
`GET /analytics` with `params={"postId": ...}` and maps views/likes/comments/shares out of the nested
`analytics` dict, with the older flat shapes as fallbacks.

## 19. Insights honesty
`/api/analytics/summary` notes "PeakCut's own records. Connect a YouTube channel for views, watch time and
click-through rate." `/api/analytics/videos` notes "PeakCut's own posts. Watch time and the rest come from
YouTube." with 0 rows. `/api/trends/{searches,videos,status}` each say no YouTube account is connected and
name what to do. No zeros posing as data.

## 20. Signoff
20 checks, 20 answered, 3 issues found during the whole session and all fixed with regression coverage
(`/api/sounds` HEAD 405, the Improve-round card printing the autopilot command, the `/app/usage` duplicate).
Two failures remain and both are environmental, proven by measurement rather than assumed: the CPU-quota
load meter and the missing `.git`.

## 21. Found in this audit and fixed
The sidebar's bottom **"Creators" heading was drawn even with nobody under it**, so a fresh install showed a
heading followed by a single "New creator" row, and the word "Creators" appeared twice (once as the new page
under Make, once as that empty heading). `web/index.html:1300` now wraps both the heading and the creator rows
in `S.creators.length ? … : ""`. Verified after a restart: the menu order is Make → Creators → Brand → Improve
→ Clip formats → Sounds → Live → Understand → Insights → Transcription → Set up → Tools → Connected apps →
Schedule → AI → Usage → Storage → Account → Help, with **zero dangling "Creators" headings**. Gates after the
change: `test_menu_pages.py` 349 ok, `test_feat_files.py` 68 files / 550 checks, `test_a11y_pages.py` 8 ok,
`test_overhaul.py` all passed, and `node --check` on the extracted index.html script is clean.

**SHIP.**
