# tests-menu

**What I built.** I added four check families to `tests/test_menu_pages.py`, so the gate now
catches the menu mistakes before anyone opens a browser.

1. **Every page sits under a heading the menu knows.** `ALLOWED_GROUPS` lists the six headings
   from the spine in `web/feat/menu.js` (`Make`, `Understand`, `Look and sound`, `Connect`,
   `Account`, `Help`) plus `Set up`. A page under any other heading fails, and the failure line
   prints the whole allowed set beside the bad group, so the fix is on the screen:
   `FAIL cramped sits under a known heading   'Nonsense' is not one of: Make, Understand, ...`.
2. **A page address may not shadow another file.** A page at path `heard` would live at
   `/app/heard` while `web/feat/heard.js` is a different thing, which reads as a bug to anyone
   with the file open. The check collects the file names in `web/feat` and refuses a page whose
   path matches a file that is not the page's own. A file named after the page it draws is the
   normal shape and stays allowed: `analytics.js` owns the `analytics` page.
3. **The four moved pages still exist.** `brand`, `transcribe`, `tools` and `apps` must each be
   registered, and each needs a tip of at least 20 characters. A missing page means a feature
   slid back into Settings, which is the complaint this rebuild answers. A short tip means the
   menu row says nothing useful.
4. **A menu row has room for its label.** Every label is 1 to 18 characters, because a longer
   one gets cut off or wraps in the left column. Every label is unique, compared without case,
   so two rows cannot read the same and leave the person guessing which one they want.

`ALLOWED_GROUPS` is one tuple at the top of the file with a comment saying where the six names
come from. Add a heading to the spine and you add one word there. Nothing else changes. The file
still prints `ok` and `FAIL` lines and ends with `All checks passed.`, same as the rest of
`tests/`. It went from 118 to 172 lines.

**The file I own.** `tests/test_menu_pages.py` only. I did not edit `web/index.html` and I did
not edit any other agent's file. A full run went from 53 checks to 91.

**The commands I ran and what they printed.**

```
$ python -m py_compile tests/test_menu_pages.py
PY OK

$ python tests/test_feat_files.py
ok   loader keeps the documented folder
{"files": 27, "checks": 222}
All checks passed.

$ python tests/test_menu_pages.py
ok   there is at least one feature file   27 files
ok   analytics-audience.js parses
ok   analytics-charts.js parses
ok   analytics-kpi.js parses
ok   analytics-table.js parses
ok   analytics-traffic.js parses
ok   analytics.js parses
ok   autopilot.js parses
ok   day.js parses
ok   filters.js parses
ok   grid.js parses
ok   heard.js parses
ok   history.js parses
ok   keys.js parses
ok   log.js parses
ok   menu-icons.js parses
ok   menu-pages.js parses
ok   menu.js parses
ok   mood.js parses
ok   nav-responsive.js parses
ok   nav-search.js parses
ok   page-guard.js parses
ok   peek.js parses
ok   pill.js parses
ok   settings-explain.js parses
ok   stage.js parses
ok   stats.js parses
ok   style-tiles.js parses
ok   at least one page is registered   5 pages
ok   analytics says what to call it
ok   analytics says where it lives
ok   analytics has a one-line tip
ok   analytics has a group
ok   analytics has an icon the page knows   chart
ok   brand says what to call it
ok   brand says where it lives
ok   brand has a one-line tip
ok   brand has a group
ok   brand has an icon the page knows   palette
ok   transcribe says what to call it
ok   transcribe says where it lives
ok   transcribe has a one-line tip
ok   transcribe has a group
ok   transcribe has an icon the page knows   microphone
ok   tools says what to call it
ok   tools says where it lives
ok   tools has a one-line tip
ok   tools has a group
ok   tools has an icon the page knows   wand
ok   apps says what to call it
ok   apps says where it lives
ok   apps has a one-line tip
ok   apps has a group
ok   apps has an icon the page knows   plug
ok   no two pages share an address
ok   no two pages share a name
ok   analytics does not take a built-in address   analytics
ok   brand does not take a built-in address   brand
ok   transcribe does not take a built-in address   transcribe
ok   tools does not take a built-in address   tools
ok   apps does not take a built-in address   apps
ok   analytics sits under a known heading   Understand
ok   brand sits under a known heading   Make
ok   transcribe sits under a known heading   Understand
ok   tools sits under a known heading   Set up
ok   apps sits under a known heading   Set up
ok   analytics does not shadow a feature file   analytics
ok   brand does not shadow a feature file   brand
ok   transcribe does not shadow a feature file   transcribe
ok   tools does not shadow a feature file   tools
ok   apps does not shadow a feature file   apps
ok   brand is a page
ok   brand has a tip long enough to say something
ok   transcribe is a page
ok   transcribe has a tip long enough to say something
ok   tools is a page
ok   tools has a tip long enough to say something
ok   apps is a page
ok   apps has a tip long enough to say something
ok   analytics has a label a menu row fits
ok   brand has a label a menu row fits
ok   transcribe has a label a menu row fits
ok   tools has a label a menu row fits
ok   apps has a label a menu row fits
ok   analytics has a label of its own
ok   brand has a label of its own
ok   transcribe has a label of its own
ok   tools has a label of its own
ok   apps has a label of its own
ok   analytics.js draws its page
ok   menu-pages.js draws its page

All checks passed. 91 ok
```

A gate that only ever says `ok` proves nothing, so I checked that it fails. I copied the tree to
a throwaway folder and broke it on purpose. Each fault failed its own check and named the page:

```
FAIL catchall does not shadow a feature file   heard is already web/feat/heard.js
FAIL cramped sits under a known heading   'Nonsense' is not one of: Make, Understand, Look and sound, Connect, Account, Help, Set up
FAIL cramped has a label a menu row fits   25 chars, needs 1 to 18: 'Cramped beyond all reason'
FAIL twin has a label of its own   'brand' is on 2 pages
FAIL brand has a label of its own   'brand' is on 2 pages
8 check(s) failed
```

and, with the tip of the real `brand` page cut to one word:

```
FAIL brand has a tip long enough to say something   7 chars, needs 20: 'Colours'
1 check(s) failed
```

The probe folder is deleted. The real tree was never edited for these, only the copy.

**What I could not do.** One thing to flag, and it is in files I do not own.

`tools` and `apps` use the heading `Set up`, and `Set up` is not one of the headings that
`web/feat/menu.js` ships. Its table is `Make` 10, `Understand` 20, `Look and sound` 30,
`Connect` 40, `Account` 60, `Help` 90. An unknown heading ranks 500, so those two rows sort to
the bottom of the menu, under everything else, instead of sitting where they belong. My test
allows `Set up` today because refusing it would fail the four pages that already exist. The real
fix is one line in a file I was not given, either way: `menu.js` adds `["Set up", 50]` to its
table, or `menu-pages.js` moves those two pages under an existing heading. Whoever owns those
files should pick one. After that, drop `"Set up"` from `ALLOWED_GROUPS` in my file, or keep it
once the spine learns the name.

A second, smaller note. I first also checked that a page name is not a feature file name, then
removed it. Files are named after the page they draw, so that check would have failed good work
from later waves. The path check covers the confusion that matters.

Skill loaded: `frontend-design`.
