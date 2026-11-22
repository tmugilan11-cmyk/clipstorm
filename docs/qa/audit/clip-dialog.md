# Clip dialog audit — agent-146

Scope: the clip dialog (`#clipdlg`) in `web/index.html` and its seven owned feature files
(`web/feat/{mood,stats,igcaption,live-heading,clean-forecast,stage,day}.js`), plus the shared
plumbing they ride on (`web/plugins.js`, `web/feat/polish-contrast.js`, the `/assets/feat` loader).
Method: static reading of every owned file, route existence checks against `studio/*.py`, HTTP
checks against the running server (127.0.0.1:8798), and WCAG 2.2 contrast math from the palette
in `web/index.html:12-21` (formula `(L1+0.05)/(L2+0.05)`).

## Owned pages / files

| What | Where |
|---|---|
| Clip dialog markup + editor JS | `web/index.html` drawClipDlg 2720-2838, wireEditor 2842-2929, mmss 2932-2935, drawHist 2937-2952, loadHist 2953-2967, action handlers ~3108-3463 |
| Sound picker | `web/feat/mood.js` |
| YouTube numbers card | `web/feat/stats.js` |
| IG caption box | `web/feat/igcaption.js` |
| Live heading preview | `web/feat/live-heading.js` |
| Clean-sound forecast | `web/feat/clean-forecast.js` |
| Job stage dots | `web/feat/stage.js` |
| "Make my day" card | `web/feat/day.js` |

## Checks run

1. Read every owned file fully (day.js tail 200-205 included).
2. Route existence: every API call from owned files matched to a handler in `studio/*.py` —
   `words` api_text.py:279, `history` GET/PATCH api_history.py:179/187, `render` server.py:1081,
   `edit` api_text.py:196, `translate` api_text.py:243, `peek`/`peek/{cid}` api_preview.py:64/101,
   `igcaption` GET/PUT/generate api_igcaption.py:60/68/89, `preview/heading` api_heading.py:143,
   `/api/moods` api_sound.py:58, `/api/stats/video` api_stats.py:71, `/api/preview` server.py:839,
   `/api/translate/langs` api_text.py:112, `/api/posts` server.py:1808,
   `/api/style/preview` api_style.py:218, `/api/captions/styles` api_style.py:46,
   `/api/channel-preview` server.py:1283. All present.
3. HTTP: `/app/videos` → 200, `/app/overview` → 200, `/app/` → 200, `/assets/feat` → 200
   (listing returns all 76 feat files incl. every owned one).
4. Plugin plumbing: `P.add` pushes into `P._order` (plugins.js:27) and wireActs dispatches
   `P[n].act[act]` (plugins.js:162) — `pcstatsread` is live. `repaint()` watches `#jobs`,
   `#ov`, `#clipdlg` (plugins.js:188-191) — all after-hooks fire. `/assets/feat` listing route
   confirmed at server.py:469-474.
5. Shared globals: `esc` is a top-level `const` (index.html:930 — global lexical scope, visible
   to classic feat scripts); `ask` is a top-level function → `window.ask` exists (index.html:1014);
   `put` (index.html:1013), `P.api/P.send/P.state` (plugins.js:258-260) all present.
6. Contrast: measured ratios computed from hex values; `polish-contrast.js:29` sets
   `#main, dialog { --faint: #A0948C; }` (7.24:1 on `--bg`), which lifts every faint string inside
   the clip dialog and on job cards.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| critical | `web/feat/day.js:17,21` | "Make my day" card paints a light cream radial-gradient on the dark app; the help sentence and error notes are unreadable over it | gradient `radial-gradient(130% 190% at 0% 0%,#FFF9F4 0%,var(--brand-soft) 62%,#FFF7F0 100%)`; `.day-help` ink `var(--text)` #F5F5F5 over the light region at the sentence's start ≈2.7:1 (worst ≈1.04:1); `.day-note` --bad #F87171 over the same region ≈1.1:1 — far below the 3:1 floor | Drop the cream stops: keep the card on a dark ground (e.g. `var(--brand-soft)` flat or a gradient between `--brand-soft` and a darker warm tone), and measure `.day-help`/`.day-note` ink against the result like polish-contrast.js does |
| critical | `web/feat/day.js:27,29` | `.day-note` status line (default --dim #A3A3A3, bad #F87171) fails over the gradient's light bottom-left region | --dim over interpolated ≈#9E948D ≈2.9:1; --bad over the same ≈1.1:1 — both below 4.5 for 13px text | Same fix as above; once the card is dark both pass untouched |
| important | `web/index.html:2963` (loadHist) | History load swallows every non-404 error silently — a network failure leaves the version list hidden with no message and no retry | catch body: `if (!/not found\|404/i.test(e.message\|\|"")) return;` — only 404 falls through to the empty state; any other error returns with nothing on screen | Show a quiet line in `#dlgvers` ("The versions could not be read. Try again.") and make the row retry on next open |
| important | `web/index.html:2853-2857` (wireEditor.sync) | Dead branch: sync() opens with `if (from === "range") { … if (from === "range") return; }` and is only ever called with `"num"` | only call site `sync("num")` at 2866-2867; ranges have their own listeners at 2868-2869 — the branch can never run and hides that the two paths were once one | Delete the unreachable block; keep one `sync()` used by both listeners |
| minor | `web/feat/stats.js` | "Numbers" summary is vague, and the section now sits inside the Look pane above its heading | summary text "Numbers"; inserted before `.panel`'s first h3, which is `h3#ed_look` "Look" (index.html:2754) — the YouTube numbers are only reachable from the Look tab; the file's own comment ("right under the score, above 'On the video'") is stale | Rename the summary to "YouTube numbers", anchor it after `.ed-railnav` (or in `.job-head`) so it is always visible, and refresh the comment |
| minor | `web/feat/mood.js` | The sound field's label "Sound" repeats the pane heading "Sound" | pane has `h3#ed_sound` "Sound" (index.html:2796) and the picker row renders a second "Sound" label above the select | Label the field "Background sound" |
| minor | `web/index.html:2741` | Job-head badge shows raw judge counts ("Words 6 · Reaction 2") — jargon a beginner can't act on | badge string in drawClipDlg | Keep it plain: "6 words · reacts 2" or a single word like "Good" with the counts in a title attribute |

## Verified clean (no finding)

- All seven API-round-tripping feat files keep proper loading / empty / error / busy states;
  igcaption resets its error key so retry works; stats.js keeps the API key in a closure, types
  the field `password` and never echoes it; live-heading's paint hook receives `#clipdlg`
  itself and its img onerror explains itself; clean-forecast uses live checkbox state and words
  the no-timings case truthfully; day.js guards live streams, never sends before confirm, and
  survives redraws without losing a half-typed link.
- Stage dots only render on `queued`/`running` cards, respect reduced motion, and match the
  stage strings `studio/jobs.py` really sets.
- Contrast inside the dialog passes everywhere measured once `polish-contrast.js` scope
  (`#main, dialog`) is applied: faint #A0948C 7.24:1, dim 8.10:1, brand-ink on brand 8.22:1.
- No owned handler is dead: `pcstatsread` routes through plugins.js wireActs; openpics lives in
  pictures.js (verified present in the live feat listing).
