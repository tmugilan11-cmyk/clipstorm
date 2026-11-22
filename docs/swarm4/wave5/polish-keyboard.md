# polish-keyboard

File I own: `peakcut/web/feat/polish-keyboard.js`. No other file was touched.

## What I added

`?` opens a panel listing every key PeakCut really answers, read out of the
files (`keys.js`, `index.html`, `filters.js`, `nav-search.js`,
`analytics-help.js`, `analytics-retention.js`, `live.js`, `day.js`, `stats.js`,
`nav-responsive.js`), never invented. 8 groups, 24 rows.

Escape closes the newest open panel, one press one thing. When something of the
page's own is open (a dialog, the notification or account menu, a dropdown, the
narrow-window menu) my handler stands back and lets that handler work.

Focus never lands on a hidden control. A `focusin` guard checks the control and
every parent for `inert`, `aria-hidden`, `display:none`, `visibility:hidden` and
a zero-size box, and moves the caret to the next visible control instead.

A Tools card ("Show all keys") opens the same panel for anyone who does not know
the `?` key exists.

## node --check

```
$ node --check web/feat/polish-keyboard.js
node --check: PASS
```

No output, exit code 0. Tests: `{"files": 59, "checks": 478}` then
`All checks passed.`

## What I measured, with real numbers

- Panel: `?` gives `hidden=false`, `role="dialog"`, 8 groups, 24 rows, 24
  `<kbd>`, focus on the close button, and focus returns to where it came from.
- Escape ordering: panel and notification menu both open, first press closed
  only the menu, second only the panel. One press used to close both.
- Tab, pressed for real 20 times: 20 stops, 0 on a hidden control. 5 more inside
  the tour: 6 stops, 0 hidden, focus never left the card.
- Page census: 100 focusable controls, 64 hidden at rest, 56 of those already in
  `[inert]`. The other 8 are the ones my guard covers.
- Review page: `a` 0/1 to 1/1 Approved, `x` to Rejected, `Enter` to Approved,
  `Backspace` to Rejected, `s` stayed 0/1 (skips only, as the panel says).
- Filter box: typed "speech", Escape emptied it, focus stayed. Menu search:
  "abc" emptied and dropped focus. Live: Enter added "somechannel" and cleared.
  Link box: Enter cleared and took the link. Analytics: Escape closed the note.
  Tour: Right and Left moved, Escape removed it.
- `?` does nothing while the caret is in a field, so it stays typeable.

## What is still missing

`Enter` on the Schedule page does not fire: `schedule.js` answers it from
`keys()`, and the loader skips `keys()` for an INPUT target. That row is left out
of the panel rather than listed as a key that does nothing. The same skip makes
the "Charts" rows depend on the chart wrapper, which was empty on this data.
`.pick` computed `visibility:hidden` even with `.open`, so that row was proven by
its handler, not its pixels.
