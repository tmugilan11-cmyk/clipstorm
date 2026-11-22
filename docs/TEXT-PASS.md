# One more pass over the text, and the two faults it found

Written 2026-11-21. The user's first complaint on this round was "the menu has some serious visual bugs in text".
Earlier passes fixed the dark ink painted on the dark page and one clipped tab strip. This pass swept every page with a
real contrast measurement instead of reading the CSS, and found two faults that a reader could actually see.

## How it was measured

A probe walks every text node in the document, takes its computed colour, walks up the DOM to the first background that
is at least 90 % opaque, and works out the WCAG 2.2 ratio `(L1 + 0.05) / (L2 + 0.05)`. Big text is judged against 3.0
and everything else against 4.5. It also flags any element whose `overflow` hides content it cannot show. A container
that scrolls on purpose is fine; one that hides text is not.

The probe is in this session's notes rather than in the repo because the browser here is driven directly; the two
regression checks that matter live in `tests/test_text_ink.py`, which reads the stylesheets instead of a browser, so
`python tests/run.py` catches both.

## Fault 1: the contrast sheet was written for a white page

`web/feat/polish-contrast.js` was added when the page was white, and it forced `--faint` to `#75695F` so a quiet grey
would clear 4.5 on white. The page is black now (`--bg #0A0A0A`), and on black that value measures **3.72:1** - it fails
for every `.hint` on every page. It was the single biggest source of unreadable text: 20 nodes on the Brand page alone,
and the same lines appear on all the other pages.

On a dark page the quiet levels run the other way: a quiet grey has to be **lighter** than the body ink, not darker.
`#A0948C` - the palette's own warm grey - measures 7.24 on `#0A0A0A`, 6.86 on `--muted #111111` and 5.68 on
`--brand-soft #2A1B10`, so it clears every surface that actually carries text, and it keeps the page warm.

Every number is now written into the sheet's own header comment so the next person can check it rather than trust it.

## Fault 2: the unread count was white on a red that is too light

`.bell .dotn` in `web/index.html` paints the unread count: white on `#E5323F` is **4.32:1**, and 10 px bold needs 4.5.
The options were worked out rather than guessed:

| ink | on `#E5323F` |
|---|---|
| white | 4.32 |
| the brand ink `#160D05` | 4.44 |
| black | 4.86 |

and the badge itself must also read against the page (3.0 as a control). `#C81E28` gives white **5.72** and the badge
**3.46** against `#0A0A0A`, which is the only combination that clears both bars. The colour is changed where it is
painted, not overridden from the feature file, because a colour written in two places drifts.

## What the sweep says now

Every page in the app, measured after both fixes: **0 low-contrast nodes, 0 clipped-text nodes.**

`/app`, `/app/videos`, `/app/review`, `/app/creators`, `/app/live`, `/app/streamer`, `/app/audio`, `/app/sounds`,
`/app/formats`, `/app/analytics` (which is the Insights page), `/app/improve`, `/app/transcribe`, `/app/brand`,
`/app/tools`, `/app/schedule`, `/app/apps`, `/app/ai`, `/app/usage`, `/app/account`, `/app/storage`, `/app/help`.

The sidebar on its own: 26 rows, none clipped, no empty heading, and the column measures exactly its own height (no
hidden scrolling). Its quiet text - the group headings, "nothing found", the small print - measures 5.55 to 6.08.

## Gates

`python tests/test_feat_files.py` - 75 files, 606 checks, all passing.
`python tests/test_text_ink.py` - 7 checks. It fails if dark ink comes back onto the page colour, and it follows the
parent rule so `.nav-item.on svg` is judged against its own orange background.
`python tests/test_clip_editor.py` - 14 checks, including the strip that must wrap rather than hide its last tab.
`node --check` clean on the page's extracted largest script and every `web/feat/*.js`.
All **41** offline suites pass. The five server-backed scripts and their two known environmental failures are
unchanged: `test_load_queue.py` on a machine limited to about 40 % of its advertised cores, and `test_updates.py`
because this copy has no `.git` folder.

## Three more faults the screenshots found

Reading the CSS said the page was clean; looking at it said otherwise. A screenshot of All videos and one of Audio
turned up three faults the measurement could not see, because none of them is a contrast ratio or a hidden overflow.

**The sidebar was slicing its own last row.** Six headings and 22 rows came to 1004 px inside a 897 px nav, and the
nav's scrollbar was hidden (`scrollbar-width:none`), so "Account" was cut in half at the bottom edge with nothing to
say there was more below. The nav now fits: heading padding 14/4 to 6/1, a row 34 px to 30, the gap 2 px to 1, which
brings 1004 to 897 exactly. The scrollbar is `thin` with a colour, so if a future change does overflow, it looks like
a list that scrolls rather than a broken edge.

**Two controls were labelled with each other's words.** The Audio page's name box read "Shortest" and the length
select read "Longest", which is a filter bar describing something other than what it filters. The box is "Find" now;
"Longest" stays on the select, where it belongs.

**Every catalogue card claimed a length of `0.0s`.** `/api/memesounds/trending` sends no `seconds` - the catalogue
lists names, not durations, and only a sound already on this machine has a length. `secs1()` did
`(Number(n) || 0)` and printed the fallback, so a sound nobody has downloaded said it was zero seconds long. That is a
claim about the sound, and it was wrong. A length is now drawn only when the catalogue gave one, and a row with no
length shows a small globe: this one is in the catalogue and not on this machine yet. Measured after: 10 catalogue
rows, 10 globes, 0 zeros.

## Gates after all three

All **41** offline suites pass, `test_feat_files.py` 75 files / 606 checks, `test_audio_page.py` 9 checks,
`node --check` clean on the page's extracted largest script and all 75 feature files.

## And one stacking/contrast fault in the clip editor

The editor screenshot showed the page's own buttons and sidebar apparently drawn on top of the dialog. Measured, the
dialog is a real modal and sits in the top layer, so that was not stacking: the **backdrop** was
`rgba(14,12,11,.42)`, which on a white page reads as 42 % of the light removed, but on a black page removes almost
nothing you can see. The page beside a 1560 px dialog therefore looked like part of it. It is `rgba(0,0,0,.72)` now,
which is dark enough that the page behind reads as out of play.
