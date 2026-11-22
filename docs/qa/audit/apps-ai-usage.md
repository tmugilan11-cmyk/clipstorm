# Audit: apps / ai / ai-usage (agent-143)

Audit wave for the Connected apps page, the AI settings page and the AI usage page,
plus the two files that draw them. Follows docs/qa/CONTRACT.md.

## Pages and files owned

- Pages: /app/apps, /app/ai, /app/ai-usage
- Files: web/feat/menu-pages.js (the apps and ai rows), web/feat/usage.js

## Checks run

1. Read docs/qa/CONTRACT.md (binding rules) and loaded the systematic-debugging skill.
2. Page shells over HTTP against http://127.0.0.1:8798:
   - /app/apps -> 200, /app/ai -> 200, /app/ai-usage -> 200. No 404 or 500.
3. Read both owned files fully: web/feat/menu-pages.js (250 lines), web/feat/usage.js (295 lines).
4. Read web/plugins.js fully (282 lines) to check how PeakCut.page, the nav drawer,
   data-act dispatch and page load errors are handled.
5. Verified every route the files use exists in studio/:
   - GET /api/usage -> studio/server.py:1398 (open to all users; no _admin gate).
   - The usage page uses no other /api route. The menu pages draw the real Settings forms,
     which call /api/ai, /api/apps, /api/zernio, /api/accounts; each of those exists in
     studio/server.py and the failure paths are caught in the drawing code.
6. Verified the globals the files rely on exist in web/index.html:
   const esc (index.html:930), const ic (index.html:992), async drawSettingTab (index.html:2538),
   and the CSS classes .err (549), .set-load (480), .set-sec (476), .pill.warn (257). All present.
7. Read the response shape the usage page draws from: studio/usage.py summary() (lines 70 to 97)
   and brief() (lines 52 to 67). Confirmed keys: ready, provider, model, today_calls,
   today_tokens, problem, calls_total, tokens_total, daily (30 days, ends today),
   by_purpose (unlimited, ordered by tokens desc), by_creator, recent.
8. Checked the counter-evidence for the "one model" claim: usage.forget_all() (studio/usage.py:39-41)
   only clears the _brief cache; call rows persist across provider switches.
9. Read the palette (web/index.html:17-30) and web/feat/polish-contrast.js fully, and computed
   the WCAG ratios for every colour pair the two files resolve:
   - --text #F5F5F5 on --bg #0A0A0A = 18.16 (headings, figures) - passes
   - --dim #A3A3A3 on --bg = 8.10 (.usg-k, .usg-svc) - passes
   - --faint #A0948C on --bg = 7.24 inside #main (runtime override, polish-contrast.js:29) - passes
   - --line-2 #2A2A2A on --bg #0A0A0A = 1.38 (chart zero-tick fill and baseline stroke) - fails 3:1 for graphics
10. Narrow-viewport check from CSS: .content padding 20px 16px at 640px and below (index.html:830),
    main#main overflow-x hidden (index.html:873), .usg-ledger collapses to one column at 700px
    (usage.js:59-64), the chart svg scales through viewBox (usage.js:33). No element exceeds a
    390px viewport. Text colors in both files sit inside #main, so all text passes 4.5:1.
11. Console-risky scan: no bare network calls without catch, every err.message is escaped through
    esc before it reaches markup, state() is wrapped in try/catch, drawSettingTab is type-checked.
    plugins.js catches page load errors and toasts. No console error on load expected.
12. Controls: the Refresh button (data-act="usgload") routes through plugins.js wireActs to
    P.usage.act.usgload (usage.js:271) - handler exists and is wired. The page has loading,
    error and empty states (usage.js:252, 258, 265, 228).
13. Checked whether the `tabs` metadata and the MOVED `cta` values are consumed anywhere:
    grep over web/ finds only the unrelated .tabs CSS class (index.html:244) and .sinfo .cta CSS.
    Both are dead data in menu-pages.js.
14. Checked id clashes: no pcpg_ id exists in index.html.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | web/feat/usage.js:220 | Wrong copy: "One model answers every call listed below" is a claim the data does not support. The sentence shows the current model, but call rows persist across provider switches, so older calls may have been answered by other services. In the empty state the same sentence sits directly above "No AI call has been made yet.", so nothing is listed below. | usage.js:220 prints the sentence from the current model only (studio/usage.py:63 takes (ai.models() or [""])[0]); usage.forget_all() (studio/usage.py:39-41) clears only the _brief cache, and the same response computes by_creator from history (studio/usage.py:79-83, 96), which exists because several creators can appear in it. | Say what is true: "The service in use now answers new calls." Or render the by_creator split the route already sends. |
| important | web/feat/menu-pages.js:205, 223 | Dead admin key: the ai and storage page registrations pass admin: true, but nothing reads it, so non-owner users see "AI" and "Storage" menu rows that end in the "Owner only" card - a dead end. Settings itself hides Storage from non-admins, so the menu and Settings disagree. | menu-pages.js:205 and 223 set admin: true; the nav drawer reads only p.hidden (web/plugins.js:85) - no p.admin anywhere in web/. Settings gates storage on is_admin (web/index.html:2242). With PEAKCUT_ACCOUNTS=1 a standard user lands on the owner-only card (menu-pages.js:87-93). | Have the nav drawer skip rows where p.admin is set and the signed-in user is not an owner (one check beside plugins.js:85), or drop the dead key and document that the fallback only fires after the click. |
| important | web/feat/usage.js:35, 157-158 | The zero-token tick is invisible: a day the route reported as zero is drawn as a 2x1 px rect filled with --line-2, which measures 1.38:1 against the chart background, below the 3:1 WCAG 1.4.11 minimum for meaningful graphics. The tick's stated purpose, that the row of days must not read as a shorter week, cannot work at that contrast. The chart baseline uses the same pair. | .usg-plot .none{fill:var(--line-2)} (usage.js:35) and .base{stroke:var(--line-2)} (usage.js:36); --line-2 is #2A2A2A and --bg is #0A0A0A (web/index.html:19). Ratio = (0.02316+0.05)/(0.00304+0.05) = 1.38. Tick is 2 px wide, 1 px tall (usage.js:158). | Fill the tick and stroke the base with a colour at 3:1 or better on --bg, measured: --faint #A0948C is 7.24:1, --dim #A3A3A3 is 8.10:1 (measured in polish-contrast.js:11-13). |
| important | web/feat/menu-pages.js:44 | Usability: "Each creator picks its own accounts in that creator's Setup." Nothing on the Connected apps page is called a creator; the page shows YouTube, Instagram, TikTok and Zernio cards. A beginner cannot connect the sentence to anything on the page in five seconds. | menu-pages.js:44; the drawn page content is the four app cards (web/index.html:2678-2682). "Creator" is PeakCut-internal vocabulary (channel identities) that this page never introduces. | Name the object: "Then pick which accounts each channel posts to, in that channel's Setup on the Creators page." |
| minor | web/feat/usage.js:196 | Purposes beyond the 8 largest are dropped with no note. The server sends every purpose ordered by tokens; a person with 10 purposes sees 8 and the rest vanish silently. | usage.js:196 got.slice(0, 8); studio/usage.py:76-78 sends all purposes with no cap. | After the rows, add a quiet line "and N smaller purposes" when got.length is greater than 8. |
| minor | web/feat/usage.js:121 | The exact token total is reachable only by hover: the visible figure is abbreviated and the exact count sits in a title attribute, which a touch screen cannot show. | usage.js:121 puts exact(toks) in title; the visible value comes from tokens() (usage.js:86-88), which abbreviates anything over 10,000. | Move the exact count into the .usg-sub line: "12,345,678 exactly, read in and written out together". |
| minor | web/feat/usage.js:277 | The nav tooltip promises "and what it cost", but the page's central card answers the cost question with "Not known" and refuses to print a figure. A beginner who hovers the row expects a number the page will not give. | usage.js:277 tip: "How much AI was used, and what it cost" against usage.js:125-127 ("Not known ... any figure printed here would be a guess"). | Change the tip to "How much AI was used, in calls and tokens". |
| minor | web/feat/usage.js:216 | "Add one under AI in Settings" is advice a standard user cannot follow: /api/ai is admin-gated and the AI settings tab is owner-only, so with accounts on the link leads to a 403. | usage.js:216; studio/server.py:1411 calls _admin(request) before returning ai.public(); menu-pages.js:51 marks the AI tab admin. menu-pages.js:90 already has the right phrasing: "Ask the owner of this PeakCut." | For non-admins say "Ask the owner to add one under AI in Settings." |
| minor | web/feat/usage.js:185 | The chart labels only the first and last of up to 30 days, and the per-bar dates live in hover-only title attributes, so on a touch screen the middle days carry no readable date at all. | usage.js:185 draws exactly two axis spans for rows.length days; the dates are in rect title elements (usage.js:163). | Label every 5th day (or first, middle, last) in the .usg-axis row. |
| minor | web/feat/usage.js:4 | Stale pointer: the header comment cites studio/server.py:1374, but the route is at studio/server.py:1398. | usage.js:4 vs studio/server.py:1398. | Update the comment to 1398. |
| minor | web/feat/menu-pages.js:127 | Stale, dead metadata: tabs lists four pages but the file registers seven (brand, transcribe, tools, apps, ai, storage, account); the tabs key is consumed nowhere in web/, the about line is equally stale, and the cta values in the MOVED table are never read (the fallback uses d.where). | menu-pages.js:127 tabs and about; grep over web/ finds only the unrelated .tabs CSS class (web/index.html:244); the fallback builds its link from d.where (menu-pages.js:98), never d.cta. | Update the list to the seven pages, or drop the dead tabs key and the unused cta fields so the metadata matches what the file registers. |
| minor | web/feat/menu-pages.js:8, web/feat/usage.js:12 | Sibling pages disagree on width: every menu settings page is capped at 780px while the Usage page is capped at 880px, so pages in the same family change width when you move between them. | menu-pages.js:8 .pcpg{max-width:780px} against usage.js:12 .usg{max-width:880px}. | Pick one width for the settings-family pages, measured against the same container. |

## What passed

- All three page shells return 200.
- Every /api route used by the two files exists in studio/ and the failure paths are caught.
- All text colours resolve to 4.5:1 or better inside #main; headings and figures are 18.16:1.
- No element exceeds a 390px viewport; the ledger stacks and the chart scales.
- The Refresh control is wired, and the usage page has loading, error and empty states;
  the menu pages have owner-only and older-shell fallbacks instead of empty boxes.
- Every server string reaches markup through esc; no console-risky code found.
