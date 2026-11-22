# QA findings — 40-auditor swarm, triaged by file

Source: `docs/qa/audit/*.md` (39 returned of 40; the `x-overflow` auditor failed and has no report — its area is covered by the mobile and contrast audits).
Method: every finding carries evidence — a file line, a measured WCAG ratio, an HTTP code. Severity: critical = unreadable or broken; important = below AA or a wrong message; minor = polish.
Totals: **245 bugs** (28 critical, 79 important, 138 minor) and **56 usability findings**, across **59 files**.

## Per-auditor counts

| Auditor | Bugs | Usability |
|---|---|---|
| account-storage-help | 0 | 0 |
| api-analytics | 10 | 4 |
| api-audio | 0 | 0 |
| api-formats-schedule | 9 | 0 |
| api-igcaption | 4 | 0 |
| api-jobs | 5 | 0 |
| api-learn | 9 | 4 |
| api-overlays | 5 | 0 |
| api-posting | 3 | 0 |
| api-style | 5 | 0 |
| api-transcribe-ai | 4 | 0 |
| apps-ai-usage | 12 | 0 |
| audio-editor | 6 | 4 |
| audio-library | 18 | 0 |
| clip-dialog | 7 | 0 |
| creators | 6 | 0 |
| formats | 8 | 6 |
| home | 13 | 4 |
| improve | 0 | 2 |
| insights-audience | 0 | 3 |
| insights-content | 5 | 3 |
| insights-frame | 0 | 5 |
| insights-trends | 0 | 0 |
| pictures-editor | 11 | 0 |
| review | 6 | 5 |
| sounds | 3 | 3 |
| streamer-live | 5 | 2 |
| tools-schedule | 9 | 6 |
| transcribe-brand | 4 | 1 |
| videos | 8 | 2 |
| x-a11y | 0 | 0 |
| x-console-risks | 3 | 0 |
| x-contrast | 24 | 0 |
| x-copy | 17 | 0 |
| x-dead-handlers | 2 | 2 |
| x-leftovers | 0 | 0 |
| x-mobile | 18 | 0 |
| x-routes-live | 2 | 0 |
| x-states | 4 | 0 |

## Fix wave — one agent per file

Files in fix order (worst first). The lead owns `web/index.html`; agents own everything else. Every agent reads `docs/qa/CONTRACT.md` and this file's own section, runs `node --check`, and proves its fixes against the audit evidence.

| File | Critical | Important | Minor | Usability |
|---|---|---|---|---|
| web/index.html | 12 | 16 | 33 | 13 |
| web/feat/pill.js | 5 | 0 | 1 | 0 |
| web/feat/day.js | 3 | 0 | 0 | 0 |
| web/feat/audio-page.js | 2 | 9 | 13 | 0 |
| web/feat/autopilot.js | 2 | 0 | 2 | 0 |
| web/feat/audio-edit.js | 1 | 4 | 4 | 4 |
| studio/api_overlay.py | 1 | 1 | 2 | 0 |
| web/feat/grid.js | 1 | 0 | 2 | 0 |
| web/feat/polish-errors.js | 1 | 0 | 0 | 0 |
| studio/server.py | 0 | 4 | 4 | 0 |
| web/feat/usage.js | 0 | 2 | 6 | 0 |
| web/feat/formats.js | 0 | 3 | 5 | 0 |
| web/feat/pictures.js | 0 | 3 | 5 | 0 |
| web/feat/streamer-mode.js | 0 | 5 | 3 | 0 |
| studio/api_analytics.py | 0 | 7 | 0 | 0 |
| web/feat/creators.js | 0 | 1 | 5 | 0 |
| web/feat/menu-pages.js | 0 | 2 | 3 | 0 |
| studio/api_preview.py | 0 | 3 | 1 | 0 |
| web/feat/analytics-table.js | 0 | 2 | 2 | 0 |
| web/feat/sounds.js | 0 | 3 | 1 | 2 |
| web/feat/history.js | 0 | 1 | 2 | 0 |
| studio/api_sound.py | 0 | 2 | 0 | 0 |
| studio/api_learnreport.py | 0 | 2 | 0 | 1 |
| studio/api_hooks.py | 0 | 1 | 1 | 0 |
| studio/ai.py | 0 | 1 | 1 | 0 |
| studio/schedule_ai.py | 0 | 1 | 0 | 0 |
| web/feat/learn-arrows.js | 0 | 1 | 0 | 0 |
| studio/zernio.py | 0 | 1 | 0 | 0 |
| web/feat/meme-timeline.js | 0 | 1 | 0 | 1 |
| web/feat/schedule.js | 0 | 1 | 0 | 3 |
| web/feat/analytics-audience.js | 0 | 1 | 0 | 1 |
| web/feat/polish-focus.js | 0 | 1 | 0 | 0 |
| studio/api_style.py | 0 | 0 | 5 | 0 |
| studio/api_trends.py | 0 | 0 | 3 | 0 |
| studio/api_learn.py | 0 | 0 | 3 | 0 |
| web/feat/pictures-dialog.js | 0 | 0 | 3 | 0 |
| web/feat/filters.js | 0 | 0 | 3 | 0 |
| web/feat/mood.js | 0 | 0 | 2 | 0 |
| web/feat/igcaption.js | 0 | 0 | 2 | 0 |
| studio/api_igcaption.py | 0 | 0 | 2 | 0 |
| web/feat/style-tiles.js | 0 | 0 | 2 | 0 |
| web/feat/learn-arms.js | 0 | 0 | 2 | 0 |
| web/feat/analytics-trends.js | 0 | 0 | 2 | 1 |
| web/ascii.js | 0 | 0 | 1 | 0 |
| studio/ai_arms.py | 0 | 0 | 1 | 0 |
| studio/overlay.py | 0 | 0 | 1 | 0 |
| (other) | 0 | 0 | 1 | 27 |
| web/feat/stats.js | 0 | 0 | 1 | 0 |
| web/plugins.js | 0 | 0 | 1 | 0 |
| web/feat/analytics-compare.js | 0 | 0 | 1 | 0 |
| web/feat/polish-contrast.js | 0 | 0 | 1 | 0 |
| web/feat/icons-extra.js | 0 | 0 | 1 | 0 |
| web/feat/polish-empty.js | 0 | 0 | 1 | 0 |
| web/feat/polish-keyboard.js | 0 | 0 | 1 | 0 |
| web/feat/peek.js | 0 | 0 | 1 | 0 |
| web/feat/clean-forecast.js | 0 | 0 | 1 | 0 |
| web/feat/analytics-retention.js | 0 | 0 | 0 | 1 |
| studio/api_posttime.py | 0 | 0 | 0 | 1 |
| studio/api_brandai.py | 0 | 0 | 0 | 1 |

## web/index.html

- **[critical]** web/index.html:803 — `.step:hover` turns near-white under light text — the home "Next steps" buttons and Settings steps become unreadable at the exact moment of hovering
  - Evidence: `.step:hover{background:#F1EBE6}`; `.step` text is `var(--text)` #F5F5F5 (`.step b` :532) → **1.08:1** (needs 4.5; big-text 3.0 also fails)
  - Fix: hover must change colour within the dark palette: `background:var(--muted)` (#111) or `var(--field)`
  - (audit: home)
- **[critical]** web/index.html:809 — every table row hover paints near-white under light text (creators table, post queue, library)
  - Evidence: `tr:hover>td{background:#FCFAF8}`; td text inherits #F5F5F5 → **1.05:1** while hovered
  - Fix: same: `background:var(--muted)`
  - (audit: home)
- **[critical]** web/index.html:90 — banner bold text is dark-on-dark in every vbanner (update, ffmpeg missing, AI not ready, disk, verify-email)
  - Evidence: `.vb b{color:#5A2C06}` on `.vb{background:var(--brand-soft)}` #2A1B10 (:87) → **1.42:1**; `drawShell` wraps `<b>` inside `.vb` in all five banners (index.html:1392-1398)
  - Fix: `.vb b{color:var(--brand-deep)}` (#FFB27A) or the banner body colour #FFD9BC (12.59:1)
  - (audit: home)
- **[critical]** web/index.html:445 — the "Posted" chart series and its legend swatch are invisible on the dark card
  - Evidence: `.chart .b2{fill:var(--brand-ink)}` → #160D05 on card #111111 = **1.02:1**; legend `<i style="background:var(--brand-ink)">` (:2125) matches
  - Fix: give b2 a visible second colour on the dark palette (e.g. `var(--brand-deep)`) and mirror it in the legend swatch
  - (audit: home)
- **[critical]** web/index.html:570 — the "making" clip-rendering state text is unreadable for the whole render (light shimmer kept from the former white theme)
  - Evidence: `.making{color:var(--dim)}` #A3A3A3 on gradient #F4EFEE/#FBF8F7 → **2.21:1 / 2.39:1** (<3), 13px 500; used at :1870
  - Fix: put the state on a dark chip: `background:var(--muted); color:var(--dim)` (7.85:1), or light ink on the shimmer
  - (audit: home)
- **[critical]** web/index.html:794 — danger-button hover (the moment before clicking Delete/Sign out) is unreadable
  - Evidence: `.btn.danger:hover{background:#FADDE0}` with text `var(--bad)` #F87171 (:209) → **2.17:1**
  - Fix: hover bg on the dark palette, e.g. `#3A1A1E`, keeping #F87171 text
  - (audit: home)
- **[critical]** `web/index.html:445` + `:2125` — The overview Activity chart's "Posted" bar series and its legend swatch are near-black on the near-black card: the whole second series is invisible
  - Evidence: `.chart .b2{fill:var(--brand-ink)}` `#160D05` on card bg `--bg #0A0A0A` (`.card{background:var(--bg)}` `:238`) = 1.03:1; bars drawn at `:2094`, legend `<i style="background:var(--brand-ink)">Posted</i>` at `:2125`
  - Fix: Fill `.b2` with a visible second colour (e.g. `--brand-deep #FFB27A` → 8.9:1, or `--dim #A3A3A3` → 6.7:1) and match the legend swatch
  - (audit: videos)
- **[critical]** web/index.html:90 (`.vb b`) + markup 1392–1398 — The bold lead of every status banner is near-invisible: dark brown #5A2C06 on #2A1B10. These bolds carry the one sentence a beginner must read ("The new version is downloaded.", "PeakCut can't make clips yet…", "The AI isn't answering.", "The drive … is almost full", "Confirm your email…")
  - Evidence: Computed 1.42:1 (needs 4.5 at 14px); banner bg `#2A1B10` at index.html:87
  - Fix: Set `.vb b{color:var(--brand-deep)}` (#FFB27A = 12.59:1) or `#FFD9BC`; never a darker-than-ground literal
  - (audit: x-contrast)
- **[critical]** web/index.html:803 (`.step:hover`) — Hover paints the guided-step cards light (#F1EBE6) under light text — shell-wide hover remnant on the dark page. Card text is `.step b/.n` `var(--text) #F5F5F5` and `.step .d` `var(--dim)`
  - Evidence: Computed #F5F5F5 on #F1EBE6 = 1.08:1, #A3A3A3 = 2.13:1 while hovering
  - Fix: Hover to a dark tint (`var(--line-2)` #2A2A2A or #1E1E1E); hover states change colour only, per AGENTS.md
  - (audit: x-contrast)
- **[critical]** web/index.html:809 (`tr:hover>td`) — Hover paints every table row light (#FCFAF8) under light text — hits any table in the app
  - Evidence: Computed #F5F5F5 on #FCFAF8 = 1.05:1, faint #A0948C = 2.84:1 while hovering
  - Fix: Hover to `#181818`/`var(--muted)`-over-card; never a light literal
  - (audit: x-contrast)
- **[critical]** web/index.html:570 (`.making`) + markup 1871, 2726, 3447 — The render overlay's shimmer background is light (#F4EFEE/#FBF8F7) under `var(--dim) #A3A3A3` text — "Making this clip…", "Waiting its turn…", "Taking a look…" are unreadable on every clip card while it renders (the error variant at 1870 sets dark `--bad-soft` inline and is fine at 6.25:1)
  - Evidence: Computed 2.21:1 on #F4EFEE, 2.39:1 on #FBF8F7
  - Fix: Dark ground like formats.js:42 does for its video chip: `rgba(0,0,0,.62)` + light text
  - (audit: x-contrast)
- **[critical]** web/index.html:335 (`.lp .tx em`) — The emphasised copy inside the link-composer preview is deep red #A12A2A on the dark `--muted #111111` panel
  - Evidence: Computed 2.59:1 (needs 4.5)
  - Fix: Pale warm red (`#F8A9A9`-class) or `var(--brand-deep)`; measure first
  - (audit: x-contrast)
- **[important]** `web/index.html:2963` (loadHist) — History load swallows every non-404 error silently — a network failure leaves the version list hidden with no message and no retry
  - Evidence: catch body: `if (!/not found\
  - Fix: 404/i.test(e.message\|\|"")) return;` — only 404 falls through to the empty state; any other error returns with nothing on screen | Show a quiet line in `#dlgvers` ("The versions could not be read. Try again.") and make the row retry on next open
  - (audit: clip-dialog)
- **[important]** `web/index.html:2853-2857` (wireEditor.sync) — Dead branch: sync() opens with `if (from === "range") { … if (from === "range") return; }` and is only ever called with `"num"`
  - Evidence: only call site `sync("num")` at 2866-2867; ranges have their own listeners at 2868-2869 — the branch can never run and hides that the two paths were once one
  - Fix: Delete the unreachable block; keep one `sync()` used by both listeners
  - (audit: clip-dialog)
- **[important]** web/index.html:743 — "Sign out" pop-menu item below AA for normal text
  - Evidence: `.pop.menu .danger{color:#C53030}` on `--bg` #0A0A0A = **3.62:1** at 14px normal (needs 4.5); item drawn by openAcct :1262
  - Fix: `color:var(--bad)` (#F87171 ≈ 8:1 on #0A0A0A)
  - (audit: home)
- **[important]** web/index.html:2082 — home page dies silently when `/api/overview` fails — no loading, empty, error or retry state; `#ov` just stays blank
  - Evidence: `loadOverview` body ends `catch { return; }`
  - Fix: catch → draw an error box with a Retry button (the pattern `loadReview` already uses)
  - (audit: home)
- **[important]** web/index.html:685-686 — toasts clip ~10px off-screen on a 390px phone viewport
  - Evidence: `#toasts{right:20px}` + `.toast{max-width:380px}` → left edge at 390−20−380 = **−10px**
  - Fix: `max-width:min(380px, calc(100vw - 40px))`
  - (audit: home)
- **[important]** web/index.html:1398 — dead view-name guard: the "AI not ready" banner still shows on the AI usage page itself
  - Evidence: guard compares `S.view !== "usage"`, but the page id is `ai-usage` (web/feat/usage.js:274-278) and `go()` sets `S.view = v` (:1463), so the comparison never matches
  - Fix: compare against `"ai-usage"`
  - (audit: home)
- **[important]** `web/index.html:2979-2996`, `:2972-2978`, `:2149-2161` — A clip that finishes while you sit on the Review page never appears in the list. `tick()` refreshes `S.jobs` and calls `render()`, which calls `drawReview()` — the clip list, the picker's selected job and the "X of Y decided" pill all come from stale `S.rv`, which only `loadReview()` ever refetches (view switch or `rv_job` change).
  - Evidence: `web/index.html:2975` (`render()` → `drawReview()` only); `S.rv` is assigned solely at `:2155`/`:2158`/`:2160` inside `loadReview()`; `tick()` at `:2988-2996` updates `S.jobs` then calls `render()`. Nothing in the sync path refetches `/api/jobs/{S.rvJid}/review`.
  - Fix: In `tick()`, when `fresh && S.view === "review"`, call `loadReview()` (or refetch `S.rv` for `S.rvJid`) before `render()`.
  - (audit: review)
- **[important]** `web/index.html:2190` + `:480` — The error state is a raw message in a loading-styled div with no way to retry. On a first visit where `/api/jobs` fails, the picker is empty too, so the whole page is one faint grey error string (e.g. "Failed to fetch") and nothing else — a beginner has no next step.
  - Evidence: `web/index.html:2190` (`put(root, picker + '<div class="set-load">' + esc(S.rv.error) + '</div>')`); `.set-load` at `:480` is the loading style (`padding:40px 0;color:var(--faint)`); `picker = ""` when `S.jobs` is empty (`:2153-2155`), which is exactly the failed-fetch case.
  - Fix: Humanize the copy ("Could not load clips — check that the server is running.") and add a "Try again" button wired to `loadReview()`.
  - (audit: review)
- **[important]** web/index.html:2414 — Brand preview hides itself silently on error. The `<img id="br_preview">` has `onerror="this.parentElement.style.display='none'"`, so when /api/style/preview fails (for example a server without ffmpeg, which the preview needs to draw a frame) the whole `#br_prevbox` — the picture **and** the sentence explaining what it shows — vanishes with no message. A missing error state on the page's centrepiece.
  - Evidence: index.html:2414; preview draws with ffmpeg (studio/api_style.py:218); no other error surface for the box
  - Fix: In the onerror, keep the box, hide only the img, and show one line instead: "The preview could not be drawn on this server yet." (keep the existing .sub explanation visible)
  - (audit: transcribe-brand)
- **[important]** web/index.html:466,474,876 — Brand preview is cramped at phone width: measured at 390 px viewport the `.sub` text column is squeezed to 144 px (about 20 characters per line of 13 px text) because the 172 px `flex:none` image plus the 18 px gap take 190 px of the 334 px box interior. There is no stacking query for `.brand-preview`, so the two-column layout never reflows.
  - Evidence: measured: .content 362 px (index.html:876), preview padding 14px (:466), img 172px flex:none (:474), gap 18px (:466) → sub = 144 px
  - Fix: Add `@media (max-width:560px){.brand-preview{flex-direction:column}}` (or cap the img width) so the explanation gets full width on a phone
  - (audit: transcribe-brand)
- **[important]** `web/index.html:258` — `.pill.live` (the "Live"/"Recording" chips) is below WCAG AA for its 12px/600 text
  - Evidence: `#fff` on `--live #EF4444` = 3.76:1, needs 4.5. Painted at `:1901` (livecard head) and `:2113` (overview Creators state())
  - Fix: Swap to dark ink `--brand-ink #160D05` on `#EF4444` → 5.10 (measured in `docs/qa/audit/creators.md`), or darken the bg to `#DC2626` (4.54)
  - (audit: videos)
- **[important]** web/index.html:130 (`.sinfo .lv`), 150 (`.sbadge.rec`), 198 (`.sb-tag.rec`), 199 (`.nav-item.on .sb-tag`), 324 (`.lp .ok.live`) — White 11–12px text on `#E5323F` badges (live/record states) fails AA
  - Evidence: Computed 4.32:1 each (needs 4.5)
  - Fix: Darken the badge red to `#C81E28`-class (white on #C81E28 = 5.72:1, proven by `.bell .dotn` index.html:715)
  - (audit: x-contrast)
- **[important]** web/index.html:258 (`.pill.live`) — White 11px text on `--live #EF4444` chip
  - Evidence: Computed 3.76:1 (needs 4.5)
  - Fix: Same darkening, or `--brand-ink` text on the red
  - (audit: x-contrast)
- **[important]** web/index.html:743 (`.pop.menu .danger`) on `.pick-menu` ground — Account-menu "sign out/delete" red #C53030 at 13px on the menu ground `#2A1A1A`
  - Evidence: Computed 3.04:1 (needs 4.5)
  - Fix: Lighten to `#F87171` on dark (7.16:1)
  - (audit: x-contrast)
- **[important]** `web/index.html:670` — Clip-editor word chips `.ed-w` are ≈26 px tall — the primary transcript interaction: tapping a word seeks the video. On a phone the chips are one dense row of ~26 px targets.
  - Evidence: `padding:4px 8px;font-size:12px;line-height:1.3` → 12×1.3 + 8 + 2 = 25.6 px. polish-mobile names `.chip` (line 54) but `.ed-w` is not a `.chip`.
  - Fix: Add `.ed-w{min-height:44px;padding:8px 10px}` to the polish-mobile 640 px block (or an index.html 640 px rule). Dense transcript rows still wrap fine at 44 px.
  - (audit: x-mobile)
- **[important]** `web/index.html:836` — At ≤560 px the shell hides **every** `.hint` from the page (`display:none`). A beginner on a phone loses all inline explanations of what a field or control does — the hints exist precisely for people who do not program.
  - Evidence: `.hero,.hint{display:none}` inside the 560 px block. `web/feat/settings-explain.js:21` re-shows some settings hints at ≤560 as `display:block` — partial coverage only; hints on other pages (jobs, live, sounds, insights) stay gone.
  - Fix: Either stop hiding `.hint` and let it wrap, or scope the hide to the handful of hints that genuinely do not fit, and extend the settings-explain re-show to the other pages.
  - (audit: x-mobile)
- **[minor]** web/index.html:3382-3386 — `zsave` PUTs the key, then runs `send("/api/zernio/test", …)` with no try/catch. If the test fails after the PUT succeeded, the exception jumps to the outer catch (`index.html:3462`), skipping `S.zOpen = false` and the `S.zernio`/`S.accounts` refresh; the user sees only the raw Zernio error and no word that the key was saved — though a failing new key is now the one in use. The AI flow solves this exact shape one screen away (`index.html:3122-3126`: `let ok = null, why = ""; try { ok = await send("/api/ai/test"); } catch (err) { why = err.message; }` → toasts `Saved, but the test failed. ${why}`).
  - Evidence: Code: `index.html:3383` `const got = await send("/api/zernio/test", {}, "POST");` with no try/catch; contrast `index.html:3123` and the toast at `:3386` only reached when the test succeeds. Not reproduced live (would need to overwrite the real saved key; refused).
  - Fix: Wrap the test call the way the AI flow does: `let got = null, why = ""; try { got = await send("/api/zernio/test", {}, "POST"); } catch (err) { why = err.message; }`, then always run the `S.zernio`/`S.accounts` refresh and toast `got ? "Saved. …" : `Saved, but the test failed. ${why}`` with kind `got ? "ok" : "bad"`.
  - (audit: api-posting)
- **[minor]** `web/index.html:3118-3128, :3146-3163` (Save/Test buttons), `studio/ai.py:523` (`ai.call` default timeout 180 s) — No visible progress during the AI test: the button is disabled but nothing says a test is running, and a slow provider can legally take up to 180 s.
  - Evidence: Code read: both save/test handlers only set `disabled`; no "Testing…" state anywhere. Measured on this install: 5.3 s for Logfare — long enough to look hung; a slow provider can take 30× that.
  - Fix: Set the button text to "Testing…" (and restore it in the finally) while the request is in flight, so a slow provider looks busy rather than broken.
  - (audit: api-transcribe-ai)
- **[minor]** `web/index.html:2741` — Job-head badge shows raw judge counts ("Words 6 · Reaction 2") — jargon a beginner can't act on
  - Evidence: badge string in drawClipDlg
  - Fix: Keep it plain: "6 words · reacts 2" or a single word like "Good" with the counts in a title attribute
  - (audit: clip-dialog)
- **[minor]** web/index.html:331 — skeleton/wait shimmer is a light block on the dark app (no text, visual-only)
  - Evidence: `.sk`/`.lp.wait .th` use the light gradient #F4EFEE/#FBF8F7
  - Fix: tint to the dark palette (e.g. #1E1E1E → #2A2A2A)
  - (audit: home)
- **[minor]** web/index.html:3405 — the bell list is fetched and redrawn twice per "mark read"
  - Evidence: `await markRead(); return openBell().then(openBell);`
  - Fix: `await openBell()` once — `render()` already repaints after markRead
  - (audit: home)
- **[minor]** `web/index.html:2165` + `studio/api_review.py:74-79` — "0:00" is shown as the clip's length when the server could not read its times — a zero that claims the clip is 0 seconds long. `_clip_len()` returns `0.0` on unreadable times, contradicting its own docstring ("simply shows no length"), and `rvCard` renders the duration span unconditionally.
  - Evidence: `web/index.html:2165` (`const dur = fmt(c.duration != null ? …)` rendered unconditionally at `:2174`); `studio/api_review.py:77-79` (`return 0.0` in the except branch) and `:85` (`duration` always present in `_review_line`).
  - Fix: In `rvCard`, omit the duration span when `!c.duration`. The root cause (api_review.py returning `0.0` instead of `None`) belongs to another agent's file — flagging it here as evidence.
  - (audit: review)
- **[minor]** `web/index.html:2143` — The review code sits under a section comment that says "AI usage".
  - Evidence: `web/index.html:2143` (`/* ============================================================ AI usage */` directly above `rvList()` at `:2144`).
  - Fix: Rename the comment to "review queue".
  - (audit: review)
- **[minor]** web/index.html:559 — `.toolpre` background uses `var(--bg2)`, which is defined nowhere
  - Evidence: Grep `--bg2:` across `web/`: 0 definitions. The "Export a schedule command" output renders with a transparent background; text stays readable (inherits #F5F5F5 on #0A0A0A, about 19:1) but the pre looks unstyled, only its border shows
  - Fix: Change to `var(--muted)` (what `.sch-pre` in schedule.js:29 uses) or define `--bg2`
  - (audit: tools-schedule)
- **[minor]** web/index.html:519, 2380, 3142 — `.warnline` errors render with no styling on the Tools tab: the only rule is scoped to `.appsetup`
  - Evidence: `.appsetup .warnline` (index.html:519) is the only `.warnline` rule; `toolFail` (index.html:2380) and the tlschedule error path (index.html:3142) render inside `#tl_schbox` in the plain settings body, so the error inherits body `--text` and looks identical to normal copy
  - Fix: Add an unscoped `.warnline { font-size:12px; color: var(--brand-deep); }` rule; #FFB27A on the settings body measures above 5:1
  - (audit: tools-schedule)
- **[minor]** web/index.html:484–490 — Dead CSS: a legacy bare `.stile` block styles a `class="stile"` that no longer exists anywhere in web/ — style-tiles.js now scopes every rule as `.stilegrid .stile` (style-tiles.js:36–52). Harmless, but it is a second truth about the tiles that nothing uses.
  - Evidence: grep: no `class="stile"` outside the grid; style-tiles.js:36+ uses `.stilegrid .stile` selectors
  - Fix: Delete the legacy block (or fold anything still wanted into style-tiles.js's own sheet)
  - (audit: transcribe-brand)
- **[minor]** `web/index.html:2132` vs `:2124` — Copy inconsistency: the KPI card says "Est. earnings", the Creators table header says "Est. $"
  - Evidence: Both strings in `drawOverview`
  - Fix: Pick one label ("Est. earnings") for both
  - (audit: videos)
- **[minor]** web/index.html:558 (`.toolsrow small`) — Latent trap: `color:var(--muted)` #111111 as text on `--bg` = 1.05:1 — but dead CSS, no markup uses `.toolsrow` anywhere in `web/` (grep: only CSS lines 555–558)
  - Evidence: Computed 1.05:1; grep shows 0 usages
  - Fix: Delete the rule or set `var(--dim)` before anybody revives it
  - (audit: x-contrast)
- **[minor]** web/index.html:559 (`.toolpre`) — `background:var(--bg2)` — `--bg2` is not defined in `:root` (transparent fallback); also dead CSS (no markup)
  - Evidence: grep: `--bg2` appears once, in this rule
  - Fix: Use `var(--bg)`/`var(--card)` or delete the rule
  - (audit: x-contrast)
- **[minor]** web/index.html:391 (`.nstep .ctl button:hover`) + web/feat/style-tiles.js:47-49 (`.stile-check`) — White icon on the orange `--brand` ground is under WCAG 1.4.11's 3:1 for graphics; both controls carry other indicators (outline, tile state) so impact is small
  - Evidence: Computed 2.34:1
  - Fix: Use `--brand-ink` icons on brand grounds (8.22:1)
  - (audit: x-contrast)
- **[minor]** web/index.html:346 (`.btn.primary:disabled`) — Disabled-state pair #B9A597 on #F3E7DD = 1.94:1 — WCAG exempts disabled controls; noted so the fix wave doesn't "fix" it
  - Evidence: Computed 1.94:1
  - Fix: None needed (exempt)
  - (audit: x-contrast)
- **[minor]** web/index.html:226-227 (`label.sw input`) — Light switch track #DCD2D0 with #fff knob on the dark page — knob-on-track 1.48:1 makes the knob hard to see; state still readable from position/border
  - Evidence: Computed 1.48:1
  - Fix: Dark track (`#2A2A2A`) with the pale knob; measure first
  - (audit: x-contrast)
- **[minor]** web/index.html:14-16 (`:root` comment) vs measured — Claims 18.4/8.1/4.6/7.6/10.4/9.0/6.3, measured 18.16/7.85/4.74/8.48 (brand on bg)/11.22 (brand-deep on bg)/10.30 (good on bg; 8.01 on good-soft)/7.16 (bad on bg)
  - Evidence: Measured table in this report
  - Fix: Update the comment to the same Python rounding as polish-contrast.js so the two agree
  - (audit: x-contrast)
- **[minor]** web/index.html:2494 — Font-picker empty state uses typographer jargon: "This server sent no font list, so only the style's own face is offered." The rest of the app says "font".
  - Evidence: File line: `2494
  - Fix: grid.innerHTML = `<p class="hint">This server sent no font list, so only the style's own face is offered.</p>`;` | "...so only each style's own font is offered."
  - (audit: x-copy)
- **[minor]** web/index.html:2549 — The AI Address field's hint names neither result nor action: "Where the service answers." A beginner cannot tell what to type or whether to leave it blank.
  - Evidence: File line: `2549
  - Fix: <label class="f" id="ai_basewrap">Address<input id="ai_base" ...><span class="hint" id="ai_basehint">Where the service answers.</span></label>` | "Leave blank unless your key comes with its own web address."
  - (audit: x-copy)
- **[minor]** web/index.html:2439 — Watermark hint mixes one explained term with file-system jargon: "A handle like @yourname, a PNG logo path, or blank for none."
  - Evidence: File line: `2439
  - Fix: <label class="f">Watermark<input id="br_watermark" ...><span class="hint">A handle like @yourname, a PNG logo path, or blank for none.</span></label>` | "A handle like @yourname, the location of a PNG logo on this computer, or blank for none."
  - (audit: x-copy)
- **[minor]** web/index.html:2459 — Editing jargon twice in one control: toggle label "Flash on the punch-in", hint "A short white flash when the clip punches in." A beginner does not know "punch-in".
  - Evidence: File line: `2459
  - Fix: ${toggle("br_flash", "Flash on the punch-in", "A short white flash when the clip punches in.", b.flash)}` | Label "Flash when the clip zooms in"; hint "A short white flash at the moment the picture zooms in quickly."
  - (audit: x-copy)
- **[minor]** web/index.html:2098 — Empty-chart text is doubly temporal and reads oddly: "No clips in the last 14 days yet".
  - Evidence: File line: `2098
  - Fix: <text class="none" ...>No clips in the last 14 days yet</text>` | "No clips in the last 14 days".
  - (audit: x-copy)
- **[minor]** web/index.html:2741 — The clip dialog's score badge uses two different formats for the same slot and shows no scale: "Words 7 · Reaction 4", "Score 7", or "Clipped by hand". A beginner cannot tell what 7 is out of.
  - Evidence: File line: `2741
  - Fix: <span class="badge ...>${c.judges ? "Words " + c.judges.words + ... : c.score ? "Score " + c.score : "Clipped by hand"}</span>` | Pick one format with a scale: "Score 7/10" or "Words 7/10 · Reaction 4/10".
  - (audit: x-copy)
- **[minor]** web/index.html:2431 + 2755 — The same setting has two names in two places: the Brand page section is titled "Hook" ("Hook title colour", "Hook position") while the clip editor calls the same field "Big text". A beginner will not connect them.
  - Evidence: File lines: `2431
  - Fix: <h3>Hook</h3>` and `2755 | <label class="f">Big text<input data-f="hook" ...>` | Add a hint under the Brand section heading: "The hook is the big text at the top of the clip — the editor calls it Big text." Or rename the Brand section "Big text".
  - (audit: x-copy)
- **[minor]** `web/index.html:678` — Clip-editor rail-nav buttons `.ed-railnav button` ≈35 px tall — the pane tabs inside the editor dialog.
  - Evidence: `padding:6px 8px;font-size:12px`, `font:inherit` line-height 21 px → 21 + 12 + 2 = 35 px.
  - Fix: `min-height:44px` at ≤640 px.
  - (audit: x-mobile)
- **[minor]** `web/index.html:142` — `.splat button` is a fixed 30×30 box — the platform buttons of the live-stream panel.
  - Evidence: `width:30px;height:30px` literal.
  - Fix: 44×44 box at ≤640 px (or 30 px icon inside a 44 px hit box).
  - (audit: x-mobile)
- **[minor]** `web/index.html:703` — New-toast close `.ntoast .x` is 22×22 — the smallest control on the page.
  - Evidence: `width:22px;height:22px` literal.
  - Fix: 44 px hit box (toasts auto-dismiss, but a user may still tap close).
  - (audit: x-mobile)
- **[minor]** `web/index.html:850` — Tour close `.tr-x` is 32×32.
  - Evidence: `width:32px;height:32px` literal.
  - Fix: 44 px box at ≤640 px (a 700 px query for `.tr-card` already exists at line 869).
  - (audit: x-mobile)
- **[minor]** `web/index.html:722` — "Mark read" in the notifications pop, `.pop-head button`, ≈29 px tall.
  - Evidence: `padding:4px 6px;font-size:12px`, inherited line-height 21 px → 29 px.
  - Fix: `min-height:44px` at ≤640 px.
  - (audit: x-mobile)
- **[minor]** `web/index.html:712` — Sidebar account button `.me-btn` ≈38 px tall (borderline, included for completeness).
  - Evidence: `padding:4px;margin:-4px` around a 30 px avatar → 38 px.
  - Fix: `min-height:44px` at ≤640 px.
  - (audit: x-mobile)
- **[minor]** `web/index.html:362` — Dropdown option buttons `.pick-opt` ≈37 px tall — the picker listbox rows (creator/brand pickers on every page).
  - Evidence: `padding:8px 10px;font-size:13px`, `button{font:inherit}` line-height 21 px → 21 + 16 = 37 px. The trigger `.pick-btn` has `.chip` and is covered; the options are not.
  - Fix: `@media (max-width:640px){.pick-opt{min-height:44px}}`.
  - (audit: x-mobile)
- **[minor]** `web/index.html:396` + `:421` + `:397` — `.tiles3{repeat(3,minmax(0,1fr));gap:8px}` has **no ≤640 px fold** (the 640 px query at 421 folds only `.og`/`.nsteps`). In the create dialog at 390 px (358 px dialog, 24 px padding → 310 px inner, 2×8 gap) each `.tile-o` button is ≈98 px wide and ≈35 px tall.
  - Evidence: `repeat(3,minmax(0,1fr))` literal; arithmetic above; no `@media` anywhere names `.tiles3` (grep over both files, 68 `@media` hits reviewed). Labels like "Word by word" wrap to two lines.
  - Fix: Add `@media (max-width:640px){.tiles3{grid-template-columns:repeat(2,minmax(0,1fr))}.tile-o{min-height:44px}}` — 2 columns makes the tiles ~151 px wide, one line of label, and a real tap target.
  - (audit: x-mobile)
- **[minor]** `web/index.html:396,397` — Create-dialog caption-style tiles are ≈98 px wide at 390 px, so their labels wrap to two cramped lines; readable, but the same `.tiles3` fold that fixes the tap target fixes the wrap.
  - Evidence: Same arithmetic as findings table row above.
  - Fix: Covered by the `.tiles3` fold fix.
  - (audit: x-mobile)
- **[usability]** web/index.html:1018 — `ask()` always sets `autofocus` on the confirm button — even for destructive dialogs (delete creator/clip/job, sign out), so a reflex **Enter confirms the destructive action**
  - Fix: autofocus the Cancel button when `danger` is true
  - (audit: home)
- **[usability]** web/index.html:1309 — when the server has no feedback link, the error toast says "Copy this message and open an issue on GitHub." but nothing is copied — the working branch (:1310) copies automatically, this one makes the user hand-copy unselectable toast text
  - Fix: run `navigator.clipboard.writeText(context)` before the toast, then say "Copied. Open an issue on GitHub."
  - (audit: home)
- **[usability]** web/index.html:3022-3024 — drag/drop handlers only preventDefault when a `.composer` exists — dropping a video on Settings/Review/Analytics **navigates the browser to the dropped file**, losing the page
  - Fix: `window.addEventListener("dragover"/"drop", e => e.preventDefault())` globally, keep the composer branch for acceptance
  - (audit: home)
- **[usability]** web/index.html:289,298 — composer removes `:focus-visible` outlines and chips only signal focus with a subtle background change — keyboard focus is easy to lose on the primary flow
  - Fix: keep a 2px `var(--brand)` outline on chips/inputs inside the composer
  - (audit: home)
- **[usability]** `web/index.html:2215-2218` + `:2178` — The Skip button on a card does not skip *that* card — `rvSkip()` advances from the page cursor (first undecided clip), so pressing Skip on the last card acts on a different clip and scrolls somewhere unexpected. Same family: pressing A/X while a different card's button has focus approves/rejects the cursor clip, not the focused one.
  - Fix: Make the card's Skip call `rvAdvanceFrom(c.id)` with its own cid (the data attribute is already on the button); keep the S key as the global "skip ahead".
  - (audit: review)
- **[usability]** `web/index.html:2187` + `studio/jobs.py:1085-1098`, `studio/api_review.py:94` — The help line "Clips waiting for a yes or no, newest first." sits under the "Pick a video" heading but reads as describing the clip list below — which is oldest-first (clips are appended as clip01, clip02… and the review endpoint preserves that order). A beginner scanning for the newest take starts at the wrong end.
  - Fix: Reword to "Videos with finished clips, newest first." and let the Clips section state its own order ("oldest takes first").
  - (audit: review)
- **[usability]** `web/index.html:2176-2178` — The A/X/S keyboard shortcuts are documented only in the section help paragraph; the Approve/Reject/Skip buttons themselves carry no hint, so the shortcut is invisible at the point of use.
  - Fix: Add a small key hint to each button, e.g. a `<span class="hint">A</span>` inside the button or `title="Shortcut: A"` — one-line change, no server work.
  - (audit: review)
- **[usability]** `web/index.html:1345` — The Review nav row shows no count of clips waiting for a decision (the All videos row shows a count badge, `:1343-1344`), so there is no way to see review work waiting from any other page.
  - Fix: Show an undecided-clip badge on the nav row. The data needs a small server-side aggregate: per-job `remaining` exists on `/api/jobs/{jid}/review` (`studio/api_review.py:95`), but nothing global ships in `/api/status` or `/api/sync` today.
  - (audit: review)
- **[usability]** web/index.html:2367-2371 — Three places produce schedule text with different defaults: the Tools page's collapsed "Export a schedule command" (09:00,18:30), the Schedule page (06:00,18:00), and the unmounted autopilot card (09:00,18:30). A beginner cannot tell when to use which, and the generator is easy to miss behind `<details>`
  - Fix: Replace the collapsed generator with one line pointing to the Schedule page, or state in the summary when to use it instead
  - (audit: tools-schedule)
- **[usability]** web/index.html:2369 — The Tools page Times field has no format hint; the equivalent field on the Schedule page does (schedule.js:314-315). A bad time is dropped quietly server-side (autopilot.js:127-128 comment), so typing "9am" can silently produce a 09:00 schedule
  - Fix: Add the same hint: "Hours and minutes, separated by commas, like 09:00,18:30"
  - (audit: tools-schedule)
- **[usability]** web/index.html:2364-2366 — The Tools page is a pointer page: "Scheduling ... Open schedule" costs one extra click to reach the real page, and the page copy does not say what the Schedule page holds
  - Fix: Merge the Schedule content into /app/tools, or name the destination in the help line ("Open the Schedule page to copy and install the timers")
  - (audit: tools-schedule)
- **[usability]** `web/index.html:2194` vs `web/feat/keys.js:23-27` — Two contradictory keyboard legends on the review page: the help text says "A says yes to the next clip, X says no, S skips ahead"; the keys.js hint says "Enter approve / Backspace reject / Right next clip". Both sets work (keys.js:6-8 deliberately leaves a/x/s alone) but neither mentions the other, so a beginner cannot tell which legend is real
  - Fix: One legend that names both sets (e.g. "Enter or A — approve · Backspace or X — reject · Right or S — next"), or align the two texts
  - (audit: videos)
- **[usability]** `web/index.html:2140` — The Post queue empty state gives no next action, unlike every other empty state on the page
  - Fix: Add one line: what queues a post (approved clips + autopost on) and a link to All videos or Settings
  - (audit: videos)

## web/feat/pill.js

- **[critical]** `web/feat/pill.js:20` — The pill's secondary clause ("· N videos running") is near-unreadable: `--dim #A3A3A3` text on the light pill backgrounds
  - Evidence: 2.38:1 on run-kind `#FFF7F0` (pill.js:7), 2.33:1 on rec-kind `#FFF3F3` (pill.js:10); 13px text needs 4.5. Shown whenever kind=rec and running>0 (words() pill.js:60-65 sets it, paint() :138 toggles `.pcrun-2` on)
  - Fix: Give `.pcrun-2` a dark per-kind colour (e.g. `#8A3C08` on `#FFF7F0`, `#9E121B` on `#FFF3F3`) instead of `var(--dim)`
  - (audit: videos)
- **[critical]** `web/feat/pill.js:13` — Hovering the wait-state pill flips it light while the text stays light grey: the label vanishes exactly when the user points at it
  - Evidence: `.pcrun.is-wait:hover{background:#F1ECE7}` with text still `var(--dim) #A3A3A3` = 2.15:1 during hover (resting 7.54:1 is fine)
  - Fix: Keep the hover dark (e.g. `background:var(--line)`) or set a dark ink colour for the hover state
  - (audit: videos)
- **[critical]** web/feat/pill.js:7 + web/feat/polish-colour.js:54 — Run-pill base text unreadable on its overridden background. pill.js paints light bg + dark text; polish-colour.js:54 (`body .pcrun.btn`, specificity 0,2,1) overrides only the background to `--brand-soft #2A1B10`, leaving `color:#8A3C08` stranded. This is the topbar "Make clips" button on every page, 13px (`btn sm`, index.html:211)
  - Evidence: Computed #8A3C08 on #2A1B10 = 2.16:1 (needs 4.5). Hover (pill.js:8) is light-on-light and fine at 7.99:1 — base state is the broken one
  - Fix: In polish-colour.js:54 also set `color:#FFD9BC` (12.59:1) or delete the override; measure before choosing
  - (audit: x-contrast)
- **[critical]** web/feat/pill.js:10 + web/feat/polish-colour.js:58 — Recording-state run pill unreadable: `color:#9E121B` stranded on `--bad-soft #2B1416` by the same body-prefixed background override (0,3,1 beats 0,3,0)
  - Evidence: Computed 2.10:1 (needs 4.5 at 13px). is-rec:hover (pill.js:11) fine at 7.08:1
  - Fix: Same fix: set a pale red ink (`#FFB4B7`-class) or remove the override; measure first
  - (audit: x-contrast)
- **[critical]** web/feat/pill.js:13 (`.pcrun.btn.is-wait:hover`) — Hover-only: keeps `color:var(--dim) #A3A3A3` under a light #F1ECE7 hover background
  - Evidence: Computed 2.15:1 while hovering (base state 7.49:1 is fine)
  - Fix: Add `color:#3A2C25` to the hover rule (dark on light = readable) or hover to a dark tint
  - (audit: x-contrast)
- **[minor]** `web/feat/pill.js:12` — The wait-state pill is a dark rectangle on the dark topbar: weakly visible until read
  - Evidence: bg `--muted #111111` on topbar `--bg #0A0A0A` with border `--line-2 #2A2A2A` → boundary ≈ 1.33:1 (the text itself passes at 7.54:1)
  - Fix: Slightly lighter pill bg (`--line #1E1E1E`) or a stronger border
  - (audit: videos)

## web/feat/day.js

- **[critical]** `web/feat/day.js:17,21` — "Make my day" card paints a light cream radial-gradient on the dark app; the help sentence and error notes are unreadable over it
  - Evidence: gradient `radial-gradient(130% 190% at 0% 0%,#FFF9F4 0%,var(--brand-soft) 62%,#FFF7F0 100%)`; `.day-help` ink `var(--text)` #F5F5F5 over the light region at the sentence's start ≈2.7:1 (worst ≈1.04:1); `.day-note` --bad #F87171 over the same region ≈1.1:1 — far below the 3:1 floor
  - Fix: Drop the cream stops: keep the card on a dark ground (e.g. `var(--brand-soft)` flat or a gradient between `--brand-soft` and a darker warm tone), and measure `.day-help`/`.day-note` ink against the result like polish-contrast.js does
  - (audit: clip-dialog)
- **[critical]** `web/feat/day.js:27,29` — `.day-note` status line (default --dim #A3A3A3, bad #F87171) fails over the gradient's light bottom-left region
  - Evidence: --dim over interpolated ≈#9E948D ≈2.9:1; --bad over the same ≈1.1:1 — both below 4.5 for 13px text
  - Fix: Same fix as above; once the card is dark both pass untouched
  - (audit: clip-dialog)
- **[critical]** web/feat/day.js:17 (with 21, 27) — Day card background is a white-page remnant gradient — light at both ends, dark in the middle: `radial-gradient(130% 190% at 0% 0%, #FFF9F4 0%, var(--brand-soft) 62%, #FFF7F0 100%)` — under light text. `.day-help` `var(--text) #F5F5F5`, `.day-note` `var(--dim) #A3A3A3`
  - Evidence: Computed help on #FFF9F4 = 1.04:1, note on #FFF7F0 = 2.38:1 at the light corners; mid is 15.25:1 — text is unreadable near top-left/bottom-right
  - Fix: Flat dark ground (`var(--brand-soft)` or `#1E1612`) so the existing light text reads
  - (audit: x-contrast)

## web/feat/audio-page.js

- **[critical]** `web/feat/audio-page.js:311` — **The Keep button never renders on any catalogue shelf.** `const kept = r.kept !== false;` assumes a per-row `kept` flag, but no server row carries one (catalogue rows: slug/title/about/…/popularity; library rows: slug/title/seconds/bytes), so `kept` is always `true` and the `alb-keep` "Keep" button (line 328) is unreachable dead code on Trending/Reaction/Funny/Fail/Hype and on every card. The one action the shelf note advertises ("Nothing is downloaded until you press Keep", line 218) cannot be performed.
  - Evidence: `curl /api/memesounds/trending?window=24h` rows contain no `kept` key; the response carries a **top-level** `"kept":[…]` slug list (`studio/api_memesound.py:119`, live-verified) that the page never reads; `studio/memesound.py:194-208` `rank()` and `:381-382` `library()` add no kept field
  - Fix: Read the response's top-level kept list into a Set in `loadBoard`; compute `kept = keptSet.has(r.slug)` in `card()`
  - (audit: audio-library)
- **[critical]** `web/feat/audio-page.js:325-328, 491-499` — **Download and Remove offered for sounds that are not on this machine, and Remove reports a false success.** On catalogue shelves every card renders a Download link to `/api/memesounds/play/<slug>` — which 404s for un-kept sounds — and a Remove button; pressing Remove DELETEs a file that does not exist, the server answers `{"ok":false}`, and the page still toasts "Removed from this machine. The catalogue still has it."
  - Evidence: `curl DELETE /api/memesounds/library/nonexistent-sound-00000` → `{"ok":false,…}` (live); `studio/api_memesound.py:209-210` play 404s for un-kept; the page ignores `ok` at lines 493–494
  - Fix: Same kept-set fix; render Download/Remove only for kept rows; honor `ok:false` with "It was not on this machine."
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:463-478` — **Play on an un-kept sound blames the browser.** The play route 404s for catalogue sounds; the catch (472–474) shows "The browser would not play it here. It is still fine on the clip." — wrong diagnosis; the sound simply is not downloaded.
  - Evidence: `curl GET /api/memesounds/play/chicken-on-tree-screaming-53890` → **404** `{"detail":"That sound is not on this machine yet."}` (live)
  - Fix: Check the kept set before playing (or catch the 404) and say "Not on this machine yet — press Keep first."
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:378-384, 407-444` — **One full-file download per card just to paint a decorative waveform.** `draw()` calls `bars(slug)` for every canvas; `bars()` fetches the complete mp3 (line 416) and decodes it, once per sound per visit. On the Saved shelf that is one full download per kept sound every time the page loads; on catalogue shelves every fetch 404s and leaves a blank box.
  - Evidence: Live library has 4 sounds → 4 full mp3 fetches on load; no virtualization; decode cache is per-session only
  - Fix: Draw a deterministic placeholder from the slug hash, or decode lazily on intersection, or have the server send peak data
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:38-44` — **Selected/hovered shelf pill text fails WCAG AA.** `.alb-cat` is white 11.5px bold; the pressed pill gets `filter:brightness(1.22)` and hover `brightness(1.16)`, brightening the orange pills past the limit.
  - Evidence: White on brightness(1.22) `#B45309` = **3.55:1**; on `#C2410C` = **3.67:1**; hover `#B45309` = 3.89:1, `#C2410C` = 4.02:1 — all below the 4.5:1 required for 11.5px text (not large). Unpressed passes 5.02/5.18
  - Fix: Keep the pressed/hover colour at the base (the inset ring already shows state) or darken instead of brighten; re-measure to ≥4.5:1
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:361-372` — **List view drops the row's main actions.** List rows render only Play/Like/Bookmark while the comment claims "the same information"; Download/Remove/Keep vanish, so the Saved shelf in list view cannot remove or download anything.
  - Evidence: lines 363–372 vs `card()` 317–329
  - Fix: Render the same trailing action the card shows
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:184-185, 291-299` vs `:213-218` — **Sidebar "Find" looks like the page's search but only filters the current shelf.** The sidebar label "Find" (a client-side filter of `B.rows`) sits above the real catalogue search ("Search every sound", below the list); a beginner types into "Find" expecting catalogue results and gets a silently shrinking shelf.
  - Evidence: `shown()` filters only `B.rows` (291–299); the catalogue search is a separate control at 213–218
  - Fix: Rename the label to "Filter this shelf" and add the hint "only filters the sounds above"
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:186-189` — **"Longest" is not a readable label for a max-length filter.** `<label>Longest<select>` with options "Any length / Under 2s / Under 5s / Under 10s" — a beginner cannot parse "Longest → Under 2s" in five seconds.
  - Evidence: line 186
  - Fix: Rename to "Length"
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:215, 222-224` — **"DankMachine" jargon is unexplained.** The placeholder "Search all of DankMachine" and the rights note name DankMachine with no explanation; a beginner has no idea it is the sound catalogue the page is searching.
  - Evidence: lines 215, 222–224
  - Fix: "Search the whole catalogue" / "The sound catalogue (DankMachine) marks most sounds…"
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:481-489` — **Keep teleports you off the shelf you are browsing.** `keep()` always `go("kept")` after a successful keep — keeping a sound from Trending jumps you to Saved and you lose your place in the list.
  - Evidence: line 485
  - Fix: Stay on the current shelf and flip that card's action to Remove
  - (audit: audio-library)
- **[important]** `web/feat/audio-page.js:85-87` — Sounds-page per-sound buttons `.alb-mini` are ≈31 px tall — the only preview/download control on every catalogue sound row.
  - Evidence: `padding:4px 8px;font-size:11px` with `font:inherit` line-height 21 px → 21 + 8 + 2 = 31 px. No matching min-height in polish-mobile.
  - Fix: `@media (max-width:640px){.alb-mini{min-height:44px}}` (page-side override already narrows `.alb-sidebar` inputs, line 52–55, so this fits the same block).
  - (audit: x-mobile)
- **[minor]** `web/feat/audio-page.js:381` vs CSS `:82` — **The waveform "empty" fallback never shows.** On decode failure the code adds the class it already has (`cv.classList.add("alb-wave")`) instead of `"empty"`, so `.alb-wave.empty` ("no bars") is dead and a failed decode leaves a blank dark box with no explanation.
  - Evidence: CSS line 82 defines `.alb-wave.empty`; markup never gains `empty`
  - Fix: Add `"empty"` and let the existing fallback text show
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:42, 65, 321, 338, 44, 410/442` — **Repo-rule violations and dead code.** `box-shadow` on the pressed pill (42) and view tab (65) — the repo rule is "no shadows"; `(liked ? icon("heart") : icon("heart"))` both branches identical (321); `icon("down")` never used (338); `.alb-cat b` CSS with no matching markup (44); `void audio` dead var (410, 442).
  - Evidence: AGENTS.md rule "no shadows"; the lines above
  - Fix: Drop the shadows (state is already shown by colour/ring), the dead ternary, the unused icon, the dead CSS
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:293-298` — **The length filter silently does nothing on catalogue shelves.** `shown()` treats missing seconds as 0, so every unknown-length catalogue sound passes "Under 2s/5s/10s" — the filter claims a limit it does not apply.
  - Evidence: Live trending rows carry no `seconds` key
  - Fix: Say "known lengths only" in the option text, or grey the filter when the shelf has no lengths
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:215, 385, 388-398, 540-544` — **Stale search results with an empty box after navigating away and back.** The page renders `alb_search` with no value and `load()` never clears `B.search`/`B.hits`, but `draw()` → `drawHits()` re-renders the old hits — results with no query visible.
  - Evidence: lines 540–544 clear nothing; `drawHits()` runs unconditionally from `draw()`
  - Fix: Clear `B.search`/`B.hits` in `load()` (or restore the query into the box)
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:272-274` — **Silent drop of shelf clicks while a load is in flight.** `if (B.busy) return;` ignores a pill click during a load with no feedback, and the pill's pressed state stays on the old board (`barHtml` is only re-drawn inside `go()`).
  - Evidence: line 273; `barHtml` assignment only inside `go()`
  - Fix: Disable the pills while busy, or queue the click
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:540-544` — **Board selection resets on every page re-entry.** `if (!B.rows.length) B.board = "kept";` bounces an empty Liked/Bookmarked/Mine shelf back to Saved whenever you leave and return to the page.
  - Evidence: line 542
  - Fix: Remember the last board regardless of row count (module state or localStorage)
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:263` — **Uploading your own file is a trip to another page.** The Mine shelf's empty state says "Upload one in the clip editor" — the claim is true (`POST /api/memesounds/upload` exists at `studio/api_memesound.py:162`, wired in `web/feat/meme-timeline.js:143`), but the library is the natural home; one button here would make it a one-step flow.
  - Evidence: route + wiring above
  - Fix: Add an Upload button on the Mine board posting to `/api/memesounds/upload`
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:364` vs `:313` — **A lone "·" stands in the duration chip in list view.** For sounds with no length the card view shows a globe icon ("in the catalogue, not on this machine") but list view shows a meaningless "·".
  - Evidence: `secsBare` fallback at 364 vs globe at 313
  - Fix: Show the globe in list view too
  - (audit: audio-library)
- **[minor]** `web/feat/audio-page.js:321` — Dead ternary — both branches identical, so the "like" icon never changes with state
  - Evidence: `(liked ? icon("heart") : icon("heart"))` on line 321
  - Fix: Replace the ternary with `icon("heart")`. Not user-facing: state is still visible via `aria-pressed` + CSS `.alb-mini[aria-pressed="true"]` — but the code misleads readers into thinking the icon is state-driven
  - (audit: x-console-risks)
- **[minor]** `web/feat/audio-page.js:313` — The globe icon shown instead of a duration carries no explanation — a beginner cannot tell it means "in the catalogue, not on this machine yet"
  - Evidence: `known(r.seconds) ? esc(secsBare(r.seconds)) : icon("web")` — icon rendered with no `title` and no text, while every neighbouring button has a `title` (:318, :321, :323, :327, :328)
  - Fix: Add `title="In the catalogue, not on this machine yet"` to the `.alb-ico` span (or a short text hint)
  - (audit: x-console-risks)
- **[minor]** web/feat/audio-page.js:215 — The catalogue's name is used but never introduced: placeholder "Search all of DankMachine"; the rights note at 222 explains what DankMachine marks, never what it is.
  - Evidence: File line: `215
  - Fix: '<input type="search" id="alb_search" placeholder="Search all of DankMachine" ...>'` | Introduce it once at the first mention: "Search all of DankMachine — the sound catalogue" or "Search the whole catalogue".
  - (audit: x-copy)
- **[minor]** `web/feat/audio-page.js:63-64` — Sounds-page tabs `.alb-tab button` ≈31 px tall.
  - Evidence: `padding:5px 11px;font-size:12px`, `font:inherit` line-height 21 px → 31 px.
  - Fix: `min-height:44px` at ≤640 px.
  - (audit: x-mobile)
- **[minor]** `web/feat/audio-page.js:439` — A failed waveform fetch leaves a blank canvas with no words. The row still shows title / Play / Keep, so nothing is broken, but the empty waveform slot carries no explanation of why it is empty.
  - Evidence: `audio-page.js:439` `.catch(() => done(null))` — the failure caches `null` and draws nothing; no note is set anywhere on the failure path.
  - Fix: On failure, draw a one-line note in the waveform slot ("The waveform could not be drawn for this sound") or hide the canvas slot.
  - (audit: x-states)

## web/feat/autopilot.js

- **[critical]** web/feat/autopilot.js:21-23 — `.pcauto-warn` text is near-black on near-black: `color: var(--brand-ink)` on `background: var(--brand-soft)`
  - Evidence: #160D05 on #2A1B10 (index.html:17). L=0.00470 vs L=0.01314, ratio (0.01314+0.05)/(0.00470+0.05) = 1.15:1, fails 3:1 and 4.5:1. polish-contrast.js:29 overrides only --faint, never this pair. Any scheduler warning inside the card is effectively invisible
  - Fix: Pair the panel with a light ink, e.g. `color: var(--brand-deep)` (#FFB27A on #2A1B10 = 9.4:1, measured). Latent today because the card never mounts (B2/B3); must be fixed before or with the mount fix
  - (audit: tools-schedule)
- **[critical]** web/feat/autopilot.js:322, 344 — The autopilot "Clip on a schedule" card is unreachable, same `#toolsec` pattern
  - Evidence: `watchMount()` (autopilot.js:390) returns at line 344 when `#toolsec` is absent, so the card never mounts and the `last` plan restore (372-381) never runs. The install/remove capability survives only through schedule.js on /app/schedule
  - Fix: Same mount fix as B2. Note B1 becomes visible once the card mounts, so fix the colour in the same wave
  - (audit: tools-schedule)
- **[minor]** web/feat/autopilot.js:176, 193 — Shared `arming` timer between the Install and Remove buttons: arming one after the other cancels the first button's 8-second timeout, leaving it armed indefinitely
  - Evidence: `arming` is one module-level variable (line 176); `armAgain` overwrites it (line 193) without clearing the other button's dataset state. Only reachable on the no-`ask()` fallback path (line 202), and the card is currently unmounted (B3)
  - Fix: Track one timer per button (for example on `b.dataset`), or disarm the other button when arming one
  - (audit: tools-schedule)
- **[minor]** web/feat/autopilot.js:253, 292 + web/feat/schedule.js:254 — A schedule "installed" and "off this machine": "The schedule is installed." (253), "The schedule is off this machine." (292), "The schedule was installed." (schedule.js:254). "Off this machine" reads as "disabled"; "installed" is odd English for a schedule.
  - Evidence: File line: `292
  - Fix: PeakCut.toast("The schedule is off this machine.", "ok");` | "The schedule is set." / "The schedule was removed." — keep the same verb pair in both files.
  - (audit: x-copy)

## web/feat/audio-edit.js

- **[critical]** `web/feat/audio-edit.js:769,584,444,538-540` — The download control is missing: handler `data-act="aed-keep"` is registered but no element in any web file renders it, so `keep()` (POST `/api/memesounds/keep`) is unreachable from the editor. The page's own AI instruction "Keep N of them on this machine before saving: use Find on the right" (538-540) is a dead end - Find shows rows with only "Add" (444), which calls `addAt` (adds a cue, downloads nothing, 757). Saving such a cue fails 400: `studio/memesound.py:474-475` "The sound {slug} is not on this machine yet." -> `studio/api_memesound.py:258-261`. Proven live: search returns `bruh` (200) while `play/bruh` -> 404.
  - Evidence: grep: `data-act="aed-keep"` = 0 elements in web/; HTTP 404 on `play/bruh`; `cue_ok` at memesound.py:474
  - Fix: Render a Keep button on shelf rows not yet kept (`data-act="aed-keep"` already works through `web/plugins.js:151-166`), or make Add auto-keep (call `keep(slug)` then `addAt`), or reword the AI note to point at the Audio page
  - (audit: audio-editor)
- **[important]** `web/feat/audio-edit.js:442-445` — Nested `<button>` inside `<button>` in the shelf list. The HTML fragment parser closes the outer row at the inner `button` start tag (spec 13.2.6.4.7), so the Add button becomes a sibling of the row: the row's second grid column (`.go`, line 120) renders empty and Add dangles below the row instead of right-aligned inside it; hovering Add no longer highlights the row
  - Evidence: lines 442-445 markup; `tests/test_feat_files.py` checks only `node --check`/registration/esc/id, so nothing catches it
  - Fix: Make the outer element `<div class="aed-row" role="button" tabindex="0">` (drag is delegated on `[data-sound]` and keeps working), or render Add as `<span role="button" data-act="aed-add">` inside the row
  - (audit: audio-editor)
- **[important]** `web/feat/audio-edit.js:82` (+ 68, 370-372, 393) — Empty-state guidance text below AA: `.aed-empty{color:#6E6E6E}` measures 3.7:1 on its backgrounds (lane `#111` line 68; cues list on `--card:#111111`), needs 4.5:1 at 11.5px. It is the only instruction the empty track and the empty cues list give
  - Evidence: measured 3.7:1 (`#6E6E6E` on `#111111`); palette pairs around it measure 7.49:1 (`--dim`) and 6.39:1 (`--faint` lifted)
  - Fix: Use `var(--dim)` (#A3A3A3 -> 7.49:1) or `var(--faint)` (#A0948C -> 6.39:1)
  - (audit: audio-editor)
- **[important]** web/feat/audio-edit.js:81-82 (`.aed-empty`) — Empty-state copy on the audio-edit lane is #6E6E6E at 11.5px on lane bg `#111` (audio-edit.js:68)
  - Evidence: Computed 3.70:1 (needs 4.5)
  - Fix: Use `var(--dim)` #A3A3A3 (7.49:1) or `var(--faint)` #A0948C in main (6.39:1)
  - (audit: x-contrast)
- **[important]** web/feat/audio-edit.js:65-66 (`.aed-ruler b`) — Ruler time labels #7C7C7C at 10px on `--track2 #161616` (audio-edit.js:61)
  - Evidence: Computed 4.34:1 (needs 4.5) — borderline fail on the smallest text in the app
  - Fix: `var(--dim)` or #8F8F8F; keep the 10px size but raise the ink
  - (audit: x-contrast)
- **[minor]** `web/feat/audio-edit.js:66` — Ruler tick labels marginally below AA: `.aed-ruler b{color:#7C7C7C}` on `--track2 #161616` measures 4.34:1 at 10px (needs 4.5). Hardcoded, so the `polish-contrast.js` lift of `--faint` does not reach it
  - Evidence: measured 4.34:1; `#8C8C8C` on the same bg = 5.38:1
  - Fix: Change to `#8C8C8C` (5.38:1) or `var(--dim)`
  - (audit: audio-editor)
- **[minor]** `web/feat/audio-edit.js:532-535, 480` — Stale selection: `ask()` and `save()` replace `E.cues` (AI list / server's tidied list) without resetting `E.sel`, so the highlight can land on a different chip (378: `i === E.sel`) and Delete/Backspace (786-793) then splices whatever now sits at that index - the wrong sound
  - Evidence: `E.sel` not reset at either replace site; splice uses the raw index at 787
  - Fix: Set `E.sel = -1` after replacing `E.cues` in `ask()` and `save()`
  - (audit: audio-editor)
- **[minor]** `web/feat/audio-edit.js:560` — Play-failure copy is false for un-kept sounds: "The browser would not play it. It is still fine when mixed in." - for a cue whose slug is not kept, `play/<slug>` answers 404 "That sound is not on this machine yet." (`studio/api_memesound.py:209-210`, proven with `play/bruh`) and mixing fails too (`cue_ok`)
  - Evidence: HTTP 404 body on `play/bruh`; message text at line 560
  - Fix: Say "The sound is not on this machine yet. Keep it first.", or HEAD-probe the play route first (the route advertises HEAD for exactly this, api_memesound.py:202-203)
  - (audit: audio-editor)
- **[minor]** web/feat/audio-edit.js:769 — Dead handler registration: act map key `"aed-keep"` exists but no `data-act="aed-keep"` is emitted anywhere in `web/` (76 feat files + index.html). The editor's remove button is `aed-take` (`:422`); `keep` is the audio-page naming (`alb-keep`, audio-page.js:328).
  - Evidence: Map key `"aed-keep"(btn){` at audio-edit.js:769; grep `data-act="aed-keep"` across `web/**/*.js` and `web/index.html` returns 0 emissions.
  - Fix: Delete the `"aed-keep"` key from the act map, or rename it to match an intended button if one was planned.
  - (audit: x-dead-handlers)
- **[usability]** `web/feat/audio-edit.js:224, 532-535` — "Ask the AI to place them" silently REPLACES every cue on the track with no confirm and no undo. The label reads as "add", and the backend is explicit that the saved list is the whole truth: "a cue missing from it is removed from the clip" (`studio/api_memesound.py:248`). A beginner with hand-placed sounds loses them on one press
  - Fix: Confirm before replacing when cues exist and are not all AI-sourced ("Replace the 3 sounds on the track with the AI's picks?"), or add AI cues alongside existing ones
  - (audit: audio-editor)
- **[usability]** `web/feat/audio-edit.js:786-793, 243` — The keyboard shortcut is undocumented: Delete/Backspace removes the selected chip, but neither the shelf hint (243) nor the empty-track text (370-372) mentions it
  - Fix: Extend the hint: "Drag one onto the track, press it and then press the track, or select a sound and press Delete."
  - (audit: audio-editor)
- **[usability]** `web/feat/audio-edit.js:228, 421` — Two play controls with different behavior and near-identical copy: "Hear it here" plays the clip from the first cue minus 1s (770-779); the per-cue "Play" plays only that sound and seeks the video (551-567)
  - Fix: Rename "Hear it here" to "Play the clip"; give both buttons title tooltips
  - (audit: audio-editor)
- **[usability]** `web/feat/audio-edit.js:827-837, 240` — Search-as-you-type does nothing: the `input` listener handles only the emptied case, so typing updates nothing until Find is pressed, while the placeholder "Search the catalogue" implies live search
  - Fix: Debounced `find()` on input, or reword the placeholder to "Type, then press Find"
  - (audit: audio-editor)

## studio/api_overlay.py

- **[critical]** `studio/api_overlay.py:130,173,217,295` — Sending an unparseable JSON body (or no body) to any of the four body-reading routes crashes with a plain-text 500 instead of a 400. The `isinstance(body, dict)` guards only catch parseable non-dict bodies.
  - Evidence: Measured: PUT `/api/overlays/templates` with `not json at all` -> 500 `Internal Server Error`; empty body -> 500; PUT clip overlay `{{{` -> 500; empty -> 500; POST preview `nope` -> 500; PUT job overlay-template `bad` -> 500; empty -> 500. JSON `null` body is handled (400), which proves the gap is exactly the parse step: `await request.json()` raises an unhandled `json.JSONDecodeError`.
  - Fix: Add one helper, e.g. `async def _obj(request) -> dict:` that reads the body, catches `ValueError`, and raises `HTTPException(400, "Send the layout as an object.")`, and use it at all four sites (templates save, clip overlay write, preview, job toggle).
  - (audit: api-overlays)
- **[important]** `studio/api_overlay.py:130` — `PUT /api/overlays/templates` answers **500 Internal Server Error** to an empty or malformed JSON body: `body = await request.json()` has no try/except, so the `JSONDecodeError` escapes as an unhandled exception. Every sibling JSON handler catches this exact case: `studio/api_brand.py:58-61` (ValueError → 400 "That brand could not be read."), `studio/api_trends.py:333-337` (empty body → graceful sentence), `studio/api_memesound.py` `_json()` helper (empty body on `/keep` → 400 "Which sound?").
  - Evidence: Live curl, twice: `curl -X PUT -H 'Content-Type: application/json' http://127.0.0.1:8798/api/overlays/templates` → `500 Internal Server Error` (m00128 probe + root-cause check). With a valid body the same route returns 200.
  - Fix: Wrap line 130 in `try/except ValueError` and raise `HTTPException(400, "Send the layout as an object.")`, reusing the copy already at line 132.
  - (audit: x-routes-live)
- **[minor]** `studio/api_overlay.py:303-305` (the `clips` loop of PUT `/api/jobs/{jid}/overlay-template`) — The every-clip toggle silently replaces a clip's own layout choice: every clip's `overlay_template` is overwritten when `clips` is true (the default). Only clips with their own pictures keep drawing them (items win in the drawing logic). The UI hint only promises "unless a clip was given its own pictures" (`web/feat/pictures-dialog.js:47`), so copy and behaviour agree — but the person is never told their per-clip layout was replaced.
  - Evidence: Code: `for clip in job.get("clips") or []: clip["overlay_template"] = tid` — unconditional. Measured E1b: the clip inherited the job template; E3 (`clips:false`) left the clip's own `tcfd67c` in place.
  - Fix: In the response note, say how many clips had their own layout and now wear this one (e.g. "3 clips had their own layout; they now draw X."), or skip clips whose `overlay_template` differs from the previous job-level value so a per-clip choice survives a toggle.
  - (audit: api-overlays)
- **[minor]** `studio/api_overlay.py:133-137` — The same route accepts an **empty `items` list** and stores a layout that draws nothing: it refuses non-empty-but-invalid lists ("None of those pictures are on the shelf…") but `{"items":[]}` passes through and returns 200 with `{"template":{"items":[]}}`. Not reachable from the UI — `web/feat/pictures.js:589` guards ("There is nothing to save yet. Add a picture first.").
  - Evidence: Live curl: `PUT /api/overlays/templates {"id":"","name":"qa-audit-probe","items":[]}` → `200 {"ok":true,"template":{"id":"tdb58d0","items":[]}}`; probe template deleted immediately after.
  - Fix: Treat a missing/empty `items` the same as the existing refusal, or document the empty layout as an intentional no-op.
  - (audit: x-routes-live)

## web/feat/grid.js

- **[critical]** web/feat/grid.js:141 (also 131-133) — The "This week" card is unreachable: it mounts into `#toolsec`, which no longer exists in the page
  - Evidence: Grep of `web/index.html` for `toolsec`: 0 matches. `toolsPage()` (index.html:2363-2372) draws hand-written markup and `loadTools()` is a no-op ("There is no generic plugin mount on this page", index.html:2375). So `tools()` markup never renders and `load()` never runs; `paint()` writes into `#pcgrid`, also absent
  - Fix: Add `<div id="toolsec"></div>` to `toolsPage()` and call `P.loadTools()` after it (index.html owner), or give grid.js a different mount. plugins.js:210 still documents the old contract
  - (audit: tools-schedule)
- **[minor]** web/feat/grid.js:108-112 — "Waiting to go out" shows the latest-due post first while the comment claims it mirrors the queue order
  - Evidence: grid.js:111 sorts descending (`b.due_at - a.due_at`); the queue it mirrors sorts ascending (studio/posting.py:273 `key=lambda p: p["due_at"]`). The top row is the post that will go out last
  - Fix: Sort ascending (`a.due_at - b.due_at`) and reword the comment, or keep descending and drop the "order the queue runs in" clause
  - (audit: tools-schedule)
- **[minor]** web/feat/grid.js:20, 93 — The zero-day bar (2px floor) is nearly invisible: --line-2 on --muted
  - Evidence: #2A2A2A (index.html:19) on #111111 (`.pcgrid .d` background, grid.js:13) = 1.33:1, below the 3:1 non-text minimum. The floor exists so an empty day still reads as a day (comment, line 92)
  - Fix: Use a measured lighter grey (one step above #2A2A2A), or give `.d.zero` a visible cue. Measure before committing
  - (audit: tools-schedule)

## web/feat/polish-errors.js

- **[critical]** web/feat/polish-errors.js:277 (`.pcerr .pcerr-btn:hover`) — Hover-only: white on the light red `--bad #F87171` hover background, 12px button label "Dismiss"
  - Evidence: Computed 2.77:1 while hovering (base transparent + `--bad` on `--bad-soft` = 6.25:1 is fine)
  - Fix: Hover to `--bad-soft` + keep `--bad` text, or darken the hover ground (`#C53030`-class, white = 5.6:1)
  - (audit: x-contrast)

## studio/server.py

- **[important]** `studio/server.py:707-712` (`_scrub`), served by `GET /api/jobs/{jid}` `log_tail` — Job logs leak personal filesystem paths: Python stdlib traceback frames reach the page with the Windows username and interpreter path intact. `_scrub` only replaces `DATA_DIR`/`ROOT`/temp-dir forms, so anything under `sys.prefix` passes verbatim — defeating the file's own rule (`studio/server.py:704`: a traceback names the folder the app runs in, "that is nobody's business but ours").
  - Evidence: Curl of the real error job returned e.g. `File "C:\Users\Asus\AppData\Local\Programs\Python\Python315\Lib\concurrent\futures\_base.py", line 454, in result` (4 such lines, lines 6/9/11/13 of the tail).
  - Fix: In `_log_roots()` also add the interpreter's own folders in both spellings: `sys.prefix`, `sys.exec_prefix`, `Path(sys.executable).parent`, and the stdlib dir (`Path(sys.executable).parent / "Lib"`), longest first like the existing roots. Stdlib frames then scrub to bare file names like repo frames already do.
  - (audit: api-jobs)
- **[important]** `studio/server.py:1090-1093` + `studio/jobs.py:441-443` — The render route surfaces raw Python exception text to the page when a clip time is not a number: `could not convert string to float: 'abc'` and `float() argument must be a string or a real number, not 'NoneType'`. A beginner cannot act on either message; every other bad-input answer on these routes is plain language.
  - Evidence: Curl: `POST /api/jobs/{jid}/clips/clip01/render` `{"start":"abc"}` → 400 `{"detail":"could not convert string to float: 'abc'"}`; `{"start":null}` → 400 `{"detail":"float() argument must be a string or a real number, not 'NoneType'"}`. Route only catches `ValueError/TypeError` and passes `str(e)` through (`studio/server.py:1092-1093`).
  - Fix: Wrap the time conversion in `request_render` (`studio/jobs.py:441-443`) in its own try that raises `ValueError("Times must be numbers, like 12.5.")`; the route already turns that into a 400. Keep `A clip can be 3 to 180 seconds long.` for the range check.
  - (audit: api-jobs)
- **[important]** `studio/server.py:121-122` cap vs `studio/overlay.py:29` (`MAX_BYTES = 12 * 1024 * 1024`) and `studio/api_overlay.py:76-78` — An ordinary real logo (1.0 MB) cannot be uploaded at all: the request gate cuts every non-`/api/upload` body at 256 KB and answers `That request is too large.` — no number, no guidance. The route's own 12 MB cap and its careful "shrink it and try again" message are unreachable, and the editor sends the file with no client-side size check, so the person only learns after the upload fails.
  - Evidence: Measured A10: 1,051,924-byte ordinary PNG -> 413 `{"detail":"That request is too large."}`; A9: 2,154-byte logo -> 200. Gate cap: `cap = ... else 256 * 1024` for any path other than `/api/upload` (`studio/server.py:120-122`). Frontend: `web/feat/pictures.js:494-513` posts `FormData` without a size check.
  - Fix: Either let `/api/overlays/upload` through the gate up to `overlay.MAX_BYTES` (as `/api/upload` is), or make the two caps agree and put the number in the gate message ("The limit is 256 KB."). Also add a client-side check against `file.size` with the same limit so the message appears before the upload.
  - (audit: api-overlays)
- **[important]** `studio/server.py:1489` (`_tr_public` ready), `:1576-1577` (`/api/transcribe/test` local branch) — Local transcription readiness is claimed without checking the model. The test route's local branch answers ok unconditionally, and `_tr_public` computes `ready = provider == "local" or (logfare and key)` — neither consults `transcribe.model_ready()` (`studio/transcribe.py:213-215` → `fetch_model.ready()`, a pure file-existence check that already exists). A green test and a green Ready pill on an install where every local transcription fails.
  - Evidence: This install has no local ASR model downloaded (`data/models` holds only `argos/` and `speech-model.tar.bz2`), yet: `PUT /api/transcribe {"provider":"local"}` then `POST /api/transcribe/test` → **200** `{"ok":true,"mode":"local","note":"Local sherpa-onnx is always ready when the model is downloaded."}` — the note's own wording admits the caveat the route never tests; `GET /api/transcribe` meanwhile reports `"ready":true`. Every local transcription on this state fails with the model missing. (Settings switched for the test and restored to `logfare`/`nova-3`, verified.)
  - Fix: In the local branch of `/api/transcribe/test`, include `transcribe.model_ready()` in the answer and return the "model not downloaded yet" guidance when it is False; in `_tr_public`, make `ready` for a local provider require `model_ready()` too, so the pill matches reality.
  - (audit: api-transcribe-ai)
- **[minor]** `studio/server.py:897` and `studio/server.py:978` — Upload rejection copy names 4 of the 7 allowed types: `Upload a video file (mp4, mov, mkv or webm).` while `VIDEO_TYPES` (`studio/server.py:48`) also accepts `.m4v`, `.ts`, `.flv`. A person holding one of those, who first tried a rejected file, is told an incomplete list.
  - Evidence: Line comparison `studio/server.py:48` vs `studio/server.py:897/978`; curl of a `.txt` upload returned the same sentence.
  - Fix: Say the whole list: `Upload a video file (mp4, mov, m4v, mkv, webm, ts or flv).` Both lines (simple upload and chunked start).
  - (audit: api-jobs)
- **[minor]** `studio/server.py:676` vs `studio/api_review.py:47`, `studio/api_preview.py:70,75` — The same missing job gets two different 404 sentences: `No such video` on `/api/jobs/{jid}` but `No such job.` on `/api/jobs/{jid}/review` and `/api/jobs/{jid}/peek`. Two names for one thing in errors a person (or the page) may show side by side.
  - Evidence: Curl: `GET /api/jobs/abc` → `No such video`; `GET /api/jobs/abc/review` → `No such job.`; `GET /api/jobs/abc/peek/clip01` → `No such job.`
  - Fix: Pick one word across all job routes (`No such video.` matches the page's own vocabulary) in `_job_or_404` in `server.py`, `api_review.py`, and `api_preview.py`.
  - (audit: api-jobs)
- **[minor]** `studio/server.py:900-904` — `POST /api/upload` silently swallows a malformed `options` form field (`json.loads` fails → `{}`). A page bug that sends broken options would make every upload quietly run with defaults, and nobody would ever see why.
  - Evidence: Code path read at `studio/server.py:900-904`; the chunked start route validates instead (`studio/server.py:989-993`), so the two upload paths disagree.
  - Fix: Log the ignored payload (`print(f"upload options ignored: {options[:200]}")`), or better, reject with 400 like `/api/upload/start` does, so both upload paths agree.
  - (audit: api-jobs)
- **[minor]** studio/server.py:1773 — Dead code: `body: dict = Body(default={}) or {}` — the `or {}` can never run because a `FieldInfo` default is truthy, so the expression is just `Body(default={})`. No behaviour impact; it suggests the author thought an absent body could arrive as `None`.
  - Evidence: Reading `studio/server.py:1772-1779`; FastAPI injects `{}` for an absent JSON body under `Body(default={})`.
  - Fix: Drop the `or {}` so the line reads `body: dict = Body(default={})`, or if the intent was None-safety, do it where it can fire: `body = body or {}` inside the function.
  - (audit: api-posting)

## web/feat/usage.js

- **[important]** web/feat/usage.js:220 — Wrong copy: "One model answers every call listed below" is a claim the data does not support. The sentence shows the current model, but call rows persist across provider switches, so older calls may have been answered by other services. In the empty state the same sentence sits directly above "No AI call has been made yet.", so nothing is listed below.
  - Evidence: usage.js:220 prints the sentence from the current model only (studio/usage.py:63 takes (ai.models() or [""])[0]); usage.forget_all() (studio/usage.py:39-41) clears only the _brief cache, and the same response computes by_creator from history (studio/usage.py:79-83, 96), which exists because several creators can appear in it.
  - Fix: Say what is true: "The service in use now answers new calls." Or render the by_creator split the route already sends.
  - (audit: apps-ai-usage)
- **[important]** web/feat/usage.js:35, 157-158 — The zero-token tick is invisible: a day the route reported as zero is drawn as a 2x1 px rect filled with --line-2, which measures 1.38:1 against the chart background, below the 3:1 WCAG 1.4.11 minimum for meaningful graphics. The tick's stated purpose, that the row of days must not read as a shorter week, cannot work at that contrast. The chart baseline uses the same pair.
  - Evidence: .usg-plot .none{fill:var(--line-2)} (usage.js:35) and .base{stroke:var(--line-2)} (usage.js:36); --line-2 is #2A2A2A and --bg is #0A0A0A (web/index.html:19). Ratio = (0.02316+0.05)/(0.00304+0.05) = 1.38. Tick is 2 px wide, 1 px tall (usage.js:158).
  - Fix: Fill the tick and stroke the base with a colour at 3:1 or better on --bg, measured: --faint #A0948C is 7.24:1, --dim #A3A3A3 is 8.10:1 (measured in polish-contrast.js:11-13).
  - (audit: apps-ai-usage)
- **[minor]** web/feat/usage.js:196 — Purposes beyond the 8 largest are dropped with no note. The server sends every purpose ordered by tokens; a person with 10 purposes sees 8 and the rest vanish silently.
  - Evidence: usage.js:196 got.slice(0, 8); studio/usage.py:76-78 sends all purposes with no cap.
  - Fix: After the rows, add a quiet line "and N smaller purposes" when got.length is greater than 8.
  - (audit: apps-ai-usage)
- **[minor]** web/feat/usage.js:121 — The exact token total is reachable only by hover: the visible figure is abbreviated and the exact count sits in a title attribute, which a touch screen cannot show.
  - Evidence: usage.js:121 puts exact(toks) in title; the visible value comes from tokens() (usage.js:86-88), which abbreviates anything over 10,000.
  - Fix: Move the exact count into the .usg-sub line: "12,345,678 exactly, read in and written out together".
  - (audit: apps-ai-usage)
- **[minor]** web/feat/usage.js:277 — The nav tooltip promises "and what it cost", but the page's central card answers the cost question with "Not known" and refuses to print a figure. A beginner who hovers the row expects a number the page will not give.
  - Evidence: usage.js:277 tip: "How much AI was used, and what it cost" against usage.js:125-127 ("Not known ... any figure printed here would be a guess").
  - Fix: Change the tip to "How much AI was used, in calls and tokens".
  - (audit: apps-ai-usage)
- **[minor]** web/feat/usage.js:216 — "Add one under AI in Settings" is advice a standard user cannot follow: /api/ai is admin-gated and the AI settings tab is owner-only, so with accounts on the link leads to a 403.
  - Evidence: usage.js:216; studio/server.py:1411 calls _admin(request) before returning ai.public(); menu-pages.js:51 marks the AI tab admin. menu-pages.js:90 already has the right phrasing: "Ask the owner of this PeakCut."
  - Fix: For non-admins say "Ask the owner to add one under AI in Settings."
  - (audit: apps-ai-usage)
- **[minor]** web/feat/usage.js:185 — The chart labels only the first and last of up to 30 days, and the per-bar dates live in hover-only title attributes, so on a touch screen the middle days carry no readable date at all.
  - Evidence: usage.js:185 draws exactly two axis spans for rows.length days; the dates are in rect title elements (usage.js:163).
  - Fix: Label every 5th day (or first, middle, last) in the .usg-axis row.
  - (audit: apps-ai-usage)
- **[minor]** web/feat/usage.js:4 — Stale pointer: the header comment cites studio/server.py:1374, but the route is at studio/server.py:1398.
  - Evidence: usage.js:4 vs studio/server.py:1398.
  - Fix: Update the comment to 1398.
  - (audit: apps-ai-usage)

## web/feat/formats.js

- **[important]** `web/feat/formats.js:298-305` — 12 of 45 look tiles render the motion descriptor as a duplicate of the label: "Comic / Comic", "Drop / Drop", "Duo / Duo", "Glow / Glow", "Hollow / Hollow", "Meme / Meme", "Punch / Punch", "Shake / Shake", "Slide / Slide", "Stamp / Stamp", "Sweep / Sweep", "Whisper / Whisper"
  - Evidence: `/api/captions/styles` returns `anim` equal to the label for those 12 looks (verified live); `tileHtml` prints `what = kind.charAt(0).toUpperCase()+kind.slice(1)` (`formats.js:299`) whenever `anim` is non-empty
  - Fix: In `tileHtml`, skip the descriptor when `kind.toLowerCase() === (x.label \|\| x.name).toLowerCase()`, or map motion names to words ("Bounce"→"Bounces in", "Glow"→"Glows")
  - (audit: formats)
- **[important]** `web/feat/formats.js:146,173,307` — The currently-default look is never marked: all 45 "Use as default" buttons render `aria-pressed="false"` / "Use as default" even for the look that *is* the default (beast right now). `lookPick`/`shapePick` are assigned and never read anywhere
  - Evidence: `/api/brand` returns `brand.style:"beast"` (verified live); `formats.js:307` hardcodes `aria-pressed="false"`; `formats.js:146`/`173` write the pick fields with no reader. Note the styles API's `default` is a hardcoded `"bounce"` (`api_style.py:69`), so it cannot be trusted either — `brand.style` is the authority the page itself saves to in `fmtuse`
  - Fix: In `load()`, also fetch `GET /api/brand` (already used by `fmtuse`) and mark the matching tile `aria-pressed="true"` + "Default for new clips"
  - (audit: formats)
- **[important]** `web/feat/formats.js:116,195-196,208-209` (+ dead CSS `:23-26`) — `needs_parts` is fetched and normalized into `needs` but never rendered. The comment says "the foot line says how many moments it joins", but `shapeCard` outputs only a heading and one line, and `.fmt-foot`/`.fmt-parts`/`.fmt-need` CSS is never used. A user choosing Callback or Compilation never learns it needs 2-3 clips
  - Evidence: `/api/formats` returns `needs_parts` (callback:2, compilation:3, escalation:3, thenvsnow:2 — verified live); `formats.js:116` computes `needs`; `shapeCard` (`:208-209`) emits no foot; CSS `:23-26` has no HTML producer
  - Fix: Render it in `shapeCard`, e.g. `<div class="fmt-foot"><span class="fmt-need">Joins N clips</span></div>` when `f.needs > 1`; or delete the dead CSS and correct the comment
  - (audit: formats)
- **[minor]** `web/feat/formats.js:83` — Dead helper `icon()` is defined and never called; it also references `ic`, which is not defined in this file (safe only because `typeof` guards it)
  - Evidence: grep: no call site for `icon(` in the file
  - Fix: Delete it
  - (audit: formats)
- **[minor]** `web/feat/formats.js:300` — Comment claims the frame is "shown at a ninth" — 270×480 is a quarter of 1080×1920
  - Evidence: 1080/270 = 4
  - Fix: Fix the comment to "a quarter"
  - (audit: formats)
- **[minor]** `web/feat/formats.js:470` vs `:478` — Nav row says "Clip formats" but the page h1 says "Caption styles"; the formats list itself sits collapsed inside a `<details>` at the bottom, so the two names never appear together and a beginner may think they landed wrong
  - Evidence: `P.page nav:"Clip formats"` (`:470`); `view()` h1 "Caption styles" (`:478`)
  - Fix: Align the names (nav "Caption styles", or h1 "Clip formats & caption styles")
  - (audit: formats)
- **[minor]** `web/feat/formats.js:41` — The "Still frame" badge is 9.5px — the smallest text on the page, below every other size used (11-15px)
  - Evidence: `.ftile .moving{font-size:9.5px;...}`
  - Fix: Raise to 11px like `.ftile-do` (contrast already passes at 5.69:1)
  - (audit: formats)
- **[minor]** `web/feat/formats.js:219-225` — Empty-state headline "Editing ideas could not be loaded." also shows when the server legitimately answered with an empty list; only the note below corrects it
  - Evidence: `paintShapes` uses one headline for both the empty and the error case; `note` carries `shapeWhy` only on error
  - Fix: Use "No editing ideas yet." when `!shapeWhy`
  - (audit: formats)

## web/feat/pictures.js

- **[important]** `web/feat/pictures.js:48-49,60-61,79` — The rotate and resize handles sit outside the picture bounds (turn handle 36px above the top edge, size handle 14px past the bottom-right corner) while the canvas clips at its box (`.pics-canvas{overflow:hidden}`). Any picture whose top edge is within ~36px of the canvas top — stickers and posters at the top: the common case — silently loses its rotate handle, and items near the bottom-right edge lose the size handle. `overflow:hidden` clips painting **and** pointer hit-testing, so a clipped handle cannot be clicked
  - Evidence: Canvas is 405px wide → 720px tall, so the top 36px is the top 5% of the frame. CSS lines cited; rotation remains possible via the slider, position via the inputs
  - Fix: Draw the handles inset within the picture bounds, or set `overflow:visible` on `.pics-canvas` and clip only the frame `img` (wrap the frame, not the handles)
  - (audit: pictures-editor)
- **[important]** `web/feat/pictures.js:112-114,332` — Re-opening the editor for the same clip shows stale state: `state()` resets `S` only when the clip id changes, and `load()` skips the overlay refetch when `active.ready` is already true. Leave via "Back to clip", change the layout in the clip dialog's Pictures pane (which PUTs `/api/jobs/{jid}/overlay-template` for all clips), reopen the editor → it draws the old items and the old `tplName` and previews the wrong template
  - Evidence: `load()` guard `if (active.jid && active.cid && !active.ready)`; `state()` reset compares only jid/cid; the dialog-pane PUT changes `clip.overlay_template` behind the editor's back
  - Fix: Drop the `!active.ready` guard so every page load refetches the clip overlay — it is one GET, and the base frame is already cached per `previewAt`
  - (audit: pictures-editor)
- **[important]** `web/feat/pictures.js:331,286-289` — A failed picture-library fetch is swallowed (`api("/api/overlays").catch(() => null)`) and the shelf then renders the empty-state text "No pictures yet. Add a logo or a poster and it stays here." — a network error is indistinguishable from an empty shelf, with no toast and no retry. The outer try/catch only toasts the clip-overlay await; the shelf promise is nulled on error
  - Evidence: `.catch(() => null)` at :331; `drawShelf()` empty branch at :286-289
  - Fix: Keep the rejection and render "The picture library could not be opened." in the grid with a Retry link (the page already has the retry pattern at :160/:573)
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures.js:210` vs `:132` — Once a picture is selected, the "On this clip" help line is replaced by the bare file name (e.g. "logo"), so the instruction disappears and a beginner may not connect the name to the selection; two different default texts also exist (body() ships "Select a picture to move or resize it.", `syncControls` rewrites it to "Choose or upload a picture from the library below.")
  - Evidence: `on.textContent = it ? pictureName(it.name) : ...` — textContent assignment, two literal strings
  - Fix: Keep an instruction with the name: `logo — drag it, or use the sliders below`
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures.js:156,574-579` — Layer ordering is one-way: only "Bring to front" exists, so a picture can never be lowered except by removing and re-adding it
  - Evidence: Single splice-to-end handler in `pics_nudgedown`; no send-to-back action anywhere
  - Fix: Add a "Send to back" button (splice to index 0) next to "Bring to front"
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures.js:141,143,152` — The size/rotation/opacity value `<output>`s are `aria-hidden="true"`, so a screen-reader user never hears the actual values, only native range announcements
  - Evidence: `aria-hidden="true"` on the three outputs
  - Fix: Drop `aria-hidden` and give each range an `aria-valuetext` (or announce via the output)
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures.js:89` — Thumbnail labels are 10px and clamp to one line — long names truncate to a sliver. Contrast passes (`#A0948C` on `--field` 6.24:1) but 10px is at the edge of legibility
  - Evidence: `.pics-thumb b{font-size:10px}`
  - Fix: 11-12px, keep the ellipsis
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures.js:147-148` — "Across (%)" / "Down (%)" are not beginner-obvious (they are the picture's x/y position inside the frame)
  - Evidence: Literal labels in the Precision details block
  - Fix: Rename to "Left-right (%)" / "Up-down (%)"
  - (audit: pictures-editor)

## web/feat/streamer-mode.js

- **[important]** web/feat/streamer-mode.js:487 (declared at 149) — "Recording now" section goes blank on every revisit after the first. paintResults builds `html`, then `if (html === lastLiveHtml) return;` quits before writing #str_live, #str_count and before paintCreators(). `lastLiveHtml` is never reset in load(), but the app rebuilds the page DOM fresh on every visit and re-render (web/plugins.js drawPage 124-141; web/index.html:2533), so the fresh empty #str_live is never filled when the job state has not changed. With zero recordings the html is constant, so after the first visit the section shows no rows, no "Nothing is being recorded right now." empty state and no count, indefinitely.
  - Evidence: streamer-mode.js:487 `if (html === lastLiveHtml) return;`; :149 `let lastLiveHtml = "";` (only 3 occurrences: declare, compare, set - no reset); web/index.html:2533 `return PeakCut.drawPage(S.view);` rebuilds the DOM per visit
  - Fix: Reset the cache when the page is rebuilt: at the top of load() set `lastLiveHtml = ""`, or paint unconditionally when `at("str_live")` has no children
  - (audit: streamer-live)
- **[important]** web/feat/streamer-mode.js:352-355 — Pressing the already-active mode card silently wipes every typed number. switchMode reads the draft, keeps only the URL (348), then `Object.assign(draft, START.live)` on the active-card branch. Clips, min/max length, style, minutes and hook words all revert to defaults with no message - the comment (356-357) says the feedback is the card unpressing and the summary line, but for the live card the mode stays "live", so nothing visible changes at all. The foot hint (606-607) invites exactly this press ("Press the mode that is on to turn it off again") without warning that typed numbers are lost.
  - Evidence: streamer-mode.js:352-355 `if (mode === k) { mode = "live"; Object.assign(draft, START.live); ... }`; readDraft at 347 commits the typed values just before they are discarded
  - Fix: Keep the typed draft on the active-card press (clear the mode without Object.assign), or reset only fields that differ from the mode's defaults, or say what changed; at minimum do not drop values the user typed
  - (audit: streamer-live)
- **[important]** web/feat/streamer-mode.js:303-305 — Hint under "Prefer moments with a police chase, a crash or a wanted level" is pure mechanism: "A note, not a filter. The job route has no field for it, so it is not sent, and PeakCut picks moments from what it hears the same way for every video." A beginner cannot parse "job route" or "not sent", and cannot tell what the tick actually does.
  - Evidence: File line: `303
  - Fix: <p class="hint">A note, not a filter. The job route has no field for it, so it is not sent, and PeakCut` | Rewrite in result terms: "This is a preference note, not a hard filter. PeakCut still picks moments by what it hears; after a clip is made it can use the note to label it a chase or a crash."
  - (audit: x-copy)
- **[important]** web/feat/streamer-mode.js:269-270 — The select "How loud chat must get" is changeable but does nothing, and the hint says so in mechanism language: "PeakCut does not read this for a job. A spike is decided by the Chat settings and by the creator's own 'only check on a spike' setting, so this box is not sent and changes nothing yet." A beginner sees a live-looking control and cannot tell why it exists.
  - Evidence: File line: `269
  - Fix: <p class="hint">PeakCut does not read this for a job. A spike is decided by the Chat settings and by the` | Lead with the result: "This box does nothing yet. Whether a chat spike counts is decided by the Chat settings and the creator's 'only check on a spike' setting." Better: disable the select (or hide it) until it is wired to the job.
  - (audit: x-copy)
- **[important]** web/feat/streamer-mode.js:274-277 — Same pattern under "Keep recording for at most, minutes": changeable number box that is never sent, plus a garbled label (the comma splits "at most" from its unit): "Keep recording for at most, minutes". Hint: "PeakCut does not read this for a job... so this box is not sent."
  - Evidence: File lines: `274
  - Fix: <label for="str_minutes">Keep recording for at most, minutes</label>` and `276 | <p class="hint">PeakCut does not read this for a job. How much of a stream a recording keeps is the` | Rename the label "Keep recording for at most (minutes)" and rewrite the hint: "This box does nothing yet. How much of a stream a recording keeps is set on that creator's Setup page."
  - (audit: x-copy)
- **[minor]** web/feat/streamer-mode.js:262-271 (str_chat), 272-278 (str_minutes) — Two dead controls: spike mode's "How loud chat must get" and catch mode's "Keep recording for at most, minutes" are never sent - the page's own hints admit "this box is not sent and changes nothing yet" (269-270) and "this box is not sent" (276-277). The hints do say so plainly, which is why this is minor, but a control that changes nothing is still a control a beginner will set and expect to work.
  - Evidence: streamer-mode.js:269-270 and 276-277 hint text; no readDraft consumption outside display
  - Fix: Remove both fields until a route reads them, or make the routes read them
  - (audit: streamer-live)
- **[minor]** web/feat/streamer-mode.js:686 — "Save these words to my brand" silently truncates: `.trim().slice(0, 120)` cuts typed hook words to 120 characters, and the success toast ("Saved. Every new clip will be told to look for those words.") never mentions the cut. A user typing 200 characters saves 80 without knowing.
  - Evidence: streamer-mode.js:686 `String((box && box.value)
  - Fix: | "").trim().slice(0, 120)`; toast at 696 | Trim to the limit in the input itself (maxlength=120 on #str_hooks), or say in the toast when words were dropped
  - (audit: streamer-live)
- **[minor]** web/feat/streamer-mode.js:661-665 — The 2.5 s results timer is never cleared. load() sets `setInterval` on every visit and stores it on `paintResults.timer` without clearing the previous one, so each visit to the page stacks one more interval. The guard `at("str_live")` makes off-page ticks no-ops, so the cost is small, but the number of live timers grows with every visit for the whole tab session.
  - Evidence: streamer-mode.js:661-665 interval assignment with no clearInterval anywhere in the file
  - Fix: `clearInterval(paintResults.timer)` at the top of load() before setting a new one
  - (audit: streamer-live)

## studio/api_analytics.py

- **[important]** studio/api_analytics.py:120-130 with studio/posting.py:277 — The local (no-YouTube) fallback covers only the last 14 days whatever window was asked; the response still echoes the full window, so wide presets show 14-day numbers labelled as 90-day/365-day/lifetime
  - Evidence: Measured: `GET /api/analytics/timeseries?metric=views&days=90` → `{"days":90,"start":"2026-08-25","end":"2026-11-22"}` with **14 rows**, first point "2026-11-09". Code: `_own` sums `posting.overview()["daily"]`, which is at most 14 entries
  - Fix: When `days` exceeds what the daily graph holds, clamp `start` to the first day with data and add a note sentence ("PeakCut's own records cover the last 14 days; connect a channel for longer ranges")
  - (audit: api-analytics)
- **[important]** studio/api_analytics.py:289 vs studio/posting.py:275 — The videos local branch reads `p.get("account_name")`, a field overview rows never carry (they carry `creator_name`), so the account column is always ""
  - Evidence: `"account": p.get("account_name") or ""` at studio/api_analytics.py:289; overview builds `"creator_name": names.get(p["creator"], "")` at studio/posting.py:275
  - Fix: Read `p.get("creator_name")`
  - (audit: api-analytics)
- **[important]** studio/api_analytics.py:280-292 — The videos local branch ignores `days` entirely: rows come from all posts (queue + last 15 done) with no date filter while the response echoes the requested start/end/days
  - Evidence: The loop `for p in o.get("posts") or []` has no date test; the same return claims `"days": days, "start": start, "end": end`. Not live-provable on this install (0 posts)
  - Fix: Filter rows by the post's date inside the window, or say in the note that the local list is not date bound
  - (audit: api-analytics)
- **[important]** studio/api_analytics.py:334-369 — The audience route swallows every sub-query failure (`except: pass` at lines 344, 349, 356, 366) and line 368 unconditionally sets the success note; with a token whose every query fails the page gets source "youtube", empty lists, and a note that says the numbers are YouTube's
  - Evidence: studio/api_analytics.py:340-367 (four try/except pass), studio/api_analytics.py:368 `out["note"] = "YouTube's own numbers. Hours are in your channel's own time zone."` — set whether or not anything arrived
  - Fix: Track whether any query succeeded; when none did, answer with the failure sentence (ytstats.explain(e)) and keep source honest instead of the success note
  - (audit: api-analytics)
- **[important]** studio/api_analytics.py:251-256 — The timeseries local fallback answers daily **clip counts** for every metric except views: metric=watch_time/likes/subscribers/… returns clip counts under the requested metric name, so the Watch time chart plots clips
  - Evidence: Measured: `GET /api/analytics/timeseries?metric=watch_time&days=7` → values 0,0,0,1,3,0,1 (the clips made those days), `"metric":"watch_time"`, `"unit":"clips"`. Line 252: `"value": d.get("views") if name == "views" else d.get("clips")`. The charts feature requests estimatedMinutesWatched first and falls back to watch_time (web/feat/analytics-charts.js:58, 206-210)
  - Fix: When the local data cannot answer the metric, return empty rows and a note that says the metric needs a YouTube connection — never clip counts under another metric's name
  - (audit: api-analytics)
- **[important]** studio/api_analytics.py:210-211 (same computation at 228) — The "Subscribers gained" card value is `subscribersGained - subscribersLost` (net) while the label says "gained"; when subscribersLost > 0 the card understates gains
  - Evidence: `"value": int(_num(r.get("subscribersGained")) - _num(r.get("subscribersLost")))` next to `"label": "Subscribers gained"`
  - Fix: Label it "Subscribers (net)", or report subscribersGained alone
  - (audit: api-analytics)
- **[important]** studio/api_analytics.py:260, 296, 419 vs 200 — timeseries, videos and retention surface a YouTube failure as `HTTPException(400, str(e))` — Google's raw response text — while summary uses `ytstats.explain(e)`, the words the owner can act on; one failure class, two different messages
  - Evidence: studio/api_analytics.py:260, 296, 419 (`raise HTTPException(400, str(e))`); studio/api_analytics.py:200 uses `ytstats.explain(e)`; the helper exists at studio/ytstats.py:122-138
  - Fix: Use `ytstats.explain(e)` in all four routes
  - (audit: api-analytics)

## web/feat/creators.js

- **[important]** `web/feat/creators.js:162` (pill painted here; rule lives in `web/index.html:258`) — The "Recording" pill fails WCAG AA: white text on the live red at 3.76:1, below the 4.5:1 required for 12px text. It is the page's only live-status indicator, shown on every card of a creator that is recording.
  - Evidence: `.pill.live{color:#fff;background:var(--live)}` (`web/index.html:258`), `--live:#EF4444` (`web/index.html:21`); measured #FFFFFF on #EF4444 = 3.76 (script `docs/qa/audit/_contrast_creators.py`); 12px semibold is not big text, so 4.5 applies.
  - Fix: In `web/index.html:258` draw the dark ink on the red, the same fix the bell unread count got (pattern documented in `web/feat/polish-contrast.js:17-19`): `--brand-ink` measures **5.10:1** on `#EF4444`.
  - (audit: creators)
- **[minor]** `web/feat/creators.js:276` — The creator count line (`#cr_count`) uses class `hint`, and `web/index.html:836` hides every `.hint` at ≤560px — so the count never shows on phones. A count is data, not a hint.
  - Evidence: `<p class="hint" id="cr_count"></p>` (`creators.js:276`); `.hint{display:none}` inside the ≤560px media block (`web/index.html:836`).
  - Fix: Give the count its own class (e.g. `class="cr-count"` with `.cr-count{font-size:12px;color:var(--faint)}` in the file's CSS) so it survives the mobile hint hiding. The two explanatory hints in `paintEmpty` (`creators.js:186-191`) collapse on phones too — acceptable, but the count is a real loss.
  - (audit: creators)
- **[minor]** `web/feat/creators.js:136` — When two or more of a creator's accounts are gone, the same sentence is drawn once per missing account: "one account is no longer connected one account is no longer connected".
  - Evidence: Each missing id renders `<span class="cr-miss">one account is no longer connected</span>` (`creators.js:136`); the ids are joined into `.cr-chans` at line 141.
  - Fix: Aggregate before drawing: count the missing ids and render one line "N accounts are no longer connected".
  - (audit: creators)
- **[minor]** `web/feat/creators.js:50,53` — Dead CSS: `.cr-chip.txt` is defined twice and no markup draws that class (chips use `cr-chip` and `cr-chip main` only).
  - Evidence: Rules at `creators.js:50` and `creators.js:53`; grep of the file finds no `class="cr-chip txt"` and no other use.
  - Fix: Delete both rules.
  - (audit: creators)
- **[minor]** `web/feat/creators.js:144-148,171` — The Track row is permanently "Not set" on every card: the backend never stores a track, so the row is dead weight on every card, and the only explanation of what a track is sits in the page footer below the cards.
  - Evidence: `trackLine` renders "Not set" whenever `c.track` is missing; `DEFAULTS` has no `track` key (`studio/creators.py:17-23`), `_clean` copies only DEFAULTS keys (`studio/creators.py:56`), and a repo-wide grep for `"track"` in `studio/*.py` returns 0 matches. The footer discloses it (`creators.js:280-282`).
  - Fix: Render the row only when the server actually sends `c.track`, and drop the now-unneeded footer sentence — the card stays honest without a permanently empty row.
  - (audit: creators)
- **[minor]** `web/feat/creators.js:133` — Usability: "No accounts picked, so nothing is posted for them" — a beginner does not know where accounts get "picked", and the copy does not point at the Setup button directly beneath it.
  - Evidence: Copy at `creators.js:133`; the card's Setup button is at `creators.js:175`.
  - Fix: Rename to "No accounts connected yet - clips are not posted anywhere until you add one in Setup."
  - (audit: creators)

## web/feat/menu-pages.js

- **[important]** web/feat/menu-pages.js:205, 223 — Dead admin key: the ai and storage page registrations pass admin: true, but nothing reads it, so non-owner users see "AI" and "Storage" menu rows that end in the "Owner only" card - a dead end. Settings itself hides Storage from non-admins, so the menu and Settings disagree.
  - Evidence: menu-pages.js:205 and 223 set admin: true; the nav drawer reads only p.hidden (web/plugins.js:85) - no p.admin anywhere in web/. Settings gates storage on is_admin (web/index.html:2242). With PEAKCUT_ACCOUNTS=1 a standard user lands on the owner-only card (menu-pages.js:87-93).
  - Fix: Have the nav drawer skip rows where p.admin is set and the signed-in user is not an owner (one check beside plugins.js:85), or drop the dead key and document that the fallback only fires after the click.
  - (audit: apps-ai-usage)
- **[important]** web/feat/menu-pages.js:44 — Usability: "Each creator picks its own accounts in that creator's Setup." Nothing on the Connected apps page is called a creator; the page shows YouTube, Instagram, TikTok and Zernio cards. A beginner cannot connect the sentence to anything on the page in five seconds.
  - Evidence: menu-pages.js:44; the drawn page content is the four app cards (web/index.html:2678-2682). "Creator" is PeakCut-internal vocabulary (channel identities) that this page never introduces.
  - Fix: Name the object: "Then pick which accounts each channel posts to, in that channel's Setup on the Creators page."
  - (audit: apps-ai-usage)
- **[minor]** web/feat/menu-pages.js:127 — Stale, dead metadata: tabs lists four pages but the file registers seven (brand, transcribe, tools, apps, ai, storage, account); the tabs key is consumed nowhere in web/, the about line is equally stale, and the cta values in the MOVED table are never read (the fallback uses d.where).
  - Evidence: menu-pages.js:127 tabs and about; grep over web/ finds only the unrelated .tabs CSS class (web/index.html:244); the fallback builds its link from d.where (menu-pages.js:98), never d.cta.
  - Fix: Update the list to the seven pages, or drop the dead tabs key and the unused cta fields so the metadata matches what the file registers.
  - (audit: apps-ai-usage)
- **[minor]** web/feat/menu-pages.js:8, web/feat/usage.js:12 — Sibling pages disagree on width: every menu settings page is capped at 780px while the Usage page is capped at 880px, so pages in the same family change width when you move between them.
  - Evidence: menu-pages.js:8 .pcpg{max-width:780px} against usage.js:12 .usg{max-width:880px}.
  - Fix: Pick one width for the settings-family pages, measured against the same container.
  - (audit: apps-ai-usage)
- **[minor]** `web/feat/menu-pages.js` + `menu.js:74-77` + `menu-icons.js:37/55` + `polish-empty.js:39` + `polish-loading.js:54` — Cross-file helper load-order fragility (convention note, no runtime error today): helpers defined in one feat file are called from another; safety depends on alphabetical `/assets/feat` load order staying favourable
  - Evidence: menu-pages.js calls `P.menuGroup`/`P.icon` defined in menu.js and menu-icons.js, which sort earlier (menu-icons.js < menu-pages.js < menu.js). Verified safe today: helpers are only called at boot, never at module scope (grep of module-scope cross-file calls → 0 hits)
  - Fix: Keep the convention: cross-file helpers may only be called at boot/load, never at module scope; or move the shared helpers (`P.icon`, `P.menuGroup`, `P.empty`, `P.loading`) into `web/plugins.js` so order stops mattering
  - (audit: x-console-risks)

## studio/api_preview.py

- **[important]** `studio/api_preview.py` — GET /api/schedule/preview — An invalid clock is answered with internally inconsistent JSON: `preview` says `/ST 09:00` (the normalized default) while `times` echoes the raw input, so the answer claims 25:99 was scheduled
  - Evidence: `GET /api/schedule/preview?times=25%3A99` → `{"ok":true, "preview":"... /ST 09:00 /F\n", "times":["25:99"], "note":"Copy this and run it yourself..."}`
  - Fix: Echo the clock the preview actually used, or answer `ok:false` with a note that the clock was replaced
  - (audit: api-formats-schedule)
- **[important]** `studio/api_preview.py` — GET /api/schedule/preview — When the platform is unknown the answer is `ok:false` with a good error preview, but the note still tells the person to run it
  - Evidence: `GET /api/schedule/preview?times=09:00&os=banana` → `ok:false`, preview `# unknown platform 'banana', use windows, macos or linux`, note `Copy this and run it yourself. PeakCut does not touch your scheduler.`
  - Fix: When `ok` is false, the note should say the plan could not be made and what to change
  - (audit: api-formats-schedule)
- **[important]** `studio/api_preview.py:135-141` — GET /api/hunt/watching — Every exception is swallowed and the answer is `{"watching":[]}`, identical to a genuine empty answer. The page has an error path for this route that can never fire, so a crashed watcher reads as "you watch nothing"
  - Evidence: Route body catches all exceptions and returns `{"watching":[]}` (lines 138-141); `web/feat/live.js:200-206` maps a failed read to `rows=[]` plus an error sentence
  - Fix: Answer `ok:false` with an error sentence on exception, so the page's existing handler works
  - (audit: api-formats-schedule)
- **[minor]** `studio/api_preview.py:54-56` — The built-in fallback for an unknown channel is unreachable in the live path and disagrees with the shape it would shadow: it lacks `tone`/`can_clip`/`blocked` and says label "Unknown" with a full note
  - Evidence: `GET /api/rules` (no params) → label `Rules unknown`, empty `note`, `tone`/`can_clip`/`blocked` present — the live path goes through `rules.badge` (`studio/rules.py:201`)
  - Fix: Point the fallback at `badge` or give it the same keys
  - (audit: api-formats-schedule)

## web/feat/analytics-table.js

- **[important]** `web/feat/analytics-table.js:76` — The Content tab **never inherits the page's date range**. `const g = r.range
  - Evidence: | r` grabs `window.PeakCutAnalytics.range`, which is a *function* (`web/feat/analytics.js:79-87`); a truthy function passes `\
  - Fix: \|`, so `g.start/g.end/g.days` are undefined → span 0, `Number(g.days)` = NaN → `asked()` always returns the module default 28. The sibling files call the getter (`analytics-compare.js:95`, `analytics-kpi.js:94`); the table never does, so the inheritance code and its comments (`:71-73`, `:165-172`, `:283-284`) are dead. `pick=true` after any table pick (`:264-265`) then disables the (already dead) path forever. | Page range 90 → header says "Last 90 days", table picker says "Last 28 days", fetch is `?days=28`. | `const g = (typeof r.range === "function" ? r.range() : r.range) || r;` (mirror `val()`), or read the plain values `head()`→`agree()` already publishes on the shell object; optionally map Lifetime → `days=0` (server: 0 = the 3650-day lifetime span, `studio/api_analytics.py:37`) instead of capping at `MOST`.
  - (audit: insights-content)
- **[important]** `web/feat/analytics-table.js:111-112`, `:144` — The **Impressions and Click-through columns can never show a number**: `normalize()` maps `imp`/`ctr` from keys the server never sends (`studio/api_analytics.py:309-320` row keys; `_VIDEO_COLS :50-51` never asks YouTube for them). Every row renders "–" in both columns with tooltip "This video did not report this number." — wrong copy: it blames the video when the app never asks for the metrics. 2 of 11 columns are permanent dead weight. Related dead code: `r.short` reads `is_short/short/format` (`:152`) — none sent → the "Short" badge (`.ant-short :32`) never renders and the short-specific tooltip (`:142-143`) is unreachable; the server does send `seconds` (`:313`), so a Short is detectable by duration.
  - Evidence: `ops_grep` row keys vs `normalize()` key lists — zero overlap for imp/ctr/short.
  - Fix: Drop the two columns (or fetch the metrics server-side); rewrite the tooltip ("PeakCut does not fetch impressions for videos"); wire the Short badge from `seconds <= 60` or remove it.
  - (audit: insights-content)
- **[minor]** `web/feat/analytics-table.js:41`, `:238` — **Stale cache after publishing**: `CACHE` is a Map keyed by `days` with no TTL or invalidation; `mount()` early-returns when the frame exists (`:277`), and `analytics.js` `reload()` (:164-174) wipes the box then `ask()` hits the cache and repaints old rows without any request. The Content tab keeps the old count until a full reload or a picker change.
  - Evidence: Cache key set at `:238`, only deleted by the error retry.
  - Fix: Delete the days-key on `peakcut:render`, give the cache a short TTL, or have `reload()` force a re-ask.
  - (audit: insights-content)
- **[minor]** `web/feat/analytics-table.js:238` — **Silently truncated list**: the table fetches only `?days=N`, the route's `limit` defaults to 100 (`studio/api_analytics.py:273`, cap 200), and the table ignores `data.total`, labelling `list.length` as the full count. A channel with >100 videos in the window sees "100 videos" with no truncation notice. (Server `total` is itself unreliable: own-case pre-limit `len(rows)` :291, YouTube-case post-limit `len(out)` :322.)
  - Evidence: Fetch string `:238`; count built from `list.length` in `paint()`.
  - Fix: Request `limit=200` and print "X of Y videos" when `total` exceeds the rows.
  - (audit: insights-content)

## web/feat/sounds.js

- **[important]** web/feat/sounds.js:247 — The description under every Meme noises row is a bare visual-gag keyword, not a sound description: all 9 meme rows show "freeze", "push-in", "shake" or "vignette", and the page's own curated sound descriptions (`BY_NAME`, "A trombone, or someone saying hello into a dark room." etc.) are unreachable. A beginner cannot tell what the sound is like from the page.
  - Evidence: sounds.js:247 `if (row.note) return row.note;` prefers the server note; studio/api_sound.py:51 `_note` reads keys `("hint","note","label","effect","treatment")` and the mood documents only carry `"treatment"` (studio/meme.py:33,46-62), which is the visual gag applied to the clip (meme.py:1); live `/api/moods` confirms: 9 meme rows with keyword notes, 4 music rows with real sentences.
  - Fix: In `about(row)`, only prefer `row.note` when it reads like a sentence (e.g. contains a space); otherwise fall through to `BY_NAME`. The root cause is `_note()` treating the clip's visual treatment as a mood description - that key list fix belongs to the fix wave (api_sound.py is not this auditor's file).
  - (audit: sounds)
- **[important]** web/feat/sounds.js:394-400 — The "stop the sound when you leave the page" listener listens for `hashchange`, but the app navigates with `history.pushState` and never changes the hash, so the listener is dead code: a sound left playing keeps sounding under every page you switch to, with no Stop control there. The page's own comment claims this case is handled.
  - Evidence: sounds.js:396 `String(location.hash
  - Fix: | "").indexOf("/app/sounds")` on a `hashchange` event; index.html:1444 `remember()` navigates via `history.pushState({v, tab}, "", url)`, and no code in index.html sets `location.hash` (grep found none). `go()` stops the live stream (`window._gaStop`, index.html:1469) but has no hook a feature page can use. | Check the state the app actually changes: pause when `PeakCut.state().view !== "sounds"` (a small interval or a `popstate` listener plus a view-change event from `go()`), or simplest, keep a 250 ms check like plugins.js's own repaint loop.
  - (audit: sounds)
- **[important]** web/feat/sounds.js:296-297 — Empty-catalogue state names Python source files to the end user: "The server answered, and the list of moods was empty, so there is nothing to show yet." + "That list is written by studio/meme.py and studio/music.py. If it stays empty, the server log names the one that failed." A beginner does not know what a .py file is or where a server log lives.
  - Evidence: File line: `297
  - Fix: <p class="hint">That list is written by studio/meme.py and studio/music.py. If it stays empty, the server log names the one that failed.</p>` | "These sounds come with PeakCut and are built on first start. If the list stays empty, the build failed — press Build sounds again; the app's log file, in PeakCut's own folder, names what went wrong."
  - (audit: x-copy)
- **[minor]** web/feat/sounds.js:290-291 — Error state says "the server log says why" with no pointer to where that is.
  - Evidence: File line: `291
  - Fix: <p class="hint">This list comes from the server. Reload the page; if it stays empty, the server log says why.</p>` | "Reload the page. If it stays empty, the app's log file — in PeakCut's own folder — says why."
  - (audit: x-copy)
- **[usability]** web/feat/sounds.js:69,280,369 with web/index.html:836 — On a phone (viewport 560px or less) every explanatory hint on the Sounds page is hidden by the global mobile rule `.hint{display:none}`: both section subtitles ("A short gag laid over the clip: a horn, a rimshot, a room going quiet." / "A looped bed mixed under the voice, one for each mood.") and the Build button's "pressing it twice costs nothing" reassurance vanish, leaving a bare "Build the missing sounds" button with no explanation of what it builds or that it is safe to press.
  - Fix: Add to the sounds CSS block: `@media (max-width:560px){.snd .hint{display:block}}`. Specificity (`.snd .hint`, 0-2-0) outranks the global rule (`.hint`, 0-1-0), so no `!important` is needed and no other page is touched.
  - (audit: sounds)
- **[usability]** web/feat/sounds.js:254-265 — The quiet line under every row repeats the pill beside it: on this install all 13 rows render "Ready to play." under a green "Ready" pill (on a fresh install, "Not built yet. Use the button below this list to make it." would stack once per not-built row), so the same sentence runs 13 times down the page.
  - Fix: Start the say-line empty - the pill already carries the state, and `aria-live="polite"` still announces the line when Play or an error fills it later. Keep the per-row guidance only where it teaches something the pill cannot (e.g. only while nothing is built at all).
  - (audit: sounds)

## web/feat/history.js

- **[important]** `web/feat/history.js:102-106`, `:148`, `:153-171` + `web/index.html:2949` — Two "Versions" sections show at once in the clip dialog. The plugin's `takeSlot()` only hides the page's own strip when called with `mine` truthy, but its **sole call site passes `false`** and the `paint()` success path never calls it at all — so `#dlgvers` is never hidden while the plugin chips show. `drawHist()` then un-hides `#dlgvers` and writes its own pill strip, and the plugin appends its chip block right after it.
  - Evidence: `history.js:102-106` (`if (mine) slot.hidden = true;` with sole call `takeSlot(box, false)` at `:148`); `history.js:153-171` (success path, no `takeSlot`); `web/index.html:2949` (`box.hidden = false` + pill buttons); `web/plugins.js:191` (`watch("#clipdlg","drawClipDlg")` fires the hook). Reachable on any clip with ≥2 versions: both `loadHist()` (page) and the plugin's `load()` fetch the same endpoint, so both strips get data. Two sets of pin controls with different wording ("Click one to pin it as the keeper" vs "Press one to keep it") — exactly the duplication the file's own header (`history.js:98-101`) claims to prevent. Side note: the history endpoint is fetched twice per dialog open.
  - Fix: In `paint()`'s success path, call `takeSlot(box, true)` once the block is inserted; make `takeSlot(box, false)` restore the slot (`slot.hidden = false`) so the stand-down handback is real. This also makes the double-fetch harmless (one strip wins the slot).
  - (audit: review)
- **[minor]** `web/feat/history.js:32`, `:127-129` — Struck-through "gone" chips — a version that is no longer on disk — are still clickable and pin a file that no longer exists; the success toast ("Pinned version N") never mentions it.
  - Evidence: `history.js:32` (`.pchist .pchip.gone{opacity:.6;text-decoration:line-through}` — visual language of "unavailable"); `history.js:127-129` (gone chips rendered without `disabled`); `studio/api_history.py:203-206` (PATCH accepts any remembered version number, including ones with `exists:false`).
  - Fix: In `block()`, render chips with `v.exists === false` as `disabled` — the tooltip already says "no longer on disk".
  - (audit: review)
- **[minor]** `web/feat/history.js:183-184`, `:192` — Two silent catches in the history panel. The load catch is documented by-design for an optional route; the reread catch silently keeps stale page data after a successful pin.
  - Evidence: `history.js:183-184` `catch { DEAD.add(k); }` — a failed history read is remembered with no user-visible trace (comment: "no history route on this job, or the server said no"); `history.js:192` `try { fresh = await P.api(…) } catch { return; }` — after a successful pin, a failed read-back leaves the page one step behind with no words.
  - Fix: On reread failure, say one line ("The clip could not be read back; the page may be one step behind"). The DEAD dedupe is by-design and acceptable for an optional route.
  - (audit: x-states)

## studio/api_sound.py

- **[important]** `studio/api_sound.py:146` (via `_meme_file:99`) — A wrong mood name in the meme branch gets a message that blames the build step: banana is not a mood, so building can never make it. The music branch's message is correct
  - Evidence: `GET /api/sounds/meme/banana` → 404 `The banana sound has not been made yet. Build the sounds first.`; `GET /api/sounds/music/banana` → 404 `There is no music bed called banana.`
  - Fix: Mirror the music wording, e.g. "There is no meme noise called banana."
  - (audit: api-formats-schedule)
- **[important]** `studio/api_sound.py:46` (`_note`) → `web/feat/sounds.js:246-250`, `web/feat/mood.js:97-99` — Meme rows carry a bare visual-treatment word as their description (`"freeze"`, `"push-in"`, `"shake"`, `"vignette"`), and both consumers prefer the server note over their own plain sentences, so the Sounds page describes hype as just "shake"
  - Evidence: `GET /api/moods` → `{"name":"hype","kind":"meme","note":"shake"}` next to `{"name":"hype","kind":"music","note":"fast and loud: a big play, a win, a run"}`; `sounds.js` `about()` returns `row.note` first; `mood.js:97` pushes `row.note` first. The page's own copy says hype is "An airhorn, then a bass drop. The loudest pair here." (`sounds.js:52`)
  - Fix: Send a plain sentence from the server (meme.py has no hint; its `effect` is a list so `_note` falls through to `treatment`), or let `BY_NAME` win when the note is a single treatment word
  - (audit: api-formats-schedule)

## studio/api_learnreport.py

- **[important]** studio/api_learnreport.py:50-53 — `/api/learn/report` reads `learn.log()`'s **newest-first** list as if it were oldest-first: `rounds[-take:]` selects the **oldest** `take` rounds, `rows.reverse()` then outputs them **oldest-first**, and `prev = rounds[i-1]` hands `learn_report.shape()` a **newer** round where its contract says "the round before it" (learn_report.py:171-176), so a record lacking `moved` gets a comparison that runs backwards in time against the wrong pair.
  - Evidence: Live: `GET /api/learn/report` → `rounds[0].at=1795128089.73 < rounds[1].at=1795200008.31` while `GET /api/learn/state` returns newest-first (1795200008 first); `?limit=1` returned the round with at=1795128089 (the oldest of two), not the newest. Code: studio/learn.py:95 (`list(reversed(data["rounds"]))`).
  - Fix: Iterate `rounds[:take]` (newest-first), pair each raw with the **next** slice entry as `previous` (None for the last), and drop the final `rows.reverse()`; or reverse the list once where `learn.log()` builds it and keep the current pairing.
  - (audit: api-learn)
- **[important]** studio/api_learnreport.py:57 — The `table` in the same response ignores `limit` and is ordered newest-first while `rounds` is oldest-first — one response carrying two contradictory orderings.
  - Evidence: Live default response: `table.rows[0]="1 days 13 h ago"` (the newer round, at=1795200008) while `rounds[0].at=1795128089` (the older one); with `?limit=1`, `count:1` but `table.rows` still holds both rounds.
  - Fix: Build `table` from the same take-limited, ordered slice used for `rows`, so one response has one order.
  - (audit: api-learn)
- **[usability]** studio/api_learnreport.py:50-53 (covered above) — The report the operator reads draws the **oldest** rounds and oldest-first — the history contradicts every other list on the Improve page.
  - Fix: Same fix as finding 1.
  - (audit: api-learn)

## studio/api_hooks.py

- **[important]** studio/api_hooks.py:44-52 and studio/api_learnreport.py:39-46 — A malformed `limit` query is refused by the framework as a raw English FastAPI validation body **before the handler runs**, so both handlers' own bad-limit fallbacks (`int(limit)` try/except) are unreachable dead code. Sibling route `/api/learn/signals` deliberately takes `days`/`seconds` as str params for exactly this reason and documents it (studio/api_learn.py:195-197) — these two routes did not follow the pattern.
  - Evidence: Live: `GET /api/learn/hooks?limit=banana` → 422 `{"detail":[{"type":"int_parsing","loc":["query","limit"],"msg":"Input should be a valid integer..."}]}`; `GET /api/learn/report?limit=banana` → 422. Both handlers keep a quiet fallback that can never fire.
  - Fix: Declare `limit: str = "40"` (hooks) / `limit: str = "20"` (report) and coerce with the existing try/except, matching `/api/learn/signals`.
  - (audit: api-learn)
- **[minor]** studio/api_hooks.py:75-76 — The comment says "a broken job folder must not take the page down", but the handler raises `HTTPException(500, ...)` — the page does get an error. Either behavior is defensible; the comment contradicts the code.
  - Evidence: studio/api_hooks.py:75-76.
  - Fix: Return `{"ok": false, "hooks": [], "note": "The clips could not be read: ..."}` (200) to match the comment, or fix the comment to say the page gets a friendly 500.
  - (audit: api-learn)

## studio/ai.py

- **[important]** `studio/ai.py:276-288` (`explain`), reached from `list_models` `:222-257` via `/api/ai/models` (`studio/server.py:1429-1440`) — The "Find models" error names the WRONG service: it always says Logfare, because `explain()` builds its message from `where()`/`models()`, which read the CURRENT saved dashboard config, not the provider/address the request actually tested. This breaks the rule `ai.where()` itself documents ("a person who pointed PeakCut at their own server needs to see that address in an error").
  - Evidence: Live: `POST /api/ai/models {"provider":"custom","base_url":"http://127.0.0.1:9/v1","key":"x"}` → **502** "…PeakCut couldn't reach **Logfare**. Check the address and the internet connection." (nothing was sent to Logfare); `{"provider":"openai","key":"sk-bogus-openai-key-123"}` → **502** "…**Logfare** refused the key. Paste a working key under Settings, AI." (it was OpenAI that refused); `{"provider":"ollama"}` (Ollama not running) → **502** "…couldn't reach **Logfare**". A person who pastes their own address reads a message about a service they never chose, and the "under Settings, AI" pointer lands on the wrong key field.
  - Fix: Give `explain()` an optional `(provider_id, address)` override, and have `list_models`' error path pass the provider/address it actually used — `where()` already has the typed-address rule, it just never sees the request's own target.
  - (audit: api-transcribe-ai)
- **[minor]** `studio/ai.py:266` (`test`, `answer: str(out)[:80]`) — The AI test page shows a Python repr, not the answer: `str(out)` on a list gives `"['ok']"`.
  - Evidence: Live: `POST /api/ai/test {}` → 200 `"answer":"['ok']"`. A person reads `['ok']` as the AI's words when it is Python spelling of a list.
  - Fix: Format the answer with `json.dumps(out, ensure_ascii=False)[:80]` (or stringify a scalar directly) so what the page shows is the answer text.
  - (audit: api-transcribe-ai)

## studio/schedule_ai.py

- **[important]** `studio/schedule_ai.py:267` (`_clock`) via GET /api/schedule/round — An invalid clock is silently replaced with the default 06:00 and answered `ok:true` with no note
  - Evidence: `GET /api/schedule/round?times=banana` → `{"ok":true, "times":["06:00"], "preview":"... at 06:00 ..."}` — banana nowhere in the answer
  - Fix: Say the clock was replaced (or reject); the times/preview pair at least agrees, so only the silence is wrong
  - (audit: api-formats-schedule)

## web/feat/learn-arrows.js

- **[important]** web/feat/learn-arrows.js:28 vs studio/learn_report.py:127 — Shape mismatch: the report route's shaped change rows carry `setting`/`from`/`to`, but the Improve page's "Every round, before and after" card reads `c.key` — `NAMES[c.key]` is `NAMES[undefined]` → undefined → `esc(undefined)` → `""`, so every change renders as "from X → Y" with a **blank setting name**. Cross-file finding: the fix belongs in learn-arrows.js (route to lead).
  - Evidence: studio/learn_report.py:127 (`out.append({"setting": ..., "from": ..., "to": ...})` — no `key`); web/feat/learn-arrows.js:28 (`NAMES[c.key]
  - Fix: | c.key`); web/feat/learn-arrows.js:44 calls this exact endpoint (`/api/learn/report?limit=8`). A live changes-round could not be created without an AI key + channel, but the two shapes are unambiguous in code. | In web/feat/learn-arrows.js:28 read `c.setting` instead of `c.key` (and keep the `NAMES` map keyed on the same five setting names it already lists).
  - (audit: api-learn)

## studio/zernio.py

- **[important]** studio/zernio.py:256-262 (+ 213-214, 149-150) — `POST /api/zernio/test` answers `{"ok": true, "accounts": 0}` when no key is saved anywhere: a success answer from the endpoint whose docstring says it "proves the key works". `accounts()` short-circuits `if not k: return []` (zernio.py:213-214) before `_call` can raise its correct no-key message "Paste a Zernio key in Settings, Connected apps first." (zernio.py:149-150), so `test()` computes `ok:True` from an empty list (zernio.py:262). The dashboard is guarded client-side (`index.html:3381` "Paste the key first."), but any direct API caller gets a wrong `ok:true` instead of the error the rest of the module writes carefully.
  - Evidence: Measured in isolation: `PEAKCUT_DATA=/tmp/pc-audit154-nokey`, `PEAKCUT_ZERNIO_KEY`/`PEAKCUT_ZERNIO_KEY_FILE` unset → `test(): {'ok': True, 'accounts': 0, 'platforms': []}`; same `saved(): has_key False`. Code: zernio.py:213-214, 256-262.
  - Fix: In `test()` (or the server route), raise the existing no-key sentence when `key_override` is empty and `key()` returns nothing: `if not (key_override or key()): raise ZernioError("Paste a Zernio key in Settings, Connected apps first.")`, so `ok:true` only ever means a real Zernio answer came back.
  - (audit: api-posting)

## web/feat/meme-timeline.js

- **[important]** web/feat/meme-timeline.js:108-112 — Every "Listen" press builds a **new** `Audio` and never pauses the previous one, and the panel has no Stop control: pressing Listen on two rows (or twice on one row) plays both copies at once, overlapping, until each file ends.
  - Evidence: meme-timeline.js:110 `const a = new Audio("/api/memesounds/play/" + enc(play)); a.play()` - no pause, no tracking of the previous element; the Sounds list 20 lines up in sounds.js:77,106-117 already does this correctly with one shared player.
  - Fix: Reuse one shared `Audio` for the whole section (copy the sounds.js pattern): pause it before each play, remember which row is sounding, and toggle the pressed button between "Listen" and "Stop".
  - (audit: sounds)
- **[usability]** web/feat/meme-timeline.js:59 — The kept-sounds error says "The shelf could not be read." - the section never calls the kept list a shelf, so a beginner has no word to attach it to.
  - Fix: "The kept sounds could not be read. Reload the page; if it stays empty, the server log says why."
  - (audit: sounds)

## web/feat/schedule.js

- **[important]** web/feat/schedule.js:282-290 — Dead Enter handler on the Clock times field: the plug-in `keys` handler can never fire for an input
  - Evidence: plugins.js:198-200 `wireKeys` returns early when `t.tagName === "INPUT"`; `#sch_times` is an `<input>` (schedule.js:309). The comment promises "Enter inside the times field rebuilds all three cards" but pressing Enter does nothing; the user must find "Rebuild all three"
  - Fix: In `load()`, attach a listener to the field itself: `document.getElementById("sch_times")?.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); drawAll(); } })`, or route input key events in plugins.js
  - (audit: tools-schedule)
- **[usability]** web/feat/schedule.js:97-100, 121-128 — The main card ("Clips on a timer") has no Copy button, yet its caption says "Copying this text installs nothing. It puts the words on your clipboard." Cards 2 and 3 each have one; the handler already supports this card (`HAVE.clips`, line 48)
  - Fix: Add `<button class="btn sm" type="button" data-act="schcopy" data-t="clips">Copy the clips text</button>` to `drawClipActs()`, or reword the card 1 caption to "select the text and copy it yourself"
  - (audit: tools-schedule)
- **[usability]** web/feat/schedule.js:312 — "Rebuild all three" next to the Clock times field does not say what it rebuilds; "all three" only makes sense after reading the cards below
  - Fix: Rename to "Update the schedules" or "Apply these times"
  - (audit: tools-schedule)
- **[usability]** web/feat/schedule.js:213 — Button copy "Copy the tick command" is jargon: a beginner must decode what "tick" means before the button makes sense. The card's note above (`:207-210`) explains the card, not the button.
  - Fix: Rename to "Copy the schedule command" (or "Copy the command the schedule runs").
  - (audit: x-dead-handlers)

## web/feat/analytics-audience.js

- **[important]** web/feat/analytics-audience.js:20-21 (`.aa-dot.new`, `.aa-fill.new`) — The "new viewers" legend dot and bar fill use `var(--brand-ink) #160D05` — a near-black fill on the near-black `--muted #111111` track. The Audience tab's "new viewers" bars are invisible (white-page remnant: dark ink bars on a white page)
  - Evidence: Computed 1.02:1 (WCAG 1.4.11 non-text wants 3:1)
  - Fix: Give the "new" series its own visible colour (e.g. `#22D3EE`, 9.26:1 on `#2A1A12`-class grounds, already used by `.aed-chip.ai`)
  - (audit: x-contrast)
- **[usability]** web/feat/analytics-audience.js:26, web/feat/audio-page.js:44 and :82, web/feat/history.js:34, web/feat/keys.js:18, web/feat/pictures.js:89 — Six quiet labels are set at 10px, below a comfortable reading size for a beginner (contrast itself passes: they use `--faint`, 7.24:1 inside `#main`).
  - Fix: Raise the smallest quiet labels to 11-12px.
  - (audit: x-dead-handlers)

## web/feat/polish-focus.js

- **[important]** web/feat/polish-focus.js:69 (comment 61–63) — Keyboard focus ring on `.side` links/buttons, dialog fields and `.pick-opt` uses `outline-color:var(--brand-line)` = #4A2E18 — dark brown on black, effectively invisible. The comment claims "‑-brand-line is #FFD9BC", which is true only of the old light palette still living in `web/admin.html:14`; index.html:21 has `#4A2E18`
  - Evidence: Computed 1.70:1 on sidebar `#000000`, 1.52:1 on dialog `#111111` (WCAG 1.4.11 wants 3:1); the base rule's `--brand-deep` would be 10.70–11.22:1
  - Fix: Change line 69 to `outline-color:var(--brand-deep)` and rewrite the comment to the measured dark-theme values
  - (audit: x-contrast)

## studio/api_style.py

- **[minor]** `studio/api_style.py:114-145` — `POST /api/formats/plan` is a live route nothing calls. The formats page builds its cards from `GET /api/formats` alone, and no `web/feat/*.js` or `index.html` line names `formats/plan` (repo-wide grep: 5 hits, all in `docs/` or the module itself). The prior wave already recorded the gap at `docs/swarm4/wave4/formats.md:61`. Dead surface: it answers, but no person can ever reach it.
  - Evidence: repo grep `formats/plan` → only `docs/port/18-clipper-ui-reference.md:136-137`, `docs/swarm4/wave4/formats.md:61`, `studio/api_style.py:13,114`; consumer list in `web/feat/formats.js:154,170` names `/api/formats` and `/api/captions/styles` only
  - Fix: Either wire it to a "try this shape" preview flow on the formats page, or remove the route. If kept, also read `words` out of `pick` (see next row)
  - (audit: api-style)
- **[minor]** `studio/api_style.py:128-137` — The plan route reads `words` from the top-level body only, but `format` from `pick` **or** the body. A caller sending the documented nested shape `{"pick":{"format":"moment","words":[…]}}` silently loses the words and plans against an empty list, with no warning in the response.
  - Evidence: `api_style.py:128` `pick = body.get("pick") … else body`; `api_style.py:134` `words = body.get("words")` — never consulted on `pick`
  - Fix: `words = pick.get("words") if body.get("pick") is None or not isinstance(body.get("pick"), dict) else (body.get("words") or pick.get("words"))` — or accept both and document which wins
  - (audit: api-style)
- **[minor]** `studio/api_style.py:139` — Plan error copy is developer-speak: `"Those words are not in the shape PeakCut writes: each needs an 's' time."` A person reading this in a form cannot act on "an 's' time" — the words are speech with `s`/`e` seconds, which the page never explains.
  - Evidence: HTTP 400 response, check 15; contract rule 6 (copy a beginner would not understand in five seconds)
  - Fix: `"Those words cannot be planned: each needs a spoken time ('s') and an end time ('e') in seconds."`
  - (audit: api-style)
- **[minor]** `studio/api_style.py:263,277` (preview) and `:342,354` (motion) — The caches store the timestamp captured **before** the ffmpeg run, so every frame's TTL starts at request start, not at draw time. The 600 s preview TTL loses up to 60 s of fresh window (`timeout=60`, `api_style.py:209`); motion loses up to 90 s of its 3600 s. Negligible for a person, but the constant no longer means what its comment says ("seconds a drawn frame stays worth reusing").
  - Evidence: `now = _time.monotonic()` at `:263`/`:342`; stored unchanged at `:277` `_PREVIEW_CACHE[key] = (now, jpg)` and `:354` `_MOTION_CACHE[key] = (now, mp4)`
  - Fix: Store `_time.monotonic()` inside the same `with _PREVIEW_LOCK:` block that inserts the result, after the render returns
  - (audit: api-style)
- **[minor]** `studio/api_style.py:264-275` (preview), `:343-352` (motion) — Concurrent identical requests both render. The lock guards only the cache probe and is released before `run_in_threadpool`, so two tabs (or two people) asking for the same uncached look at the same moment run ffmpeg twice and the second result overwrites the first. The formats page deliberately fires 4 stills + 3 motions at once (`web/feat/formats.js:234,322`), which makes same-look races reachable.
  - Evidence: lock scope `:264-273` ends before `:275 jpg = await run_in_threadpool(…)`; same shape at `:343-351` → `:352`
  - Fix: Keep a per-key in-flight event (or hold the lock across the render for an already-pending key) so the second caller waits for the first result
  - (audit: api-style)

## studio/api_trends.py

- **[minor]** studio/api_trends.py:78, 195, 223, 273, 324, 332, 368 — Trends routes spend the rate limit on every request, including cache hits — the exact thing studio/api_analytics.py:81-101 says must not happen ("Asking for a number we already hold costs nothing, so it must count for nothing")
  - Evidence: `_throttle(u.id)` at the top of every trends route; trends `_cached` (line 78) takes no uid and never throttles; analytics `_cached` throttles only on a rebuild (studio/api_analytics.py:81-101). auth.throttle counts requests (studio/auth.py:57-69)
  - Fix: Pass uid into trends `_cached` and throttle only on a cache miss, as analytics does
  - (audit: api-analytics)
- **[minor]** studio/api_trends.py:198-213 vs studio/api_analytics.py:149-173 — `GET /api/trends/status` omits the `source` key its sibling analytics status sends; a consumer keying on source gets nothing
  - Evidence: Measured: trends status → `{"connected":false,"note":...}`; analytics status → `{"connected":...,"source":"peakcut","scope":...,"ranges":...,"note":...}`. The page does not read it today
  - Fix: Add `"source"` to the trends status answer
  - (audit: api-analytics)
- **[minor]** studio/api_trends.py:334-342 — A body that cannot be read as JSON is answered "Type a search term first, then save it." — the person did send something; the message never says the body was unreadable
  - Evidence: Measured: POST text/plain "plain text not json" → 400 "Type a search term first, then save it."; the `except` at 336-337 folds the JSON error into body={} and the blank-term branch answers
  - Fix: When `request.json()` raises, answer "That body could not be read as JSON. Send a JSON object, like {\"term\": \"...\"}."
  - (audit: api-analytics)

## studio/api_learn.py

- **[minor]** studio/api_learn.py:114 (and :122) — The undo 400 message's own example `{"at": 0}` can never succeed: every round records `at > 0` and matching is `abs(r.at - at) < 1` (studio/learn.py:671), so `at=0` always answers "There is no round from that time." A beginner who copies the suggested shape gets an error.
  - Evidence: Live: `POST /api/learn/undo {"at":0}` → 400 `"There is no round from that time."`; studio/learn.py:671.
  - Fix: Change the example to `"leave \"at\" out to undo the newest round"` and drop the `{"at": 0}` shape from the message.
  - (audit: api-learn)
- **[minor]** studio/api_learn.py:87-93 — An invalid `days` value silently becomes 28 with no note anywhere in the answer. The response does carry `"days": 28`, so it is discoverable, but an operator sending `{"days": 30}` is never told.
  - Evidence: Live: `POST /api/learn/run {"days":"bad","dry":true}` → `"days": 28`, no note.
  - Fix: Either accept 1-365 and clamp only at the extremes, or add a `"note"` sentence naming the fallback.
  - (audit: api-learn)
- **[minor]** studio/api_learn.py:19-20 vs :224-236 — The module header promises "Every route answers with a sentence as well as data", but `GET /api/learn/arms` returns `{"trial": null}` with no sentence (only the module-missing path carries a `why`). The empty answer is exactly the one the header says most needs explaining.
  - Evidence: Live: `GET /api/learn/arms` → `{"trial":null}` (empty and after cleanup).
  - Fix: Add `"why": "No trial is saved yet. Start one to try two settings against each other."` alongside `trial: null`.
  - (audit: api-learn)

## web/feat/pictures-dialog.js

- **[minor]** `web/feat/pictures-dialog.js:25-26` — The dialog pane caches per clip (`box.dataset.key`) and never refreshes: after changing the layout in that pane, closing and reopening the dialog for the same clip shows the stale select and hint, contradicting what was just saved
  - Evidence: The guard `if (box.dataset.key === D.jid + "/" + D.cid) return;` skips the fetch on every later draw for that clip
  - Fix: Refetch on each `drawClipDlg` (one cheap GET) or rewrite `box.innerHTML` in the change handler
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures-dialog.js:46-48,51-55` — After choosing a layout in the pane's select, the hint under it does not update — it still describes the old layout until the dialog is redrawn
  - Evidence: The hint is static innerHTML; the change handler only toasts
  - Fix: Update the hint inside the change handler from the response (`out.name`/`out.note` are already sent by `api_overlay.py:309-310`)
  - (audit: pictures-editor)
- **[minor]** `web/feat/pictures-dialog.js:51-55` — The select keeps the newly chosen value when the PUT fails, so the control contradicts the toast and the server state
  - Evidence: No revert on catch
  - Fix: Revert `sel.value` to the previous template on error
  - (audit: pictures-editor)

## web/feat/filters.js

- **[minor]** `web/feat/filters.js:17-18` — Same weak-boundary pattern on the filter pills
  - Evidence: `.pcf-pill` bg `--bg` on the page bg with border `--line #1E1E1E` → boundary 1.33:1
  - Fix: Same: lighter bg or stronger border
  - (audit: videos)
- **[minor]** `web/feat/filters.js:33` — `display:none!important` — `!important` is on the fix-wave ban list
  - Evidence: `[data-pcfilter="out"]{display:none!important}`
  - Fix: Works today; replace with a higher-specificity selector in the fix wave
  - (audit: videos)
- **[minor]** `web/feat/filters.js:17` — Filter pills `.pcf-pill` capped at 32 px via explicit `height:32px`.
  - Evidence: `height:32px` literal.
  - Fix: `min-height:44px` at ≤640 px.
  - (audit: x-mobile)

## web/feat/mood.js

- **[minor]** `web/feat/mood.js:55` vs `web/feat/sounds.js:212` — The two consumers read the `ready` flag with opposite polarity: the clip dialog treats a missing flag as playable (`r.ready !== false`), the Sounds page as not built (`r.ready === true`)
  - Evidence: Both lines as quoted; the server always sends `ready`, so nothing is wrong today
  - Fix: Pick one polarity in both files; the Sounds page's is the safer one
  - (audit: api-formats-schedule)
- **[minor]** `web/feat/mood.js` — The sound field's label "Sound" repeats the pane heading "Sound"
  - Evidence: pane has `h3#ed_sound` "Sound" (index.html:2796) and the picker row renders a second "Sound" label above the select
  - Fix: Label the field "Background sound"
  - (audit: clip-dialog)

## web/feat/igcaption.js

- **[minor]** web/feat/igcaption.js:42, :58 — The UI hardcodes the 2,200-character limit instead of using the `limit` the API sends, so it can silently drift from `MAX_LENGTH`
  - Evidence: `igcaption.py:11 MAX_LENGTH = 2200`; view (igcaption.py:51) and looks (api_igcaption.py:56) both send `limit: 2200`; the counter prints the literal `" / 2,200 characters"` and the textarea has `maxlength="2200"`
  - Fix: Use the API's `limit` in both the counter string and the textarea maxlength
  - (audit: api-igcaption)
- **[minor]** web/feat/igcaption.js:42 vs :58 — The visible counter and the textarea maxlength count different units: `Array.from(caption).length` counts code points, HTML maxlength counts UTF-16 units; with emoji the box blocks input while the counter still shows room (1,100 emoji → "1,100 / 2,200" but typing blocked)
  - Evidence: measured: two different counting units on the same pair of controls; no data loss (the UI is only ever stricter than the server), but the numbers disagree
  - Fix: Drop `maxlength` and rely on the counter plus the server's clear 400, or align both to one counting unit
  - (audit: api-igcaption)

## studio/api_igcaption.py

- **[minor]** studio/api_igcaption.py:53-57 — `GET /api/igcaption/looks` skips the `_me(request)` disabled-account check that every other route in this router performs
  - Evidence: igcaption_for (:61-62), igcaption_write (:70), igcaption_generate (:91) all call `_me`; igcaption_looks does not. Impact is nil today (the response carries only constants, no user data)
  - Fix: Call `_me(request)` for consistency so the router gates uniformly
  - (audit: api-igcaption)
- **[minor]** studio/api_igcaption.py:55-56 — `/api/igcaption/looks` returns languages as bare IDs with no labels while formats carry `{id,label}`; a consumer reading this endpoint alone shows "ja"/"zh", which a beginner would not understand in five seconds
  - Evidence: curl: `"langs":["original","ja","zh"]` next to `"formats":[{"id":"natural","label":"Natural"},…]`; `LANG_NAMES` (igcaption.py:19) already holds plain names ("the same language as the source", "Japanese", "Simplified Chinese") but is unused by this route; the shipped UI hardcodes its own labels (igcaption.js:52) so users are fine today
  - Fix: Return `[{"id","label"}]` for langs using `LANG_NAMES`, matching the formats shape
  - (audit: api-igcaption)

## web/feat/style-tiles.js

- **[minor]** web/feat/style-tiles.js:48 — The selected tile's check glyph is #fff on `--brand` #FF8B33 = 2.34:1, below the 3:1 non-text minimum. It is `aria-hidden`-decorative and duplicates the orange border, the label flipping to `--text` and aria-pressed, so nothing is lost without it — but it is the one below-minimum pair on the page.
  - Evidence: style-tiles.js:47–51; measured L(#FF8B33)=0.3997 → 1.05/0.4497 = 2.34:1; decorative: `.stile.on .stile-lb` turns `--text` (:45)
  - Fix: Use `--brand-ink` #160D05 for the check stroke (about 8.5:1 on the orange), or leave as decorative and note it
  - (audit: transcribe-brand)
- **[minor]** `web/feat/style-tiles.js:112` — The styles-route fetch fails silently — but it is a fallback-only enhancement: the primary source of looks is the page's own state, and the re-mount is gated so the fetch only refines what is already shown.
  - Evidence: `style-tiles.js:112` `.catch(() => {})`; the re-mount at `style-tiles.js:106-111` runs only when the fetched list actually differs (`if (g.dataset.names === names(list)) continue;` at `:107`).
  - Fix: Acceptable as-is; a one-line note would be polish.
  - (audit: x-states)

## web/feat/learn-arms.js

- **[minor]** web/feat/learn-arms.js:170-171, 168, 200, 295 — The Improve page's trial card speaks A/B-testing jargon: heading "Two arm trial" (line 200), "Both arms have run." (168), "Arm a is running now: ... Arm b is ..." (170-171), toast "The trial is written down. Arm a runs first." (295). "Arm" means nothing to a beginner.
  - Evidence: File lines: `170
  - Fix: parts.push(`<p class="armline">Arm ${esc(arm)} is running now: ...` and `295 | P.toast("The trial is written down. Arm a runs first.", "ok");` | Replace arm a/b with "the first setting"/"the second setting" everywhere the card speaks; rename the heading "Try one setting, then another" or "Two-setting trial".
  - (audit: x-copy)
- **[minor]** web/feat/learn-arms.js:178-179 — Edge state explains itself with mechanism: "Both arms have run. PeakCut has not sent the sentence that compares them yet, so there is nothing to quote here." ("has not sent" = a server field is missing).
  - Evidence: File line: `178
  - Fix: parts.push(`<p class="sub" style="margin:11px 0 0">Both arms have run. PeakCut has not sent the sentence` | "Both settings have been measured. The sentence comparing them is not written yet — it appears here once PeakCut has finished."
  - (audit: x-copy)

## web/feat/analytics-trends.js

- **[minor]** `web/feat/analytics-trends.js:44` — Trend-chip close button `.atr-x` is 26×26.
  - Evidence: `width:26px;height:26px` literal.
  - Fix: 44 px hit box at ≤640 px; keep the glyph small, pad the box.
  - (audit: x-mobile)
- **[minor]** `web/feat/analytics-trends.js:42` — `.atr-chip` itself (button) is capped at 32 px via explicit `min-height:32px`.
  - Evidence: `min-height:32px` literal — an explicit declaration, so polish-mobile's absent sweep leaves it at 32.
  - Fix: Raise to `min-height:44px` at ≤640 px.
  - (audit: x-mobile)
- **[usability]** Trends tab, "Breakout videos" block (title drawn by web/feat/analytics-trends.js:232; route studio/api_trends.py:265-314) — The title says "breakout", but the route answers this channel's own videos ranked by views; the route's note explains it, the title does not. A beginner may expect YouTube's public trending chart
  - Fix: Rename the block to "Your videos this range", or lead the block with the route's note before the rows
  - (audit: api-analytics)

## web/ascii.js

- **[minor]** `web/ascii.js:171-182` (`rules()`, reached from `PeakTools.ruleBadge`) — The file is loaded by no page — `index.html:922` loads `/assets/gradient-ascii.js`, and a grep of all six HTML files plus all 76 `web/feat/*.js` finds no `PeakTools` caller — and its `/api/rules` call expects a `{rules:{...}}` table while the route answers a single badge, so if anything ever loads the file every badge reads "Rules unknown"
  - Evidence: `grep PeakTools` over `web/` matches only `ascii.js` itself; `GET /api/rules` (no params) → `{"rule":"unknown",...,"label":"Rules unknown","tone":"","can_clip":true,"blocked":false}` with no `rules` key
  - Fix: Delete the dead file or update `rules()` to the badge shape and give it a page
  - (audit: api-formats-schedule)

## studio/ai_arms.py

- **[minor]** studio/ai_arms.py:96 (via POST /api/learn/arms) — A one-arm request is refused with `"PeakCut does not change a setting called nothing."` — it never says the second setting is missing. The page blocks this client-side with clearer copy ("Pick two different settings for the trial.", web/feat/learn-arms.js:271-278), so the server copy only shows for hand-crafted calls, but the two disagree.
  - Evidence: Live: `POST /api/learn/arms {"target":"style","value":"beast"}` → 400 `"a setting called nothing"`; studio/ai_arms.py:94-97 validates both arms in one loop.
  - Fix: In ai_arms.start, refuse an empty arm with `"Name two settings to try, one for each arm."` before the known-settings check.
  - (audit: api-learn)

## studio/overlay.py

- **[minor]** `studio/overlay.py:66` (`stem, ext = spoken, "png"`) and `studio/api_overlay.py:109-111` — Every upload is stored under a `.png` name whatever its real format, and then served with `content-type: image/png` even when the bytes are JPEG. Browsers sniff and still render it, but the Content-Type header lies, and a file saved from the page carries a wrong extension.
  - Evidence: Measured M1: a real JPEG uploaded -> stored `jpegshot-8ec437.png`. M2: GET it -> 200 `content-type: image/png` while the bytes begin `FF D8 FF E0` (JPEG magic).
  - Fix: Pick the extension from the format `_identify` already reads (ffprobe gives `codec_name`), or serve by sniffed content instead of the suffix.
  - (audit: api-overlays)

## (other)

- **[minor]** GET `/api/overlays/image/{name}` with a dot path — `/api/overlays/image/..` is answered with a 307 that redirects to the shelf list instead of a 404. Cosmetic: the slug guard (`studio/overlay.py:56-59`) runs before any file access, so nothing is ever served through it — the encoded form already 404s.
  - Evidence: Measured A7: 307 with `location: http://127.0.0.1:8798/api/overlays`, followed -> 200 (the shelf JSON). A7b: `..%2F..%2Fetc%2Fpasswd` -> 404.
  - Fix: Not worth a fix in the route (Starlette normalizes the URL before routing). If desired, reject names whose slug form is not `clean_slug`-clean with 404 and document that the bare `..` case is a framework redirect.
  - (audit: api-overlays)
- **[usability]** where — what
  - Fix: fix
  - (audit: api-analytics)
- **[usability]** Insights page wide presets (Last 90 days / 365 days / Lifetime) in local mode — The numbers behind them cover only 14 days and nothing on screen says so; a chart draws 14 points across a 90-day axis with no explanation (measured above)
  - Fix: Add the note sentence from finding B1 and clamp the chart's date labels to the days that have data
  - (audit: api-analytics)
- **[usability]** where — what
  - Fix: fix
  - (audit: api-learn)
- **[usability]** where — what
  - Fix: fix
  - (audit: formats)
- **[usability]** Look tiles (`formats.js:301-308`) — A beginner cannot see which caption style is already the default; every tile says "Use as default" and they must leave the page (Brand tab) to find out
  - Fix: Mark the current default tile `aria-pressed="true"` / "Default for new clips" on load
  - (audit: formats)
- **[usability]** Shape cards (`formats.js:197-210`) — Shape cards never say how many clips a shape joins ("Callback needs 2"), though the server sends it and the code comment promises it
  - Fix: Show "Joins N clips" in the card foot
  - (audit: formats)
- **[usability]** Nav vs page (`formats.js:470/478`) — "Clip formats" nav leads to a page titled "Caption styles"
  - Fix: Make the two names agree
  - (audit: formats)
- **[usability]** Look tiles (12 styles) — Duplicated descriptor ("Meme / Meme") reads as a rendering bug
  - Fix: Skip or reword when the descriptor equals the label
  - (audit: formats)
- **[usability]** `formats.js:41` — 9.5px "Still frame" badge is very small to read
  - Fix: 11px
  - (audit: formats)
- **[usability]** U1 — minor
  - Fix: `web/feat/learn.js:83-86, 249, 292-307` | Premature empty state on first load: while `/api/learn/state` is still in flight, the page already prints "PeakCut has not looked yet. Press the button below and it will read the last 28 days first." and shows the "Analyse and improve" button disabled with no reason — a false claim ("has not looked yet") over a page that is merely loading. | `factsBlock` prints the has-not-looked copy whenever `st.length` is 0 (learn.js:83-86), which includes `STATE === null`; `runBlock` disables the button when `STATE` is null (`can = STATE && STATE.can_run`, learn.js:249) with `why` empty; `load()` paints `body()` before awaiting the read (learn.js:292-307). | While `STATE` is null, show a one-line "Reading the numbers…" state (the learn-hooks/post-time cards already use exactly this pattern, e.g. learn-hooks.js:37).
  - (audit: improve)
- **[usability]** U2 — minor
  - Fix: `web/feat/learn.js:260-263, 317` | The "Look at [28 days]" select has no visible effect until a run button is pressed: its value is only read inside `run()` (learn.js:317). Changing it redraws nothing and nothing says so — a beginner can believe the page ignored their choice. (The control is not dead — the value does reach `/api/learn/run`.) | Select `#lrn_days` (learn.js:261-263) has no `data-act` and plugins.js has no change-event wiring (grep `addEventListener\("change"\|onchange` over plugins.js → only MutationObserver watches, plugins.js:175-193); consumed at learn.js:317. | Either a one-line hint under the run row ("the buttons use the years you pick here"), or re-read the preview when the select changes.
  - (audit: improve)
- **[usability]** Minor — `web/feat/analytics-audience.js` (no-token note)
  - Fix: With no channel connected, the Audience tab tells the user to connect but gives no way there: the note text renders as plain copy, so `analytics-empty.js` (which links empty boxes) deliberately stays out, and this file contains no link. Every sibling surface on the same page links: traffic :141, KPI :128, realtime :130, empty-boxes :61 | Grep for `/app/apps` across all analytics files: present in 5 files, absent in `analytics-audience.js` and `analytics-retention.js`. `analytics-empty.js:86` returns early on real content, so the note text suppresses the link | Append a "Connected apps" link to the no-token note, the way `analytics-traffic.js:141` does
  - (audit: insights-audience)
- **[usability]** Minor — `web/feat/analytics-audience.js:25,155`
  - Fix: The 7×24 hours heatmap (`min-width:520px`) sits in an `overflow-x:auto` scroll region with no hint; on a 390 px phone roughly 130 px (about hours 18-24) hides off-screen, and on overlay-scrollbar platforms there is no visible scrollbar and no copy saying more is there | :25 `.aa-scroll{overflow-x:auto;padding-bottom:2px}.aa-map{min-width:520px}`; :155 renders it; grep for "scroll/swipe/drag" copy in the file: none | One faint line under the map: "Swipe to see the whole day" (or a right-edge fade)
  - (audit: insights-audience)
- **[usability]** Minor — `web/feat/analytics-retention.js` (fail state)
  - Fix: The curve's error shows the server's "Retention comes from YouTube. Connect a channel under Connected apps." with retry buttons but no link, so the user must find the nav row themselves | Server body verified: `{"detail":"Retention comes from YouTube. Connect a channel under Connected apps."}` (`studio/api_analytics.py:411`); grep: no `/app/apps` in this file | Link the words "Connected apps" to `/app/apps`, the way the other cards do
  - (audit: insights-audience)
- **[usability]** important — `web/feat/analytics-table.js:76` + `web/feat/analytics.js:79-87,140`
  - Fix: **Two date-range controls can disagree**: the page header says one range (e.g. "Last 90 days, ending …") while the table picker and its numbers say another ("Last 28 days"). A beginner cannot tell which control is in charge, and the hint under the picker does not mention that the page-level range exists. | The bug-1 fix (inherit the page range into the picker), or hide the table picker while it disagrees with the header.
  - (audit: insights-content)
- **[usability]** important — `web/feat/analytics-table.js:111-112,144`
  - Fix: **Two columns of dashes that blame the video**: beginners read the permanent "–" in Impressions / Click-through, with the tooltip "This video did not report this number", as broken data on their channel. | Drop the columns, or re-copy the tooltip so it says the app does not fetch these numbers.
  - (audit: insights-content)
- **[usability]** minor — `web/feat/analytics-table.js:18` + `web/index.html:619,883`
  - Fix: **No scroll cue at phone width**: the 11-column table is `min-width:960px` (560px on ≤640px) inside `.scroll{overflow-x:auto}`; at a 390px viewport roughly a third of the table is off-screen with no visible scrollbar or affordance, so a first-time user may not realise more columns exist. | Fade the right edge or add a short "swipe for more columns" hint on small screens.
  - (audit: insights-content)
- **[usability]** `analytics-kpi.js:157→129` — During load the key-numbers box says "Not connected yet. Connect a channel in Connected apps to fill these in." even for a connected install — a reader learns the wrong state in the first second of every visit.
  - Fix: Loading copy, not the not-connected copy (finding 4).
  - (audit: insights-frame)
- **[usability]** `analytics.js:68` + `analytics-charts.js:133` — The header promises "compared with the N days before" and the chart's legend is ready to say "Previous range", but the comparison never arrives — a beginner looks for a dashed line that can never be drawn.
  - Fix: Ship the comparison or stop claiming it (finding 3).
  - (audit: insights-frame)
- **[usability]** `analytics-kpi.js:99` — The Compare toggle's two positions produce identical requests and identical numbers — a control that does nothing the reader can see.
  - Fix: Honor the off position (finding 2).
  - (audit: insights-frame)
- **[usability]** `analytics.js:41-45` — "Lifetime" is really the last ten years; a beginner comparing two Lifetime reads a year apart sees no difference.
  - Fix: Label the cap (finding 7).
  - (audit: insights-frame)
- **[usability]** Good, no change needed — "Connect a channel in Connected apps to fill these in." carries a working link to `/app/apps` (verified 200) — one step from the broken state to its fix. "Not in this answer yet: Impressions, Click-through rate." states exactly which numbers are missing instead of blank space. Range labels 7/28/90/365/Lifetime are self-explanatory; the change pills carry arrows plus `title`/`aria-label` explaining direction and the period.
  - Fix: —
  - (audit: insights-frame)
- **[usability]** where — what
  - Fix: fix
  - (audit: review)
- **[usability]** important — web/index.html:836 (hits both owned pages)
  - Fix: Every explanation vanishes on phones. index.html hides all `.hint` elements inside `@media (max-width:560px)`, and 390px is inside that range. On a phone the streamer form loses all of its field hints (URL, clips, lengths, style, chat, minutes, the gta-only "This one is real", "A note, not a filter", the creator select hint), and the Live page loses the Check now / Remove / Look again / channel-name hints. Controls that depend on their hint for meaning are left with none - the gta-only checkboxes and the brand-save button become unexplained toggles and buttons. | web/index.html:836 `@media (max-width:560px){... .hint{display:none} ...}`; streamer-mode.js carries 10+ .hint nodes in formHtml; live.js carries 4 | Keep hints readable on small screens (smaller size, block display) or move the essential explanation into aria-label/placeholder so the meaning survives
  - (audit: streamer-live)
- **[usability]** minor — web/feat/streamer-mode.js:543-564 (with server.py:1365-1366)
  - Fix: "Start recording" can silently record a different channel than the one the user typed. startReading reads the draft (which includes the URL box) and sends {channel: link}, but the route uses that channel only when it is already one of the creator's saved channels (server.py:1366), otherwise it falls back to the creator's own or the on-air channel with no message. The hint at 625-626 explains the general rule ("uses the creator's own saved channel and settings"), but not that a pasted link can be quietly ignored, and the UI reads like the link above is the input. | streamer-mode.js:551-552 code comment; server.py:1366 `url = asked if asked in c["channels"].values() else ...` | When the typed link is not a saved channel, say so in #str_lerr instead of falling back silently
  - (audit: streamer-live)
- **[usability]** where — what
  - Fix: fix
  - (audit: tools-schedule)
- **[usability]** minor — web/index.html:2414 + 2465
  - Fix: The preview follows edits live (debounced 650 ms) while the brand is only saved by "Save brand" at the very bottom of a six-section form. The copy explains both ("It follows your edits as you type" / "Save here and every clip made from now on uses it"), but a beginner who edits a colour and sees the frame change can reasonably believe the change is already applied, then close the page. | index.html:2414 (.sub copy), 2465 (button), brandsave handler 3166–3194 (PUT /api/brand is the only save) | Once any #br_* field changes, label the button "Save brand — not saved yet" (or add a sticky save bar), and clear it after the PUT
  - (audit: transcribe-brand)

## web/feat/stats.js

- **[minor]** `web/feat/stats.js` — "Numbers" summary is vague, and the section now sits inside the Look pane above its heading
  - Evidence: summary text "Numbers"; inserted before `.panel`'s first h3, which is `h3#ed_look` "Look" (index.html:2754) — the YouTube numbers are only reachable from the Look tab; the file's own comment ("right under the score, above 'On the video'") is stale
  - Fix: Rename the summary to "YouTube numbers", anchor it after `.ed-railnav` (or in `.job-head`) so it is always visible, and refresh the comment
  - (audit: clip-dialog)

## web/plugins.js

- **[minor]** web/plugins.js:153 — one-sided `pcDone` handshake: wireActs skips elements marked `dataset.pcDone === "1"` ("already handled by index.html") but index.html never sets it (0 matches in web/index.html)
  - Evidence: latent double-fire if a plugin act ever shares a name with an index.html act (none today — plugin act names are unique)
  - Fix: either mark `pcDone` in index.html's act switch or delete the check and its comment
  - (audit: home)

## web/feat/analytics-compare.js

- **[minor]** `web/feat/analytics-compare.js:212` — **Duplicate summary request**: the compare asks `/api/analytics/summary?days=N&compare=1` while the KPI row asks the same route with `start&end&days&compare` (`analytics-kpi.js:96-100`) — two client requests for one server-cached answer (same key `sum:{uid}:{days}:{compare}:{token}`, `studio/api_analytics.py:234`). No quota cost, redundant network.
  - Evidence: Two query strings in `web/feat/analytics-*.js`.
  - Fix: Share one query-string builder or one in-flight request between KPI and compare.
  - (audit: insights-content)

## web/feat/polish-contrast.js

- **[minor]** web/feat/polish-contrast.js header vs measured — Header numbers are off: claims 8.10/4.79/7.24/6.86/5.68, measured 7.85 (dim on bg) / 4.74 (#7C7C7C on bg) / 6.70 (#A0948C on bg) / 6.39 (on muted) / 5.63 (on brand-soft). Text 18.16 and #75695F=3.72 match. Header says "None of them are estimates" — they are rounded from a different rounding path
  - Evidence: Measured table in this report (Python, exit 0)
  - Fix: Re-measure and rewrite the header numbers; keep "None of them are estimates" true
  - (audit: x-contrast)

## web/feat/icons-extra.js

- **[minor]** web/feat/icons-extra.js:154-158 — The Icons Tools card is written for the maintainer, not the user: "Three icon names the page uses but never drew", "Press this after editing the file", "It re-reads the page's icon map". Every signed-in user sees this card.
  - Evidence: File line: `158
  - Fix: <p class="hint">Press this after editing the file. It re-reads the page's icon map and marks each icon as drawn or missing.</p>` | Either move the card behind a maintainer flag, or rewrite: "Three missing icons, now filled in. Press Check again after updating PeakCut."
  - (audit: x-copy)

## web/feat/polish-empty.js

- **[minor]** web/feat/polish-empty.js:39-47 — Dead helper: `P.empty({act, ...})` builds markup with a dynamic `data-act="${act}"` (`:43`), but no feature ever calls `P.empty`, so the helper, its `act` parameter and the `:86` handler branch never run.
  - Evidence: grep `P.empty` across `web/feat/*.js` finds only the definition at polish-empty.js:39; no caller passes `{act:...}`.
  - Fix: Remove the helper, or wire it into a real empty state so the act it accepts is reachable.
  - (audit: x-dead-handlers)

## web/feat/polish-keyboard.js

- **[minor]** `web/feat/polish-keyboard.js:31` — Keyboard-palette close `.pckb-x` is 30×30.
  - Evidence: `width:30px;height:30px` literal.
  - Fix: 44 px box at ≤640 px.
  - (audit: x-mobile)

## web/feat/peek.js

- **[minor]** `web/feat/peek.js:25` — "Take stills" button `.pcpeekbtn` is 30 px tall.
  - Evidence: `height:30px` literal (dashed secondary button on clip cards).
  - Fix: `min-height:44px` at ≤640 px; container query at `web/feat/peek.js:31` already handles the narrow card.
  - (audit: x-mobile)

## web/feat/clean-forecast.js

- **[minor]** `web/feat/clean-forecast.js:44` — A failed words fetch is conflated with "this clip has no word timings yet". `.catch(() => [])` makes a failed fetch yield the same empty array as a clip with no transcript, so the panel shows the empty-state claim instead of a fetch-failure note.
  - Evidence: `clean-forecast.js:44` `.catch(() => [])`; `say()` at `clean-forecast.js:90-92` then prints "PeakCut has no word timings for this clip yet, so it cannot say what will change until the clip is made once." For an existing clip whose transcript exists, the copy implies making the clip will fix it, when the server simply did not answer — a fact the server never stated (the repo's own zero-is-a-claim rule). It is in words, never silent, so minor.
  - Fix: Catch sets a failure flag; on failure print "The word timings could not be read. Try again." instead of the no-word-timings claim.
  - (audit: x-states)

## web/feat/analytics-retention.js

- **[usability]** Retention picker in local mode (web/feat/analytics-retention.js:96-103, 205; route studio/api_analytics.py:271-324) — The picker needs 11-character YouTube ids; the videos route's local branch answers PeakCut post ids, so the picker is empty and the page's empty sentence ("No videos in this range yet") can read false once posts exist
  - Fix: In the local branch, derive the YouTube id from the post URL when there is one, and have the route's note say the picker needs a connected channel
  - (audit: api-analytics)

## studio/api_posttime.py

- **[usability]** studio/api_posttime.py:63,73-75 — Best-hours are computed from the **UTC** hour of each post (`(when % 86400) // 3600`) and presented as plain clock labels (`"14:00"`, `"averaged 500 views at 14:00"`) with no zone marker. A beginner reads "14:00" as their local clock and posts 5.5 h early (IST +5:30).
  - Fix: Either convert to the account's local zone before labelling, or append " UTC" to `label` and `note` (e.g. `"averaged 500 views at 14:00 UTC"`).
  - (audit: api-learn)

## studio/api_brandai.py

- **[usability]** studio/api_brandai.py:52-56 (measured) — `POST /api/brandai/suggest` blocked for 41.0 s on this install. The throttle message says nothing about the wait, and the route's docstring does not warn callers how slow an enforced-schema ask is (compare the 8.9 s vs 38.3 s measurement recorded in AGENTS.md).
  - Fix: Add a hint where the button is defined ("this can take about half a minute") so a beginner does not think it hung.
  - (audit: api-learn)

