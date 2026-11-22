# menu-core

**What I built.** `web/feat/menu.js` is the shared spine the rest of wave 1 calls. It does four
things and draws nothing: `PeakCut.menuGroup(name, order)` registers or moves a menu heading (memory
only, no server call); `PeakCut.menuGroups()` returns the headings in order with the top group `""`
first when a page really sits there; `PeakCut.pageRows()` returns every registered page as
`{name, nav, icon, tip, group, order}` sorted by heading then page order then arrival;
`PeakCut.groupFor(name)` returns the heading a page sits under, or `""`. Six headings ship by
default (`Make` 10, `Understand` 20, `Look and sound` 30, `Connect` 40, `Account` 60, `Help` 90) so
wave 1 agents have names to use without registering anything first; a later file can add or move
one. Two pages that both say `order: 20` keep the order they registered in, matching what
`plugins.js` already does. 81 lines. No page of its own, no visible UI, no Tools card markup.

**The file I own.** `web/feat/menu.js` only. I did not edit `web/index.html` or any other agent's file.

**The commands I ran and what they printed.**

```
$ node --check web/feat/menu.js
JS OK

$ python tests/test_feat_files.py
ok   menu.js parses
ok   menu.js declares one plug-in
ok   menu.js is named after itself
ok   menu.js is the only owner of menu
ok   menu.js does not write into index.html
ok   menu.js draws no markup
ok   menu.js uses no absolute origin
ok   menu.js invents no clashing id
{"files": 15, "checks": 126}
All checks passed.

$ python tests/test_menu_pages.py
ok   menu.js parses
ok   at least one page is registered   none yet, which is allowed: a build that adds no page adds no page
All checks passed. 19 ok
```

Note on the second gate: it reports zero registered pages because this file deliberately registers
none. That is the allowed case, and the check still parses my file.

Live, in the browser at `http://127.0.0.1:8798/app`:

```
window.PeakCut._order            -> contains "menu"
PeakCut.menuGroups()             -> ["Make","Understand","Look and sound","Connect","Account","Help"]
PeakCut.pageRows()               -> []          (nothing registered yet, correct)
typeof PeakCut.menuGroup         -> "function"   (all four are functions)
```

I also ran a throwaway probe (since deleted, it lived in `.local_tmp/`) that loaded the file in a
bare `vm` stub and checked 15 cases: sort order across headings, arrival order when two pages share
an `order`, a heading added and then moved without duplicating, a page naming an unregistered
heading sorting after the known ones, `groupFor` on a known page / a missing page / a page with no
group, and the fallback of `nav` to the page name and `icon` to an empty string. All passed. I
re-ran the same table against the live page registry and then restored the registry to empty.

**What I could not do.** One thing worth flagging rather than fixing, since it is outside my file:
`PeakCut.navHtml()` in `web/plugins.js` groups rows by `p.group` but never sorts by `order` across
groups and does not consult `menuGroups()`, so the menu can print the same heading twice if two
pages in the same group register apart, and a group can appear out of place. My `pageRows()` is the
sorted list that fixes that. Whoever owns `plugins.js` (or a later menu-drawing file) should draw
the menu from `PeakCut.pageRows()` and `PeakCut.menuGroups()` instead of walking `P._pages`, and use
`groupFor()` when it needs one row's heading. That is a change to a file I do not own, so I did not
make it.

Skill loaded: `frontend-design`.
