# Fix wave: web/feat/menu-pages.js + web/plugins.js

Fixer agent-183. Scope: every finding under "## web/feat/menu-pages.js" and
"## web/plugins.js" in docs/qa/FINDINGS.md, verified against the source audits
(docs/qa/audit/apps-ai-usage.md, docs/qa/audit/x-console-risks.md,
docs/qa/audit/home.md) before any edit. 6 findings: 5 fixed, 1 skipped.

## Files owned

- `web/feat/menu-pages.js`
- `web/plugins.js`

Nothing else was edited. `web/index.html` was not touched (lead owns it).

## Fixes

### 1. [important] web/plugins.js:85 - the nav drawer ignored the admin flag, so non-owners landed on a dead end

Evidence held. The AI page (menu-pages.js:205 before the fix, now :200) and the
Storage page (menu-pages.js:223 before, now :218) register with `admin: true`,
because Settings itself keeps those tabs for an owner account
(`S.status.user?.is_admin`, web/index.html:2242). But the drawer read only
`if (p.hidden) continue;` (web/plugins.js:85) and nothing in web/ read
`p.admin` (grep). A signed-in non-owner saw both rows, pressed one, and landed
on the owner-only card in web/feat/menu-pages.js:86-93: a dead end with no form
to use. `studio/auth.py:244-254` forces the built-in owner's `is_admin=True`,
so default single-owner mode keeps both rows.

Fix: one guard beside the `hidden` skip, using the same key path Settings
checks, at web/plugins.js:84 and :90:

    const amOwner = typeof S === "object" && S && S.status && S.status.user && S.status.user.is_admin;
    ...
    if (p.admin && !amOwner) continue;

`S` is the same global navHtml already reads at :101 for the `on` highlight, so
no new import path; when the state arrives the repaint redraws the drawer, the
same way the badge and highlight already refresh.

Proof: `node --check web/plugins.js` (exit 0); read-only
`curl -s http://127.0.0.1:8798/api/status` shows `is_admin: True`, so the rows
still render in default mode; the guard only hides them for non-owners.

### 2. [important] web/feat/menu-pages.js:44 - apps page copy said "Each creator..." on a page that never shows a creator

Evidence held at the named line. Fix applied:

    what: "Press Connect, sign in on the platform's own page, and you come back here. PeakCut never sees your passwords. Then pick which accounts each channel posts to, in that channel's Setup on the Creators page.",

"Channel" is what the page actually shows (YouTube, Instagram, TikTok, Zernio
cards); the Creators page is real (`web/feat/creators.js` has the Setup button
and says "Setup opens that creator's own page: their channels, clip rules and
connected accounts.").

One nuance, recorded honestly: while verifying, `d.what` turned out to render
only inside the owner-only card (menu-pages.js:89), and the apps entry carries
no `admin` flag, so that card never fires for apps. The sentence a user
actually sees on the menu's Connected apps page comes from `web/index.html:2677`
("Then pick which accounts each creator posts to, in that creator's Setup."),
which is the lead's file. The dead copy in my file was still wrong data and the
fix costs nothing, so it is applied; the same wording in index.html:2677 needs
the lead's attention (same fix: name the channel and the Creators page).

Proof: `node --check web/feat/menu-pages.js` (exit 0); grep shows no
`Each creator picks` left in web/feat/menu-pages.js.

### 3. [minor] web/feat/menu-pages.js - the file's own metadata was four pages behind

Evidence held. `about` and `tabs` (menu-pages.js:126-127 before the fix) listed
brand, transcribe, tools, apps while the file registers seven pages (brand,
transcribe, tools, apps, ai, storage, account). The `tabs` key is consumed
nowhere in web/ (only an unrelated `.tabs` CSS class in index.html), and the
seven `cta` fields were read nowhere (`fill()` uses d.what/d.tab/d.icon/
d.admin/d.two/d.where only).

Fix applied at menu-pages.js:16, :122 and :123:

    // What each moved setting is and what the page promises. One table, seven pages, no drift.
    ...
    about: "Brand, transcription, tools, connected apps, AI, storage and account now open from the main menu.",
    tabs: ["brand", "transcribe", "tools", "apps", "ai", "storage", "account"],

and the seven unused `cta` lines are deleted.

Proof: `node --check web/feat/menu-pages.js` (exit 0); grep shows no
`cta: "Open` left in the file; `tabs:` lists all seven names.

### 4. [minor] web/feat/menu-pages.js:8 - the moved pages were 100px narrower than their sibling page

Evidence held. `.pcpg{max-width:780px}` (menu-pages.js:8) vs
`.usg{max-width:880px}` (web/feat/usage.js:12): both are menu rows drawing
settings-family forms, and moving between them resized the page. Both caps sit
inside the same container (`#main>.content` is 1480px via
web/feat/polish-wide.js:25), so the cap is the active constraint on both pages.

Fix (my file only; usage.js is not mine): `.pcpg{max-width:880px}` with a
comment naming the measured source, so the family keeps one width:

    /* 880, the Usage page's own cap (.usg in web/feat/usage.js), so the menu family keeps one width
     * measured against the same container (#main>.content is 1480px in web/feat/polish-wide.js). */
    .pcpg{max-width:880px}

Proof: `node --check web/feat/menu-pages.js` (exit 0); grep confirms
`.pcpg{max-width:880px}` and `.usg{max-width:880px}` now match. No colour was
changed, so no contrast ratio needed measuring.

### 5. [minor] web/plugins.js:153 - a one-sided handshake on a key nobody sets

Evidence held. `if (!b || b.dataset.pcDone === "1") return;` with the comment
"already handled by index.html": `dataset.pcDone` is set nowhere in web/ (grep
over web/ found only this check), so the second half was unreachable. Plugin
act names are unique, so removing it changes no behaviour.

Fix: the line is now just `if (!b) return;` and the stale comment went with it.

Proof: `node --check web/plugins.js` (exit 0); grep shows no `pcDone` left
anywhere in web/.

## Skips

### web/feat/menu-pages.js - cross-file helper load-order (files: menu-pages.js, menu.js, menu-icons.js, polish-empty.js, polish-loading.js)

Skipped: the evidence does not hold. The finding claims menu-pages.js calls
`P.menuGroup`/`P.icon` at module scope before their files load. Grep over web/
shows `P.menuGroup`/`P.menuGroups` are defined and called only inside
web/feat/menu.js (its own file, safe), `P.icon` is defined and called only
inside web/feat/menu-icons.js (its own file, safe), and menu-pages.js contains
no call to either (its only match for the search pattern was the word
`.admin`). The finding itself concedes "no runtime error today" and that a
grep of module-scope cross-file calls returns 0 hits. There is no bug in
menu-pages.js to fix.

## Gates run

- `node --check web/plugins.js` - exit 0
- `node --check web/feat/menu-pages.js` - exit 0
- `python tests/test_feat_files.py` - exit 0, 75 files, 606 checks, "All checks passed."
- `python tests/test_menu_pages.py` - exit 0, 439 ok, "All checks passed."
- `python tests/test_text_ink.py` - exit 0, 10 ok, "All checks passed."
- read-only `curl -s http://127.0.0.1:8798/api/status` - `is_admin: True`
  (no state changed on the running server)

## Notes for the lead

- `web/index.html:2677` carries the same "Each creator..." wording that
  finding 2 fixed in menu-pages.js. That file is yours; the fix is the same
  one sentence: name the channel and the Creators page.
- Fixed JS takes effect on the next page load; no server restart was needed
  and none was performed.
