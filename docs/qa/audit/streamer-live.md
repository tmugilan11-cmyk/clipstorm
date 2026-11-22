# Audit: Streamer clipping page and Live page

Auditor: agent-131 (QA swarm 40). Date: 2026-11-22.
Rule set: docs/qa/CONTRACT.md. Severity: critical / important / minor.

## Pages and files owned

| Kind | Path | Size |
|---|---|---|
| Page | /app/streamer | shell 200 OK |
| Page | /app/live | shell 200 OK |
| File | web/feat/streamer-mode.js | 712 lines, 37,259 bytes |
| File | web/feat/live.js | 383 lines, 16,935 bytes |

Both owned files were read fully, line by line. Shared code read where the pages depend on it:
web/plugins.js (all 282 lines), web/index.html (routing, api/send, palette, icon map, CSS),
studio/server.py, studio/api_preview.py, studio/api_brand.py, studio/jobs.py, studio/hunt.py,
studio/render.py, studio/captions.py.

## Checks run

1. Read docs/qa/CONTRACT.md before starting; loaded skills systematic-debugging and frontend-design.
2. Read web/feat/streamer-mode.js fully (712 lines) and web/feat/live.js fully (383 lines).
3. `node --check web/feat/streamer-mode.js` and `node --check web/feat/live.js` - exit 0 both. The
   doubled backslashes shown by the file reader are display escaping; the regexes at
   streamer-mode.js:389 and live.js:77 are valid.
4. Page shells: `curl -s -o /dev/null -w "%{http_code}"` - /app/streamer = 200, /app/live = 200,
   / = 303 (redirect to the app, expected). Shell body read with curl: both serve the full
   PeakCut app shell (title, fonts, inline style, plugin boot).
5. Route verification - extracted every `/api/...` address from both owned files and confirmed each
   route exists in studio/*.py:
   - streamer-mode.js: /api/status (server.py:647), /api/jobs GET (826) and POST (860),
     /api/preview (839), /api/brand GET (api_brand.py:42) and PUT (48),
     /api/creators/{cid}/live (1354), /api/live/{jid}/clip (1382), /api/live/{jid}/stop (1373),
     /api/sync (814). All exist. 0 missing routes.
   - live.js: /api/hunt/watching (api_preview.py:135), /api/hunt/live (122),
     /api/hunt/watch (144), /api/hunt/unwatch (158). All exist. 0 missing routes.
6. Call signatures: P.api/P.send exist (web/plugins.js:258-259). `send(path, body, method="POST")`
   (web/index.html:1005) supports the `"PUT"` used by str_savehooks; `api(path, opt)`
   (web/index.html:999) throws with the server's `detail` sentence on non-OK.
7. Option keys: studio/jobs.py clean_options DEFAULTS/LIMITS (111-116) accept every key the page
   sends - max_clips, min_len, max_len, style, captions, range_start - and LIMITS match the page's
   own ranges exactly (max_clips 1-20, min_len 5-120, max_len 10-180; streamer-mode.js:373-382).
   Style "beast" is a real caption look (captions.py:21), "bounce" a real house look (render.py:24),
   both served by /api/status styles (server.py:655 via _caption_styles, 659-670).
8. /api/creators/{cid}/live channel semantics (server.py:1364-1366): a channel sent in the body is
   used only when it is one of that creator's saved channels, otherwise the creator's own channel or
   the on-air one is used. The page's comment (streamer-mode.js:551-552) matches.
9. /api/live/{jid}/clip seconds (server.py:1391): clamped to 5-180, default 30 - matches the page's
   fixed {seconds: 30}.
10. live.js platform names: studio/hunt.py PLATFORMS = ("twitch", "kick", "youtube")
    (hunt.py:16, _LOOK at 134) matches live.js NAME exactly.
11. Shared CSS classes used by both files exist in web/index.html: .row (184), .btn (203),
    .help (243), .pill (254), .hint (300), .set-sec (476), .err (549).
12. Contrast, measured from web/index.html:17-22 palette (dark theme): --text on --bg about 19:1;
    --dim on --bg 7.84:1, on --muted 7.48:1; --faint (#7C7C7C) on --bg 4.74:1, and
    web/feat/polish-contrast.js overrides --faint to #A0948C for #main,dialog (7.24:1 on --bg);
    --brand on --bg 8.47:1; --brand-deep on --bg about 11.2:1. Every ink in both owned files comes
    from these variables; neither file declares a raw hex colour. 0 low-contrast nodes found
    (all quiet text is 12px or larger and 4.74:1 or better, above the 4.5:1 bar).
13. Width and mobile: streamer-mode.js carries @media (max-width:680px) collapsing the mode grid and
    field grid to one column with full-width buttons (77-86); live.js carries @media (max-width:560px)
    (42-46); both form rows use flex-wrap. No element is wider than a 390px viewport.
14. Icons: every icon key used by the two files (video, rec, stop, play, x, warn, crown, bell, bolt,
    upright) exists in the `const I` map, web/index.html:931+.
15. Accessibility: the three live regions (#str_live, #str_summary, #pclive_list) carry
    role="status" aria-live="polite"; mode cards carry aria-pressed; both files style
    :focus-visible outlines.
16. Page lifecycle verified: web/plugins.js drawPage (124-141) rebuilds `view.innerHTML` fresh on
    every visit and re-runs the page's load(); web/index.html:1477 and 2533 call it on every route
    change and re-render. This is what makes finding 1 visible.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | web/feat/streamer-mode.js:487 (declared at 149) | "Recording now" section goes blank on every revisit after the first. paintResults builds `html`, then `if (html === lastLiveHtml) return;` quits before writing #str_live, #str_count and before paintCreators(). `lastLiveHtml` is never reset in load(), but the app rebuilds the page DOM fresh on every visit and re-render (web/plugins.js drawPage 124-141; web/index.html:2533), so the fresh empty #str_live is never filled when the job state has not changed. With zero recordings the html is constant, so after the first visit the section shows no rows, no "Nothing is being recorded right now." empty state and no count, indefinitely. | streamer-mode.js:487 `if (html === lastLiveHtml) return;`; :149 `let lastLiveHtml = "";` (only 3 occurrences: declare, compare, set - no reset); web/index.html:2533 `return PeakCut.drawPage(S.view);` rebuilds the DOM per visit | Reset the cache when the page is rebuilt: at the top of load() set `lastLiveHtml = ""`, or paint unconditionally when `at("str_live")` has no children |
| important | web/feat/streamer-mode.js:352-355 | Pressing the already-active mode card silently wipes every typed number. switchMode reads the draft, keeps only the URL (348), then `Object.assign(draft, START.live)` on the active-card branch. Clips, min/max length, style, minutes and hook words all revert to defaults with no message - the comment (356-357) says the feedback is the card unpressing and the summary line, but for the live card the mode stays "live", so nothing visible changes at all. The foot hint (606-607) invites exactly this press ("Press the mode that is on to turn it off again") without warning that typed numbers are lost. | streamer-mode.js:352-355 `if (mode === k) { mode = "live"; Object.assign(draft, START.live); ... }`; readDraft at 347 commits the typed values just before they are discarded | Keep the typed draft on the active-card press (clear the mode without Object.assign), or reset only fields that differ from the mode's defaults, or say what changed; at minimum do not drop values the user typed |
| minor | web/feat/streamer-mode.js:262-271 (str_chat), 272-278 (str_minutes) | Two dead controls: spike mode's "How loud chat must get" and catch mode's "Keep recording for at most, minutes" are never sent - the page's own hints admit "this box is not sent and changes nothing yet" (269-270) and "this box is not sent" (276-277). The hints do say so plainly, which is why this is minor, but a control that changes nothing is still a control a beginner will set and expect to work. | streamer-mode.js:269-270 and 276-277 hint text; no readDraft consumption outside display | Remove both fields until a route reads them, or make the routes read them |
| minor | web/feat/streamer-mode.js:686 | "Save these words to my brand" silently truncates: `.trim().slice(0, 120)` cuts typed hook words to 120 characters, and the success toast ("Saved. Every new clip will be told to look for those words.") never mentions the cut. A user typing 200 characters saves 80 without knowing. | streamer-mode.js:686 `String((box && box.value) || "").trim().slice(0, 120)`; toast at 696 | Trim to the limit in the input itself (maxlength=120 on #str_hooks), or say in the toast when words were dropped |
| minor | web/feat/streamer-mode.js:661-665 | The 2.5 s results timer is never cleared. load() sets `setInterval` on every visit and stores it on `paintResults.timer` without clearing the previous one, so each visit to the page stacks one more interval. The guard `at("str_live")` makes off-page ticks no-ops, so the cost is small, but the number of live timers grows with every visit for the whole tab session. | streamer-mode.js:661-665 interval assignment with no clearInterval anywhere in the file | `clearInterval(paintResults.timer)` at the top of load() before setting a new one |

## Usability

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| important | web/index.html:836 (hits both owned pages) | Every explanation vanishes on phones. index.html hides all `.hint` elements inside `@media (max-width:560px)`, and 390px is inside that range. On a phone the streamer form loses all of its field hints (URL, clips, lengths, style, chat, minutes, the gta-only "This one is real", "A note, not a filter", the creator select hint), and the Live page loses the Check now / Remove / Look again / channel-name hints. Controls that depend on their hint for meaning are left with none - the gta-only checkboxes and the brand-save button become unexplained toggles and buttons. | web/index.html:836 `@media (max-width:560px){... .hint{display:none} ...}`; streamer-mode.js carries 10+ .hint nodes in formHtml; live.js carries 4 | Keep hints readable on small screens (smaller size, block display) or move the essential explanation into aria-label/placeholder so the meaning survives |
| minor | web/feat/streamer-mode.js:543-564 (with server.py:1365-1366) | "Start recording" can silently record a different channel than the one the user typed. startReading reads the draft (which includes the URL box) and sends {channel: link}, but the route uses that channel only when it is already one of the creator's saved channels (server.py:1366), otherwise it falls back to the creator's own or the on-air channel with no message. The hint at 625-626 explains the general rule ("uses the creator's own saved channel and settings"), but not that a pasted link can be quietly ignored, and the UI reads like the link above is the input. | streamer-mode.js:551-552 code comment; server.py:1366 `url = asked if asked in c["channels"].values() else ...` | When the typed link is not a saved channel, say so in #str_lerr instead of falling back silently |

## What was clean

- Both pages return 200 and the shell loads plugins and feature files as designed.
- Every /api address in both files maps to an existing route; signatures and option keys match the
  server's own validation; the page's number ranges match jobs.py LIMITS exactly.
- live.js paints unconditionally and carries wait, empty, error and per-row states; both of its
  buttons and both flows are explained in plain language; it relies on the global esc from
  web/index.html:930, which resolves in the classic-script scope (verified).
- Contrast: 0 low-contrast nodes in either file; no raw hex colours; focus-visible outlines present.
- Mobile: mode/field grids collapse to one column below 680px; no 390px overflow.
- aria: live regions marked role=status, mode cards aria-pressed, icons all resolve.
