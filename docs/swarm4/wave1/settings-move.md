# settings-move

**What I built.** `web/feat/menu-pages.js` adds four pages to the main menu: Brand at `/app/brand` (group
Make), Transcription at `/app/transcribe` (group Understand), Tools at `/app/tools` and Connected apps at
`/app/apps` (group Set up). Each has a name, a one-line tip and an icon that already exists in the icon map
(palette, microphone, wand, plug). Each page draws its own heading and an empty container, `#pcpg_brand`
and so on, then `load()` fills it with a card: a pill that says "Moved out of Settings", one plain sentence
what the setting does, a line saying the controls are still in Settings on that tab, and one button to
`/app/settings/<tab>`. The Transcription card first calls `PeakCut.state()`; a viewer who is not an owner
gets a sentence saying only an owner can change it and a button to `/app/settings` instead of a tab that
would not open for them. Nothing on these pages posts, saves or talks to the server.

**What is not done here.** The forms did not move. Each page explains the setting and hands you to the
right tab in Settings. The full move of the forms, and the redirects that keep old links working, is wave 4.

**File I own.** `web/feat/menu-pages.js` only. I did not touch `web/index.html` or any other agent's file,
and I created no other file.

**Commands and what they said.**
- `node --check web/feat/menu-pages.js` printed nothing and exited 0.
- `python tests/test_feat_files.py` ended `{"files": 24, "checks": 198}` then `All checks passed.` Exit 0.
  My file's own eight lines: parses, declares one plug-in, named after itself, only owner of menu-pages,
  does not write into the frozen page, escapes what it draws, uses no absolute origin, invents no clashing id.
- `python tests/test_menu_pages.py` ended `All checks passed. 53 ok`, counting `4 pages`. Exit 0. All four
  pages pass name, address, tip, group and icon, no shared address, no shared name, no built-in address taken.

**Skill.** `frontend-design`, as asked.
