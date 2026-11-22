# docs-menu (agent-31)

What I built: `docs/menu.md`, one page that says what every left menu row is for. It has one
table of the rows that are in the rail today plus the rows this wave adds, with the group, the
address and one sentence each. Then "Where the settings went", which names the four things that
left Settings and the page each one now opens. Then "What still lives in Settings, and why",
which keeps AI, Storage, Profile and Security and gives the reason. It also records the two
things that are not finished: the four forms are still in Settings and are reached by a button,
and Analytics and Transcription both register with order 20, so those two rows can swap places
between reloads. I read `drawShell()` at `web/index.html:1293` and `setTabs()` at
`web/index.html:2211` before writing, so the rows and the Settings tabs are read from the code
and not remembered.

The file I own: `docs/menu.md`. I edited nothing else. I have no `.js` file, so `node --check`
had nothing of mine to check; both python gates run it over every feature file anyway.

The commands I ran and what they printed: `python tests/test_feat_files.py` printed
`{"files": 27, "checks": 222}` then `All checks passed.` `python tests/test_menu_pages.py`
printed `All checks passed. 91 ok`, over the five pages analytics, brand, transcribe, tools and
apps. Both exited 0. I also checked the page for em dashes, en dashes, emoji and the banned
marketing words; none are present.

What I could not do: I could not fix the duplicate order number at 20. That is a one word change
in `web/feat/analytics.js` or `web/feat/menu-pages.js`, and neither file is mine, so I wrote the
wobble down in `docs/menu.md` instead. The same goes for the Settings subtitle that still says
"Your profile, security and connected apps." It is drawn by the frozen `web/index.html`, so it
needs a feature file to override it or a wave 4 decision.
