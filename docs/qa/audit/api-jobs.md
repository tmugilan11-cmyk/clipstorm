# Audit: API jobs area — upload, job detail, review, render, peek, jobs list

Auditor: agent-147 (API area, QA swarm audit wave, 2026-11-22).

## Files / routes owned (read fully)

| Route | Where |
|---|---|
| `GET /api/jobs` (list) | `studio/server.py:826-828`, `studio/jobs.py:309-312` |
| `GET /api/jobs/{jid}` (detail + `log_tail`) | `studio/server.py:831-836`, helpers `_job_or_404` (`studio/server.py:673-677`), `_job_log_tail` / `_scrub` / `_log_roots` (`studio/server.py:685-736`) |
| `POST /api/upload` | `studio/server.py:890-929` (limit check `studio/server.py:908-915`, `VIDEO_TYPES` `studio/server.py:48`) |
| `GET /api/jobs/{jid}/review` | `studio/api_review.py:89-95` |
| `PATCH /api/jobs/{jid}/clips/{cid}` (review decide) | `studio/api_review.py:98-114` |
| `POST /api/jobs/{jid}/clips/{cid}/render` | `studio/server.py:1081-1094`, `studio/jobs.py:435-478` (`request_render`) |
| `POST /api/jobs/{jid}/peek` | `studio/api_preview.py:64-98` |
| `GET /api/jobs/{jid}/peek/{cid}` | `studio/api_preview.py:101-118` |

Also read as shared context: `studio/jobs.py` `public` (`studio/jobs.py:188-211`), `clean_options` (`studio/jobs.py:123-178`), `create` (`studio/jobs.py:372-397`).

Server: live install at `http://127.0.0.1:8798`, 6 real jobs (5 `done`, 1 `error`). No browser used (contract rule 2).

## Every check run (all with curl)

1. `GET /api/jobs` — 200, array of 6 jobs, shape checked against `jobs.public` (`id/kind/creator/created/source/options/status/stage/progress/title/uploader/duration/clips/error/ai/heard_to/watched_pct/blocks_done/blocks_total`).
2. `GET /api/jobs/{jid}` — 200 realistic (full job JSON). Invalid: short id `abc` → 404 `No such video`; well-formed unknown id → 404; path traversal `%2F%2Fetc` → 404 (regex `[\w\-]{8,60}` blocks it); unicode id → 404. `log_tail` present on the `error` job (32 lines), absent (`0` lines) on the clean job — shape never changes.
3. **Path-leak probe on `log_tail`** — grep for `C:/Users` in the served tail: 4 lines of Python stdlib traceback leaked (see finding B1).
4. `GET /api/jobs/{jid}/review` — 200 (`clips` + `remaining:1`); bad id → 404 `No such job.`
5. `PATCH /api/jobs/{jid}/clips/{cid}` — realistic `{"review":"approved"}` → 200, clip echoed, `remaining:0`; `{"review":"maybe"}` → 400 `Choose approved or rejected.`; empty body → 400 same; bad clip id → 404 `No such clip in this job.`
6. `POST /api/jobs/{jid}/clips/{cid}/render` — realistic `{}` → 200 (re-queues the clip; hook/title preserved); while queued → 409 `This clip is still being made...`; `{"start":10,"end":2}` → 400 `A clip can be 3 to 180 seconds long.`; `{"start":0,"end":999}` → 400 same; **`{"start":"abc"}` → 400 `could not convert string to float: 'abc'`**; **`{"start":null}` → 400 `float() argument must be a string or a real number, not 'NoneType'`** (finding B2); bad clip id → 404; bad job id → 404.
7. `POST /api/jobs/{jid}/peek` — realistic `?cid=clip01` → 200 `{"ok":true,"frames":[{"id":"clip01","peek":"clip01_peek.jpg","peek_at":[1.0,3.67,7.33,10.0],"peek_version":1}]}`; bad cid → 404; job with no clips → 400 `There are no clips to look at yet.`
8. `GET /api/jobs/{jid}/peek/{cid}` — 200, real `image/jpeg`, 18 339 bytes; bad cid → 404; bad job → 404.
9. `POST /api/upload` — no file → 422 Field required; `.txt` file → 400 `Upload a video file (mp4, mov, mkv or webm).`; valid name + `creator=ghost` → 404 `No such creator`; realistic upload of a tiny ffmpeg-made mp4 → 200, job created and shape-checked; job then deleted via `DELETE /api/jobs/{jid}` (200) to restore the list; local test files removed.
10. Malformed `options` form field (`options=not json`) — code path `studio/server.py:900-904` silently falls back to `{}` (finding B5, verified by reading, not curled to avoid creating another job).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `studio/server.py:707-712` (`_scrub`), served by `GET /api/jobs/{jid}` `log_tail` | Job logs leak personal filesystem paths: Python stdlib traceback frames reach the page with the Windows username and interpreter path intact. `_scrub` only replaces `DATA_DIR`/`ROOT`/temp-dir forms, so anything under `sys.prefix` passes verbatim — defeating the file's own rule (`studio/server.py:704`: a traceback names the folder the app runs in, "that is nobody's business but ours"). | Curl of the real error job returned e.g. `File "C:\Users\Asus\AppData\Local\Programs\Python\Python315\Lib\concurrent\futures\_base.py", line 454, in result` (4 such lines, lines 6/9/11/13 of the tail). | In `_log_roots()` also add the interpreter's own folders in both spellings: `sys.prefix`, `sys.exec_prefix`, `Path(sys.executable).parent`, and the stdlib dir (`Path(sys.executable).parent / "Lib"`), longest first like the existing roots. Stdlib frames then scrub to bare file names like repo frames already do. |
| important | `studio/server.py:1090-1093` + `studio/jobs.py:441-443` | The render route surfaces raw Python exception text to the page when a clip time is not a number: `could not convert string to float: 'abc'` and `float() argument must be a string or a real number, not 'NoneType'`. A beginner cannot act on either message; every other bad-input answer on these routes is plain language. | Curl: `POST /api/jobs/{jid}/clips/clip01/render` `{"start":"abc"}` → 400 `{"detail":"could not convert string to float: 'abc'"}`; `{"start":null}` → 400 `{"detail":"float() argument must be a string or a real number, not 'NoneType'"}`. Route only catches `ValueError/TypeError` and passes `str(e)` through (`studio/server.py:1092-1093`). | Wrap the time conversion in `request_render` (`studio/jobs.py:441-443`) in its own try that raises `ValueError("Times must be numbers, like 12.5.")`; the route already turns that into a 400. Keep `A clip can be 3 to 180 seconds long.` for the range check. |
| minor | `studio/server.py:897` and `studio/server.py:978` | Upload rejection copy names 4 of the 7 allowed types: `Upload a video file (mp4, mov, mkv or webm).` while `VIDEO_TYPES` (`studio/server.py:48`) also accepts `.m4v`, `.ts`, `.flv`. A person holding one of those, who first tried a rejected file, is told an incomplete list. | Line comparison `studio/server.py:48` vs `studio/server.py:897/978`; curl of a `.txt` upload returned the same sentence. | Say the whole list: `Upload a video file (mp4, mov, m4v, mkv, webm, ts or flv).` Both lines (simple upload and chunked start). |
| minor | `studio/server.py:676` vs `studio/api_review.py:47`, `studio/api_preview.py:70,75` | The same missing job gets two different 404 sentences: `No such video` on `/api/jobs/{jid}` but `No such job.` on `/api/jobs/{jid}/review` and `/api/jobs/{jid}/peek`. Two names for one thing in errors a person (or the page) may show side by side. | Curl: `GET /api/jobs/abc` → `No such video`; `GET /api/jobs/abc/review` → `No such job.`; `GET /api/jobs/abc/peek/clip01` → `No such job.` | Pick one word across all job routes (`No such video.` matches the page's own vocabulary) in `_job_or_404` in `server.py`, `api_review.py`, and `api_preview.py`. |
| minor | `studio/server.py:900-904` | `POST /api/upload` silently swallows a malformed `options` form field (`json.loads` fails → `{}`). A page bug that sends broken options would make every upload quietly run with defaults, and nobody would ever see why. | Code path read at `studio/server.py:900-904`; the chunked start route validates instead (`studio/server.py:989-993`), so the two upload paths disagree. | Log the ignored payload (`print(f"upload options ignored: {options[:200]}")`), or better, reject with 400 like `/api/upload/start` does, so both upload paths agree. |

### Side effects made while auditing (declared, not findings)

- Approved `clip01` of job `20261122-122201-798840cfbf` via PATCH (review `null` → `approved`); the API offers no way back to undecided, so it stays approved.
- Re-rendered the same clip once (no changes; hook `WAIT FOR IT` and title preserved; completed back to `done`).
- Created job `20261122-131124-1052ddc712` with a 2-second test upload, then deleted it; job list back to the original 6.

## What checked out clean

- Every route in the area answers; no 500s on any realistic or invalid input (30+ calls).
- `jobs.public` never leaks server paths or owner id (`studio/jobs.py:185-194`); `log_tail` is text-only and omitted when empty (`studio/server.py:835`).
- Ownership: `jobs.get` returns the job only to its owner (`studio/jobs.py:315-318`); peek/review re-check via `_uid`.
- Upload limits enforced mid-stream with the temp file cleaned up in `finally` (`studio/server.py:908-926`); bad creator and bad extension rejected before anything is written.
- Good error copy elsewhere: `A clip can be 3 to 180 seconds long.`, `This clip is still being made. Try again when it has finished.`, `There are no clips to look at yet.`, `Choose approved or rejected.`, and the transcription failure message names the fix (Settings, Transcription).
- `remaining` on review and `peek_at`/`peek_version` on peek give the page everything it needs for loading/empty states.
