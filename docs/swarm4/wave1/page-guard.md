# page-guard

**What I built.** `web/feat/page-guard.js` holds two quiet guards and draws no page of its
own. The first is an address guard: when the bar points at `/app/<something>` that no
built-in view and no registered page owns, and `#view` would otherwise be left with the
frame's empty player, one line goes in above it: "There is no page at that address." with a
`Go home` link to `/app`. That link is a plain anchor with no `data-act`, because the frame
cancels the default for every anchor that carries one, and this link has to work when
routing is the broken part. A second sentence, "That page is not here.", covers the other
case, a view name nothing owns, for example a page file that failed to load. The line takes
itself back the moment something claims the view, and it never talks over a playing video.
The second guard is a duplicate guard: `PeakCut.page` is wrapped so that a name already in
`PeakCut._pages` costs exactly one `console.warn` for the life of the page. `PeakCut.pageGuard(name)`
is exported so a page file can ask before it registers, and with no argument it returns the
names already taken. 86 lines. The trigger is a `MutationObserver` on `#view` plus
`popstate`, not a timer: the `drawShell` after hook alone was not enough, because changing
view leaves the shell exactly as it was and the hook never fired again. I found that in the
browser, not by reading.

**The file I own.** `web/feat/page-guard.js` only. I did not edit `web/index.html` or any
other agent's file, and I created no other file.

**The commands I ran and what they printed.**

```
$ node --check web/feat/page-guard.js
NODE OK

$ python tests/test_feat_files.py
ok   page-guard.js parses
ok   page-guard.js declares one plug-in
ok   page-guard.js is named after itself
ok   page-guard.js is the only owner of page-guard
ok   page-guard.js does not write into index.html
ok   page-guard.js draws no markup
ok   page-guard.js uses no absolute origin
ok   page-guard.js invents no clashing id
{"files": 28, "checks": 230}
All checks passed.

$ python tests/test_menu_pages.py
All checks passed. 103 ok
```

Live, in the browser at `http://127.0.0.1:8798`:

```
open /app/this-page-does-not-exist   -> "There is no page at that address. Go home", link href "/app"
click that link                     -> lands on /app, the line is gone
go("nonsense-view")                 -> "That page is not here. Go home"
then go("library") / go("settings") -> no line, the note removes itself
three registrations of one page name, plus 60 drawShell() calls
                                    -> console.warn fired once
PeakCut.pageGuard()                 -> ["brand","analytics","transcribe","improve","tools","apps"]
```

**What I could not do, and one thing worth flagging.** I could not make the first paint
perfect: `stray()` stays silent until `PeakCut._booted` is true and `pathKnown` exists,
because before the frame has loaded its files every page address looks unknown, and a guard
that cries wolf on load is worse than no guard. In practice the note appears within a frame
or two of the first draw. Two limits are by design rather than omission: a duplicate is
reported once per name and never again, so a second duplicate later in the session is not
announced, and the duplicate guard only catches registrations that pass through
`PeakCut.page` after this file has loaded, which the loader order makes true in practice but
is not a guarantee across every future file. Finally, worth flagging outside my file:
`plugins.js` `P.page` silently filters the old entry before pushing the new one, so the first
file's page is destroyed with no trace. A duplicate is a build mistake that should gate the
tests, not just cost a console line. `tests/test_menu_pages.py` already forbids two pages
sharing a name among the files it walks, so the runtime warning is a backstop for a file the
test could not see, such as one added after the suite ran.

Skill loaded: `frontend-design`.
