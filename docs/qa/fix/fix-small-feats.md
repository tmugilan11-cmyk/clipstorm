# Fix report — fix-small-feats (agent-205)

Fix wave for PeakCut. Files owned: `web/feat/stats.js`, `web/feat/peek.js`,
`web/feat/clean-forecast.js`. No other file was written. The server was not
restarted and no route was changed, so nothing here takes effect until the
lead's final restart.

## Fixes

### web/feat/stats.js — vague "Numbers" summary, box tucked inside the Look pane (minor)

Finding: the summary text was "Numbers", and the box was inserted before
`.panel`'s first h3, which is `h3#ed_look` "Look" (web/index.html:2754) — so the
YouTube numbers sat inside the Look pane, above its own heading, reachable only
from the Look tab. The inline comment ("right under the score, above 'On the
video'") described an older layout.

Verified first: `panel.querySelector("h3")` really resolves to `h3#ed_look`,
because web/index.html:2752-2754 nests the panes (`div.ed-panes > div.ed-pane.on
[data-pane="look"] > h3#ed_look`) inside `.panel`. The evidence holds.

Applied (web/feat/stats.js:257-268):

1. Summary renamed to **"YouTube numbers"**.
2. The box is now anchored after `.ed-railnav` (`rail.insertAdjacentHTML("afterend",
   html)`), so it sits between the tab rail and the panes and shows on every tab.
   Fallback when no rail exists: top of `.panel` (still always visible — never
   inside a pane).
3. The stale comment replaced with one that says why the anchor moved.

Proof: `node --check web/feat/stats.js` exit 0; `python tests/test_feat_files.py`
606 checks all passed.

Known consequence, reported for the lead: `tests/test_clip_editor.py:138-141`
(`the_numbers_box_stays_with_the_look_controls`) asserts the literal
`'const head = panel.querySelector("h3")'` in stats.js — the exact anchor this
audit finding calls the bug. The test encodes the pre-audit behaviour and is
stale relative to the tab-rail layout it predates. It fails with that test file
now and needs its owner (or the lead) to update the assertion to the new anchor,
e.g. `panel.querySelector(".ed-railnav")` + `insertAdjacentHTML("afterend", html)`.
I did not edit that test: it is outside my file list.

### web/feat/peek.js — "Take stills" button 30 px tall (minor)

Finding: `.pcpeekbtn` had a literal `height:30px` (web/feat/peek.js:25), below
the 44 px tap target on small screens. Evidence verified: the literal is there.

Applied (web/feat/peek.js:31-35): added

```css
@media (max-width:640px){
  .pcpeek .pcpeekbtn{min-height:44px}
}
```

`min-height` wins over the existing `height:30px`, so the desktop size is
unchanged and the phone button grows to 44 px. The existing container query at
web/feat/peek.js:24 already drops the times row when the card is very narrow.
No colour was touched, so no contrast measurement was needed.

Proof: `node --check web/feat/peek.js` exit 0; `python tests/test_feat_files.py`
all passed (peek.js section).

### web/feat/clean-forecast.js — failed words fetch worded as "no timings" (minor)

Finding: `wordsFor` ended in `.catch(() => [])`, so a fetch the server did not
answer yielded the same empty array as a clip with no transcript, and `say()`
printed "PeakCut has no word timings for this clip yet…" — a claim the server
never made. Evidence verified at web/feat/clean-forecast.js:44 (old line).

Applied (web/feat/clean-forecast.js:28-49 and :91-97):

1. The cache carries a `failed` flag; the catch sets
   `cache = { key, words: [], failed: true }`.
2. `say()` checks the flag against this clip's key and prints
   **"The word timings could not be read. Try again."** instead of the
   no-word-timings claim. The truthful empty-state copy is unchanged for a clip
   that genuinely has no timings.
3. A failed ask is not kept: the cache-hit guard skips entries marked `failed`,
   so the next switch flip or dialog redraw asks again and "Try again" is a real
   instruction, not a dead end.

Proof: `node --check web/feat/clean-forecast.js` exit 0;
`python tests/test_censor_cleanup.py` all checks passed (including its three
clean-forecast.js checks); `python tests/test_feat_files.py` all passed.

## Skips

None of the three findings was skipped — all evidence held and all were fixed.

Two observations outside my ownership, for the lead:

1. `tests/test_clip_editor.py:138-141` is stale (details under the stats.js fix
   above). Its assertion names the old anchor; the fix followed the audit.
2. `python tests/test_text_ink.py` fails on
   `web/index.html .pill.live (behind it: var(--live))` — web/index.html:258
   `.pill.live{color:var(--brand-ink);background:var(--live)}`. That file is the
   lead's and I did not touch it; my three files contain no `.pill` or `--live`
   (grep over all three, 0 matches), so this failure is not from this fix wave's
   three files.

## Gates run

- `node --check web/feat/stats.js` — exit 0
- `node --check web/feat/peek.js` — exit 0
- `node --check web/feat/clean-forecast.js` — exit 0
- `python tests/test_feat_files.py` — 606 checks, all passed
- `python tests/test_censor_cleanup.py` — all checks passed
- `python tests/test_clip_editor.py` — 1 failure: stale assertion on the old
  stats.js anchor (see above; not caused by the fix's logic)
- `python tests/test_text_ink.py` — 1 failure, entirely in web/index.html
  `.pill.live`, a file this agent never wrote
- Route existence re-checked by grep: `/api/stats/video` (studio/api_stats.py:71),
  `/api/jobs/{jid}/peek/{cid}` (studio/api_preview.py:101),
  `/api/jobs/{jid}/clips/{cid}/words` (studio/api_text.py:279) — none changed.
