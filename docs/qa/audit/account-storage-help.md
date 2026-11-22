# Audit: account / storage / help pages (agent-144)

Scope: pages `/app/account`, `/app/storage`, `/app/help` and files
`web/feat/menu-pages.js` (account and storage rows) and `web/feat/help.js`.
Method: static reading of the two owned files plus every file they depend on
(`web/plugins.js`, `web/index.html` drawers and routes, `studio/server.py`
routes, `studio/account.py`, `web/feat/polish-contrast.js`,
`web/feat/menu-icons.js`), and `curl` checks against
`http://127.0.0.1:8798`. No browser was used (the lead owns it during the
audit).

Severity follows docs/qa/CONTRACT.md: critical = broken control, 404 route,
text under 3:1, console error on load; important = wrong copy, cramped
layout, dead handler, missing empty or error state, hard to use; minor =
spacing, wording, polish.

## Pages and files owned

| What | Address / file | Check |
|---|---|---|
| Page | `/app/account` | curl 200 |
| Page | `/app/storage` | curl 200 |
| Page | `/app/help` | curl 200 |
| File | `web/feat/menu-pages.js` (250 lines, read fully) | `node --check` passes |
| File | `web/feat/help.js` (145 lines, read fully) | `node --check` passes |

## Checks run

1. **HTTP codes.** `curl -s -o /dev/null -w "%{http_code}"` on the three
   pages: 200, 200, 200. The server route is a catch-all
   (`@app.get("/app/{rest:path}")`, studio/server.py:438), so every
   `/app/*` address serves the shell by design; the curl body of
   `/app/help` is the real PeakCut shell.
2. **Syntax.** `node --check` on both owned files: both pass.
3. **Controls.** Traced every control the two files draw to its handler:
   the help questions (plain `<details>`, native toggle), the help "go"
   links (`a[data-hlp-go]`, handled in help.js:103-118, with a plain-href
   fallback for unregistered pages), the account/storage fills
   (menu-pages.js fill(), 82-123) into `drawSettingTab`
   (web/index.html:2538), and the security actions to their routes:
   `/api/auth/password` (server.py:610), `/api/auth/logout` (597),
   `/api/account/delete` (1160-1173), `/api/storage` GET (1695),
   `/api/storage/open` (1702), `/api/storage/pick` (1715),
   `/api/storage` PUT (1724). All routes exist; all handlers exist.
4. **Deep links.** A fresh direct visit to `/app/account`, `/app/storage`
   or `/app/help` is picked up twice: the boot block draws the overview
   first (index.html:3487, feature files not loaded yet), then
   `P.boot` re-reads the address and swaps to the right page
   (plugins.js:272-276). Verified the swap always happens for these three
   addresses (all three are registered; `pageFor` resolves once the
   feature files are in).
5. **Loading, empty and error states.** fill() shows `Loading…`
   (menu-pages.js:101), catches draw errors into a hint card (104-116,
   120-122), and `P.drawPage` toasts and logs if a page cannot finish
   loading (plugins.js:124-141). The storage drawer renders even when the
   drive is empty (percent guarded at index.html:2597 with a
   `s.total_gb ? ... : 0` fallback).
6. **Contrast.** Every text colour on the three pages was measured with
   `P.ratio` in polish-contrast.js and cross-checked by hand:
   `--text` on `--bg` 18.16, `--dim` 8.10, `--faint` as overridden to
   `#A0948C` 7.24 (the `#7C7C7C` fallback is 4.79). No text below 4.5:1,
   so nothing below 3:1. The answer border (`--brand-line`, about 1.6:1)
   is decoration, which WCAG 1.4.11 exempts.
7. **Small screens.** The frame hides `.hint` on phones
   (index.html:836), but every hint on these pages has a rule of its own
   that stays visible (`.pcpg .hint` at specificity 0,2,0 in
   menu-pages.js:14; `.hlp-open`/`.hlp-hint` display:block in help.js,
   injected after the static sheet so the later equal-specificity rule
   wins). The storage path code wraps (`overflow-wrap:anywhere`,
   index.html:506), so long Windows paths cannot overflow a 390px
   viewport. Headings drop to 20px under 560px in both files.
8. **Icons.** The Help row's icon is seeded by `web/feat/menu-icons.js`
   (SET.help at line 94, written into the live icon map at 100), and
   `navHtml` only draws an icon when one exists (plugins.js:78). Tests
   (`tests/test_a11y_pages.py`) confirm every icon-only button is named.
9. **Link targets.** All six help answers point at registered pages:
   `/app/videos`, `/app/apps`, `/app/improve`, `/app/ai-usage`,
   `/app/storage`, `/app/schedule`. None 404s, and the click handler only
   takes over when the address resolves to a real page (unknown addresses
   fall through to the plain href, which the shell can serve).

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| Important | `/app/account`, menu-pages.js:69 + 104-116 | On a default install (sign-in off, `accounts: false`) the Account page draws the Password, Sign out and Delete my account forms that Settings deliberately hides in that mode, and the destructive action always errors when pressed. | `two: ["profile","security"]` (menu-pages.js:69) is drawn unconditionally (104-116) while Settings hides both tabs when `S.status.accounts === false` (setTabs, index.html:2240-2241; server.py:652 returns `"accounts": config.ACCOUNTS`, false by default). The Password section's help paragraph is an empty string in that mode (index.html:2586), so the form has no explanation. Pressing "Delete my account" on a default install always ends in "Admin accounts can't be deleted. Make it a normal account first." (`if u.is_admin: raise Busy(...)`, studio/account.py:140-141). The moved copy says "the password you sign in with" (menu-pages.js:67) but nobody signs in on a default install. | In fill(), when `window.PeakCut.state().status.accounts === false`, draw only the profile tab plus one sentence, mirroring setTabs: "Sign-in is off on this PeakCut, so there is no password to change and nothing to sign out of." Keep the full security tab when accounts are on. |
| Minor | All three pages, plugins.js:280-281 + index.html:3487 | A fresh direct visit to `/app/storage`, `/app/account` or `/app/help` draws the full overview page (hero headline plus an overview API call) for about 1.4 seconds before the real page swaps in. | Feature files load on a 1400 ms timer (`setTimeout(..., 1400)`, plugins.js:280-281); before that, `fromPath` returns `["overview","clips"]` for these addresses and `go("overview")` draws the hero and calls `loadOverview()` (index.html:3487, 1470-1471, 1484). The loader then corrects itself (plugins.js:272-276). The comment at index.html:3488-3491 documents the tradeoff, but the flash misleads for a moment and wastes an overview load. | In the boot block, when `pathKnown(location.pathname)` is false, leave the view with a quiet "Loading" shell instead of drawing the overview hero until the loader corrects. (index.html is another agent's file in this wave.) |
| Minor | menu-pages.js:205, 223 | `admin: true` on the storage and AI page registrations is read by nothing, and the transcribe registration lacks the flag its own moved-table row carries. | `plugins.js` `P.page`/`navHtml` (58-106) never look at `p.admin`; admin-only rows show in every user's menu on purpose, and non-admins get the explained "Owner only" card (menu-pages.js:87-93), consistent with the `/api/storage` gate (`_admin(request)`, server.py:1698). The MOVED transcribe row says `admin:true` (line 29) but the transcribe registration (147-162) omits it, so the flag is not even a convention here. | Drop the unused `admin: true` from the storage and AI registrations (or honor it in navHtml to hide the rows for non-admins, which would be a behaviour change to weigh separately). |
| Minor | menu-pages.js:127, 63-70 | `tabs: ["brand","transcribe","tools","apps"]` in `P.add("menu-pages", ...)` and the account row's `what`/`cta` are never rendered. | plugins.js reads `about`, `tools`, `load`, `act`, `after` and `keys` from a plugin definition, never `tabs`. The account row carries no `admin` flag, so `fill("account")` never renders the "Owner only" card, which is the only place `d.what` is drawn (menu-pages.js:89); its `cta` ("Open Account in Settings") is likewise unreachable. | Drop the dead fields, or wire `tabs` into the plugin loader if it was meant to do something. |
| Minor | menu-pages.js:126 | The plugin's `about` string omits half of what the file puts in the menu. | The string is "Brand, transcription, tools and connected apps now open from the main menu." but the same file registers AI, Storage and Account rows too (198-232, 234-249). | "Brand, transcription, AI, storage, account and connected apps now open from the main menu." |
| Minor | help.js:47-49 | The media-query re-show of `.hlp-hint` is redundant, and the comment above it states a rationale that does not hold. | The base rule `.hlp-hint{display:block;...}` (line 40) already beats the frame's `.hint{display:none}` (index.html:836) on equal specificity, because the feature stylesheets are appended to the head after the static sheet (plugins.js:40). The comment says "The frame hides every .hint on a phone. These are the sentences that say where to go, so they stay." — the base rule, not the re-show, is what keeps them. | Drop the redundant `.hlp-hint{display:block}` inside the media query (keep the padding change), and correct or shorten the comment. |

## Checked and clean (no finding)

- All three page shells return 200 and are the real PeakCut shell.
- Both owned files pass `node --check`.
- No broken controls: every button, link and form on the three pages
  resolves to a real handler and route (checks 3 and 9 above).
- No console-error risk in the real load path: the feature files run after
  `window.PeakCut` exists (plugins.js:21), `esc`/`ic` are script-scope
  constants available to them, and both files escape the markup they
  interpolate (`esc()` on every user-facing string).
- Loading, empty and error states are present on every dynamic path
  (check 5 above).
- No text below 4.5:1 anywhere on the three pages (check 6 above).
- Nothing overflows a 390px viewport; the storage path wraps long Windows
  paths (check 7 above).
- The help answers are written in plain first-day language, name no
  invented numbers, and print no price for the AI (the cost answer points
  at `/app/ai-usage`, which counts calls and tokens, not money). This
  matches the repo rule that a number on the page has to come from
  somewhere.
- Deleting things is gated behind a typed confirmation on the page
  (index.html delaccount handler) and the server re-checks busy state
  (account.py:142-148), so the destructive flow cannot fire by accident.
