# nav-responsive

**What I built.** The left menu is now its own scroll area. Only the rows scroll. The logo, the search box and the account feet stay where they are. `#nav` got `padding-bottom: calc(18px + env(safe-area-inset-bottom))` so the last row always clears the bottom edge, and `scroll-padding-bottom` so a row scrolled to by the keyboard is not flush against it either. Below 900px the sidebar is already a fixed drawer, so the sidebar's own collapse button is shown again (the frozen page hides it at `@media (max-width:900px)`), and a capture-phase click listener turns it into the drawer toggle: it flips `open` on `#app` and never touches the page's own `mini` class at that width. Wider than 900px the listener returns immediately and the page's collapse logic runs untouched. The closed drawer is now `visibility:hidden` after it slides out plus `inert`, so the keyboard cannot walk into a menu nobody can see; Escape and the page's own scrim close it; the button carries `aria-expanded` and a label that says what it will do. A `MutationObserver` on `#app`'s class list keeps that label right when the page's topbar menu button opens the drawer instead.

**File I own.** `web/feat/nav-responsive.js` (112 lines). I edited no other file. `web/index.html` untouched.

**Commands I ran and what they said.**
- `node --check web/feat/nav-responsive.js` -> PARSE OK, exit 0
- `python tests/test_feat_files.py` -> `{"files": 26, "checks": 214}`, All checks passed.
- `python tests/test_menu_pages.py` -> All checks passed. 83 ok

**Skill used.** `frontend-design`.

**Not done.** I did not load the real page in a browser at 899px and 901px, so the drawer toggle is proven by the tests and by reading the frozen page's CSS, not by a live click. The sticky search box from `nav-search.js` sits at `top:0` inside `#nav` and keeps working because I only added padding, but I did not re-test it on a narrow window.
