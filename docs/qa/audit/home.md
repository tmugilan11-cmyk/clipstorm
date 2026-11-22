# Audit — `/app` shell: `web/index.html` + `web/plugins.js`

Auditor: agent-127 (40-agent QA swarm). Date: 2026-11-22.
Server: http://127.0.0.1:8798. Repo: current directory. Rule set: docs/qa/CONTRACT.md.
No browser used (lead owns the browser): all checks ran with ops_grep / ops_glob / ops_inspect_local_file, python (contrast + raw-byte repr) and curl.

## Pages / files owned

| Owned | What it is |
|---|---|
| PAGE `/app` | the signed-in app shell (server route `@app.get("/app")` + `/app/{rest:path}` SPA fallback, studio/server.py:437-438) |
| `web/index.html` (3504 lines) | the whole signed-in app: :root tokens, `.side` nav, topbar, `#view` switch, all page draw functions |
| `web/plugins.js` (282 lines) | the feature-file loader: `PeakCut.add/page`, css injection, act routing, paint hooks, key handling, boot |

## Every check run

1. Read `docs/qa/CONTRACT.md`; loaded skills `frontend-design` + `systematic-debugging`.
2. Read `web/index.html` fully (5 chunks) and `web/plugins.js` fully.
3. curl status codes (all must be 200):

| Code | Path |
|---|---|
| 200 | `/app` |
| 200 | `/app/settings` |
| 200 | `/app/videos` |
| 200 | `/app/review` |
| 200 | `/app/ai-usage` |
| 200 | `/app/analytics/` (trailing slash) |
| 200 | `/app/creators/x` |
| 200 | `/app/bogus-deep-link` |
| 303 | `/login` (redirects when sign-in is off — correct) |
| 200 | `/assets/plugins.js` |
| 200 | `/assets/feat` (feature-list JSON) |

4. WCAG contrast computed in python for 14 colour pairs (relative luminance, (L1+0.05)/(L2+0.05); normal text 4.5, big text 3.0).
5. Raw-byte check (python repr) of every line where the file reader's doubled-backslash display had produced a suspected regex bug.
6. greps: `pcDone` (index.html: 0 matches), static DOM ids (`#clipdlg` :915, `#formdlg` :916, `#file` :917 all exist), `--bad-soft`/`--good-soft` tokens (exist, :21), chart colours (:443-445).
7. Feature-page registrations grepped across all 76 files in `web/feat/` (both `window.PeakCut.page(` and local-alias `P.page(` / `P.add(` forms).
8. Every `/api/*` URL called from the shell cross-checked against `@app.…`/`@router.…` decorators in `studio/*.py` (101 routes in server.py + 92 in api_* modules). All exist. Highlights: `/api/settings` GET/PUT (:1611/:1616), `/api/notifications` + `/read` (:1261/:1267), `/api/upload` + `/start` + PUT `/{upid}/{n}` + `/finish` + DELETE (:890/:969/:1013/:1037/:1074), `/api/sync` (:814), `/api/status` (:647), `/api/overview` (:1606), `/api/clips.zip` (:1134), `/api/bulk/delete` (:1126), `/api/creators/...` (:1148-1373), `/api/live/{jid}/stop|clip` (:1373/:1382), `/api/auth/logout|password|resend-verification` (:597/:610/:538), `/api/account/delete` (:1160), `/api/translate/langs` (api_text.py:112), `/api/style/preview` (api_style.py:218), `/api/schedule/preview` (api_preview.py:174), `/api/channel-preview` (:1283), `/api/alerts/test` (:1831), `/assets/feat` listing (server.py:469-474).

## Suspected and cleared (retracted)

- **Trailing-slash regex bug** (`plugins.js:66`, `index.html:1430/:1450`): the file reader doubles backslashes in its display; python repr confirms the file really contains `/\/$/` — a correct trailing-`/` strip. `curl /app/analytics/` returns 200. Not a bug.
- Same reader artefact cleared: `VIDEO_EXT = /\.(mp4|mov|mkv|webm|m4v|ts|flv)$/i` (`index.html:1645`), `fmtK` `/\.0$/` (`:1174`), storage placeholder renders `D:\PeakCut` (`:2607`).
- **Missing pages**: every `go()`/`openaudio`/`pcpage` target is registered — `schedule` (web/feat/schedule.js:293), `analytics` (:210), `audio-edit` (audio-edit.js:715), `ai-usage` (usage.js:274), `audio` (audio-page.js:532), `creators` (creators.js:256), `formats` (formats.js:469), `help` (help.js:124), `improve` (learn.js:354), `live` (live.js:302), `pictures` (pictures.js:540), `sounds` (sounds.js:347), `streamer` (streamer-mode.js:592), plus brand/transcribe/tools/apps/ai/storage/account (menu-pages.js:130-234).
- `--faint #7C7C7C` on `--bg #0A0A0A` = **4.74:1** — passes 4.5.
- `.btn.primary:disabled` 1.94:1 — disabled controls exempt from WCAG.
- `loadFiles` fetches `/assets/feat`, a real JSON listing endpoint (server.py:469-474) — not a 404 path.
- `pcDone` is never set by index.html (see minor finding) but no double-fire exists today because plugin act names are unique.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| critical | web/index.html:803 | `.step:hover` turns near-white under light text — the home "Next steps" buttons and Settings steps become unreadable at the exact moment of hovering | `.step:hover{background:#F1EBE6}`; `.step` text is `var(--text)` #F5F5F5 (`.step b` :532) → **1.08:1** (needs 4.5; big-text 3.0 also fails) | hover must change colour within the dark palette: `background:var(--muted)` (#111) or `var(--field)` |
| critical | web/index.html:809 | every table row hover paints near-white under light text (creators table, post queue, library) | `tr:hover>td{background:#FCFAF8}`; td text inherits #F5F5F5 → **1.05:1** while hovered | same: `background:var(--muted)` |
| critical | web/index.html:90 | banner bold text is dark-on-dark in every vbanner (update, ffmpeg missing, AI not ready, disk, verify-email) | `.vb b{color:#5A2C06}` on `.vb{background:var(--brand-soft)}` #2A1B10 (:87) → **1.42:1**; `drawShell` wraps `<b>` inside `.vb` in all five banners (index.html:1392-1398) | `.vb b{color:var(--brand-deep)}` (#FFB27A) or the banner body colour #FFD9BC (12.59:1) |
| critical | web/index.html:445 | the "Posted" chart series and its legend swatch are invisible on the dark card | `.chart .b2{fill:var(--brand-ink)}` → #160D05 on card #111111 = **1.02:1**; legend `<i style="background:var(--brand-ink)">` (:2125) matches | give b2 a visible second colour on the dark palette (e.g. `var(--brand-deep)`) and mirror it in the legend swatch |
| critical | web/index.html:570 | the "making" clip-rendering state text is unreadable for the whole render (light shimmer kept from the former white theme) | `.making{color:var(--dim)}` #A3A3A3 on gradient #F4EFEE/#FBF8F7 → **2.21:1 / 2.39:1** (<3), 13px 500; used at :1870 | put the state on a dark chip: `background:var(--muted); color:var(--dim)` (7.85:1), or light ink on the shimmer |
| critical | web/index.html:794 | danger-button hover (the moment before clicking Delete/Sign out) is unreadable | `.btn.danger:hover{background:#FADDE0}` with text `var(--bad)` #F87171 (:209) → **2.17:1** | hover bg on the dark palette, e.g. `#3A1A1E`, keeping #F87171 text |
| important | web/index.html:743 | "Sign out" pop-menu item below AA for normal text | `.pop.menu .danger{color:#C53030}` on `--bg` #0A0A0A = **3.62:1** at 14px normal (needs 4.5); item drawn by openAcct :1262 | `color:var(--bad)` (#F87171 ≈ 8:1 on #0A0A0A) |
| important | web/index.html:2082 | home page dies silently when `/api/overview` fails — no loading, empty, error or retry state; `#ov` just stays blank | `loadOverview` body ends `catch { return; }` | catch → draw an error box with a Retry button (the pattern `loadReview` already uses) |
| important | web/index.html:685-686 | toasts clip ~10px off-screen on a 390px phone viewport | `#toasts{right:20px}` + `.toast{max-width:380px}` → left edge at 390−20−380 = **−10px** | `max-width:min(380px, calc(100vw - 40px))` |
| important | web/index.html:1398 | dead view-name guard: the "AI not ready" banner still shows on the AI usage page itself | guard compares `S.view !== "usage"`, but the page id is `ai-usage` (web/feat/usage.js:274-278) and `go()` sets `S.view = v` (:1463), so the comparison never matches | compare against `"ai-usage"` |
| minor | web/index.html:331 | skeleton/wait shimmer is a light block on the dark app (no text, visual-only) | `.sk`/`.lp.wait .th` use the light gradient #F4EFEE/#FBF8F7 | tint to the dark palette (e.g. #1E1E1E → #2A2A2A) |
| minor | web/index.html:3405 | the bell list is fetched and redrawn twice per "mark read" | `await markRead(); return openBell().then(openBell);` | `await openBell()` once — `render()` already repaints after markRead |
| minor | web/plugins.js:153 | one-sided `pcDone` handshake: wireActs skips elements marked `dataset.pcDone === "1"` ("already handled by index.html") but index.html never sets it (0 matches in web/index.html) | latent double-fire if a plugin act ever shares a name with an index.html act (none today — plugin act names are unique) | either mark `pcDone` in index.html's act switch or delete the check and its comment |

## Usability findings

| Where | What | Fix |
|---|---|---|
| web/index.html:1018 | `ask()` always sets `autofocus` on the confirm button — even for destructive dialogs (delete creator/clip/job, sign out), so a reflex **Enter confirms the destructive action** | autofocus the Cancel button when `danger` is true |
| web/index.html:1309 | when the server has no feedback link, the error toast says "Copy this message and open an issue on GitHub." but nothing is copied — the working branch (:1310) copies automatically, this one makes the user hand-copy unselectable toast text | run `navigator.clipboard.writeText(context)` before the toast, then say "Copied. Open an issue on GitHub." |
| web/index.html:3022-3024 | drag/drop handlers only preventDefault when a `.composer` exists — dropping a video on Settings/Review/Analytics **navigates the browser to the dropped file**, losing the page | `window.addEventListener("dragover"/"drop", e => e.preventDefault())` globally, keep the composer branch for acceptance |
| web/index.html:289,298 | composer removes `:focus-visible` outlines and chips only signal focus with a subtle background change — keyboard focus is easy to lose on the primary flow | keep a 2px `var(--brand)` outline on chips/inputs inside the composer |

## What passed

- All 11 curl checks (table above) — every owned page shell is 200; `/login` 303 is the documented signed-out redirect.
- All `/api/*` calls from the shell exist server-side (101 + 92 routes checked).
- Static DOM ids used by boot code all exist (`#clipdlg`, `#formdlg`, `#file`).
- `--bad-soft`/`--good-soft` tokens exist, so the error/ok clip states are valid (:21, :1870, :255-256).
- `--faint` passes AA (4.74:1); `--dim` on bg 7.85:1; body text 17.32:1 on cards.
- Feature-page registry complete; `PeakCut.drawPage` has a load-error toast + console.warn path (plugins.js:124-141).
- Loader/injection: plugins.js dedupes styles, escapes nav labels with `esc()`, `wireKeys` skips form fields, `wireActs` has try/catch per handler, `loadFiles` failures resolve silently without breaking boot.
- prefers-reduced-motion handled (:871); responsive drawer ≤900px, tiles 2-col ≤1100px, grid 2-col ≤640px.
