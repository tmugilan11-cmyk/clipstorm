# QA audit — Review page (`/app/review`) + `web/feat/history.js`

Auditor: agent-129 (review slug). Binding rule set: `docs/qa/CONTRACT.md`.

## Pages / files owned

- Page: `/app/review` (Review view drawn by `web/index.html` review views)
- Files: `web/index.html` (review views + `rvCard`/`rvList`), `web/feat/history.js` (version chips in the clip dialog)

## Checks run

1. **Page shell**: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/review` → **200**.
2. **Assets on the shell**: `/assets/plugins.js` → **200**, `/assets/feat/history.js` → **200** (feat files load via script injection, `web/plugins.js:248`).
3. **Routes verified in `studio/`** (every route the review view and history.js use):
   - `GET /api/jobs` — `studio/server.py:826`
   - `GET /api/jobs/{jid}/review` — `studio/api_review.py:89`
   - `PATCH /api/jobs/{jid}/clips/{cid}` — `studio/api_review.py:98`
   - `GET /api/jobs/{jid}/clips/{cid}/history` — `studio/api_history.py:179`
   - `PATCH /api/jobs/{jid}/clips/{cid}/history` — `studio/api_history.py:187`
   - `GET /media/{jid}/{name}` — `studio/server.py:1176`
   All exist. No 404/500 route found.
4. **Handlers traced (broken-control check)**: `rvapprove`/`rvreject` → `web/index.html:3443`, `rvskip` → `:3444`, `histkeep` → `:3264`, `pchistkeep` → `web/feat/history.js:243` dispatched by `web/plugins.js:150-168` (`wireActs`). All alive; errors surface as toasts via the try/catch at `web/index.html:3462`.
5. **Keyboard guards**: `rvKeys` (`web/index.html:2223-2232`) excludes INPUT/TEXTAREA/SELECT/contentEditable targets and modifier keys; keys a/x/s only act on the Review view (`:1622`).
6. **Contrast computed** (WCAG 2.2 `(L1+0.05)/(L2+0.05)`, palette at `web/index.html:13-21`):
   - `.pill` default: `#A3A3A3` on `#111111` → **8.4:1** (pass)
   - `.btn.danger`: `#F87171` on `#2B1416` → **6.25:1** (pass)
   - `.btn.primary`: `#160D05` on `#FF8B33` → **8.2:1** (pass)
   - `.rv-job` (12px label): `#A3A3A3` on `#0A0A0A` → **8.8:1** (pass)
   - `.set-load` error text: `--faint` → **6.7:1** as overridden by `web/feat/polish-contrast.js` (`#A0948C`, its header says 7.24 on `--bg`); **4.74:1** with the base `--faint #7C7C7C` — both pass.
   No contrast failures found on this page.
7. **390px viewport**: sidebar stacks to one column at ≤900px (`web/index.html:819`), card padding drops to 16px at ≤640px (`:882`), `.rv-top` and `.row` wrap (`:274`, `:184`), `.rv-body` has `min-width:0` (`:273`). Thumbnail is 88px wide. No element wider than the viewport; no clipping found.
8. **Escape audit**: every server-originated string into markup passes `esc()` — `web/feat/history.js:46-47` applied at `:127-129`; `web/index.html:2169-2174`. `data-v` is a `Number.isFinite`-checked number (`history.js:113`, `:127`). No console-risky markup path found.
9. **States**: loading (`web/index.html:2151`), empty for no clips (`:2191`), empty for all-decided (`:2197`), error (`:2190`) all present.
10. **Full reads**: `web/feat/history.js` (246 lines, complete), `web/index.html` review views (`:1341-1404`, `:1475`, `:1600-1630`, `:2143-2232`, `:2928-3011`, `:3415-3463`), `studio/api_review.py` (complete), `studio/api_history.py` (history payload + PATCH), `studio/jobs.py` (clip order).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `web/feat/history.js:102-106`, `:148`, `:153-171` + `web/index.html:2949` | Two "Versions" sections show at once in the clip dialog. The plugin's `takeSlot()` only hides the page's own strip when called with `mine` truthy, but its **sole call site passes `false`** and the `paint()` success path never calls it at all — so `#dlgvers` is never hidden while the plugin chips show. `drawHist()` then un-hides `#dlgvers` and writes its own pill strip, and the plugin appends its chip block right after it. | `history.js:102-106` (`if (mine) slot.hidden = true;` with sole call `takeSlot(box, false)` at `:148`); `history.js:153-171` (success path, no `takeSlot`); `web/index.html:2949` (`box.hidden = false` + pill buttons); `web/plugins.js:191` (`watch("#clipdlg","drawClipDlg")` fires the hook). Reachable on any clip with ≥2 versions: both `loadHist()` (page) and the plugin's `load()` fetch the same endpoint, so both strips get data. Two sets of pin controls with different wording ("Click one to pin it as the keeper" vs "Press one to keep it") — exactly the duplication the file's own header (`history.js:98-101`) claims to prevent. Side note: the history endpoint is fetched twice per dialog open. | In `paint()`'s success path, call `takeSlot(box, true)` once the block is inserted; make `takeSlot(box, false)` restore the slot (`slot.hidden = false`) so the stand-down handback is real. This also makes the double-fetch harmless (one strip wins the slot). |
| important | `web/index.html:2979-2996`, `:2972-2978`, `:2149-2161` | A clip that finishes while you sit on the Review page never appears in the list. `tick()` refreshes `S.jobs` and calls `render()`, which calls `drawReview()` — the clip list, the picker's selected job and the "X of Y decided" pill all come from stale `S.rv`, which only `loadReview()` ever refetches (view switch or `rv_job` change). | `web/index.html:2975` (`render()` → `drawReview()` only); `S.rv` is assigned solely at `:2155`/`:2158`/`:2160` inside `loadReview()`; `tick()` at `:2988-2996` updates `S.jobs` then calls `render()`. Nothing in the sync path refetches `/api/jobs/{S.rvJid}/review`. | In `tick()`, when `fresh && S.view === "review"`, call `loadReview()` (or refetch `S.rv` for `S.rvJid`) before `render()`. |
| important | `web/index.html:2190` + `:480` | The error state is a raw message in a loading-styled div with no way to retry. On a first visit where `/api/jobs` fails, the picker is empty too, so the whole page is one faint grey error string (e.g. "Failed to fetch") and nothing else — a beginner has no next step. | `web/index.html:2190` (`put(root, picker + '<div class="set-load">' + esc(S.rv.error) + '</div>')`); `.set-load` at `:480` is the loading style (`padding:40px 0;color:var(--faint)`); `picker = ""` when `S.jobs` is empty (`:2153-2155`), which is exactly the failed-fetch case. | Humanize the copy ("Could not load clips — check that the server is running.") and add a "Try again" button wired to `loadReview()`. |
| minor | `web/index.html:2165` + `studio/api_review.py:74-79` | "0:00" is shown as the clip's length when the server could not read its times — a zero that claims the clip is 0 seconds long. `_clip_len()` returns `0.0` on unreadable times, contradicting its own docstring ("simply shows no length"), and `rvCard` renders the duration span unconditionally. | `web/index.html:2165` (`const dur = fmt(c.duration != null ? …)` rendered unconditionally at `:2174`); `studio/api_review.py:77-79` (`return 0.0` in the except branch) and `:85` (`duration` always present in `_review_line`). | In `rvCard`, omit the duration span when `!c.duration`. The root cause (api_review.py returning `0.0` instead of `None`) belongs to another agent's file — flagging it here as evidence. |
| minor | `web/feat/history.js:32`, `:127-129` | Struck-through "gone" chips — a version that is no longer on disk — are still clickable and pin a file that no longer exists; the success toast ("Pinned version N") never mentions it. | `history.js:32` (`.pchist .pchip.gone{opacity:.6;text-decoration:line-through}` — visual language of "unavailable"); `history.js:127-129` (gone chips rendered without `disabled`); `studio/api_history.py:203-206` (PATCH accepts any remembered version number, including ones with `exists:false`). | In `block()`, render chips with `v.exists === false` as `disabled` — the tooltip already says "no longer on disk". |
| minor | `web/index.html:2143` | The review code sits under a section comment that says "AI usage". | `web/index.html:2143` (`/* ============================================================ AI usage */` directly above `rvList()` at `:2144`). | Rename the comment to "review queue". |

## Usability findings

| where | what | fix |
|---|---|---|
| `web/index.html:2215-2218` + `:2178` | The Skip button on a card does not skip *that* card — `rvSkip()` advances from the page cursor (first undecided clip), so pressing Skip on the last card acts on a different clip and scrolls somewhere unexpected. Same family: pressing A/X while a different card's button has focus approves/rejects the cursor clip, not the focused one. | Make the card's Skip call `rvAdvanceFrom(c.id)` with its own cid (the data attribute is already on the button); keep the S key as the global "skip ahead". |
| `web/index.html:2187` + `studio/jobs.py:1085-1098`, `studio/api_review.py:94` | The help line "Clips waiting for a yes or no, newest first." sits under the "Pick a video" heading but reads as describing the clip list below — which is oldest-first (clips are appended as clip01, clip02… and the review endpoint preserves that order). A beginner scanning for the newest take starts at the wrong end. | Reword to "Videos with finished clips, newest first." and let the Clips section state its own order ("oldest takes first"). |
| `web/index.html:2176-2178` | The A/X/S keyboard shortcuts are documented only in the section help paragraph; the Approve/Reject/Skip buttons themselves carry no hint, so the shortcut is invisible at the point of use. | Add a small key hint to each button, e.g. a `<span class="hint">A</span>` inside the button or `title="Shortcut: A"` — one-line change, no server work. |
| `web/index.html:1345` | The Review nav row shows no count of clips waiting for a decision (the All videos row shows a count badge, `:1343-1344`), so there is no way to see review work waiting from any other page. | Show an undecided-clip badge on the nav row. The data needs a small server-side aggregate: per-job `remaining` exists on `/api/jobs/{jid}/review` (`studio/api_review.py:95`), but nothing global ships in `/api/status` or `/api/sync` today. |

## Verdict

No broken controls, no 404/500, no contrast failures, no 390px overflow on this page. The two important bugs are the duplicate Versions strips in the clip dialog (the plugin's slot-handoff contract is dead code) and the stale review list when a clip finishes while the page is open.
