# QA audit — Creators page (`/app/creators`) and `web/feat/creators.js`

Audit wave, 2026-11-22. One auditor's report per the contract in `docs/qa/CONTRACT.md`.

## Files and pages owned

- PAGE: `/app/creators` (shell + feature-drawn view)
- FILE: `web/feat/creators.js` (299 lines, read in full)

## Checks run

1. **Page shell over HTTP** — `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/creators` → **200**.
2. **Full read of `web/feat/creators.js`** (lines 1-299) — CSS block, helpers (`num`, `count`, `at`, `handleOf`, `face`, `chips`, `accountLine`, `trackLine`, `clipsLine`, `card`), `paintEmpty`, `paint`, `load`, `P.page` registration, `P.add` plugin.
3. **Every route the feature calls exists in `studio/`**:
   - `GET /api/creators` — `studio/server.py:1315`
   - `GET /api/creators/{cid}/avatar` — `studio/server.py:1302`
   - `GET /api/overview` — `studio/server.py:1606` (sends `creators[].id` and `creators[].clips_total`, `studio/posting.py:263-267`)
   - `GET /api/accounts` — `studio/server.py:1625` (sends `id`, `label`, `name`, `platform`, `studio/accounts.py:315-320`)
4. **Response shape vs. what the file reads** — `_creator_rows()` (`studio/server.py:789-796`) sends `{**creator, live_job, log}`; creator carries `name`, `channel`, `channels`, `accounts`, `profile` (singular, set at `studio/creators.py:178`), `id`. `face()` guards `prof.pic && prof.channel && prof.channel === c.channel`; the avatar route's default platform key (`server.py:1307`) matches that guard. All consistent.
5. **Handlers for every `data-act` the file paints**:
   - `data-act="newcreator"` → `web/index.html:3227` (opens the New creator dialog)
   - `data-act="go" data-v="c:<id>" data-tab="setup"|"clips"` → `web/index.html:3113` (`go(d.v, d.tab)`), `go()` at `index.html:1461-1463` falls back to overview for unknown creator ids; tabs `setup`/`clips` are valid creator tabs (`index.html:1490`)
   - `data-act="creators_reload"` → the file's own plugin act (`creators.js:294`), routed by `web/plugins.js:161-167`
6. **Routing** — `/app/creators` resolves through `fromPath` → `PeakCut.pageFor` (`web/index.html:1439`), drawn via `PeakCut.drawPage` (`index.html:1477`); boot-time re-read in `web/plugins.js:272-277`.
7. **Registration conventions** — ran `python tests/test_menu_pages.py` and `python tests/test_feat_files.py`: every `creators` check **ok** (parses, names itself, group "Make" is allowed (`tests/test_menu_pages.py:26-28`), icon `user` exists in the page's map, no id clash, escapes markup, no absolute origin, one plug-in).
8. **Syntax** — `node --check web/feat/creators.js` → OK.
9. **Contrast, measured** (WCAG 2.2 formula `(L1+0.05)/(L2+0.05)`, script `docs/qa/audit/_contrast_creators.py`):
   - `--text #F5F5F5` on `--bg #0A0A0A` → 18.16 (names, values)
   - `--dim #A3A3A3` on `--bg` → 7.85 (lede, handles in values); on `--muted #111111` → 7.49 (chips)
   - `--faint` resolved to `#A0948C` inside `#main` by `web/feat/polish-contrast.js:29` → 6.70 on `--bg`, 6.39 on `--muted` (all quiet text: labels, handles, "Not set", foot) — passes; even the `:root` fallback `#7C7C7C` measures 4.74/4.52, still above 4.5
   - `--brand-deep #FFB27A` on `--brand-soft #2A1B10` → 9.43 (main chip, avatar letter)
   - **`#FFFFFF` on `--live #EF4444` → 3.76 — fails the 4.5 required for the 12px "Recording" pill** (finding 1)
   - proposed fix `--brand-ink #160D05` on `#EF4444` → 5.10 — passes
10. **390px viewport** — content width 390 − 28 = 362px (`.content{padding:20px 16px}` at ≤640px, `web/index.html:830`); the ≤560px media query in `creators.js:61-66` collapses the grid to one column and the rows to one column; `main#main{overflow-x:hidden}` (`web/index.html:873`). No element wider than the viewport.
11. **States** — loading (`cr-wait`, `creators.js:222-224`), empty (`paintEmpty`, `creators.js:181-193`), read-failure (`creators.js:205-213`, with a Try again button), partial-failure notes (`creators.js:239-250` + `cr_err` at line 201, plus a toast when the list is empty) — all present.
12. **Hypothesis disproven** — line 89's trailing-slash strip: raw bytes are `replace(/\/+$/)` (single backslash, forward slashes), correct; not a bug.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| important | `web/feat/creators.js:162` (pill painted here; rule lives in `web/index.html:258`) | The "Recording" pill fails WCAG AA: white text on the live red at 3.76:1, below the 4.5:1 required for 12px text. It is the page's only live-status indicator, shown on every card of a creator that is recording. | `.pill.live{color:#fff;background:var(--live)}` (`web/index.html:258`), `--live:#EF4444` (`web/index.html:21`); measured #FFFFFF on #EF4444 = 3.76 (script `docs/qa/audit/_contrast_creators.py`); 12px semibold is not big text, so 4.5 applies. | In `web/index.html:258` draw the dark ink on the red, the same fix the bell unread count got (pattern documented in `web/feat/polish-contrast.js:17-19`): `--brand-ink` measures **5.10:1** on `#EF4444`. |
| minor | `web/feat/creators.js:276` | The creator count line (`#cr_count`) uses class `hint`, and `web/index.html:836` hides every `.hint` at ≤560px — so the count never shows on phones. A count is data, not a hint. | `<p class="hint" id="cr_count"></p>` (`creators.js:276`); `.hint{display:none}` inside the ≤560px media block (`web/index.html:836`). | Give the count its own class (e.g. `class="cr-count"` with `.cr-count{font-size:12px;color:var(--faint)}` in the file's CSS) so it survives the mobile hint hiding. The two explanatory hints in `paintEmpty` (`creators.js:186-191`) collapse on phones too — acceptable, but the count is a real loss. |
| minor | `web/feat/creators.js:136` | When two or more of a creator's accounts are gone, the same sentence is drawn once per missing account: "one account is no longer connected one account is no longer connected". | Each missing id renders `<span class="cr-miss">one account is no longer connected</span>` (`creators.js:136`); the ids are joined into `.cr-chans` at line 141. | Aggregate before drawing: count the missing ids and render one line "N accounts are no longer connected". |
| minor | `web/feat/creators.js:50,53` | Dead CSS: `.cr-chip.txt` is defined twice and no markup draws that class (chips use `cr-chip` and `cr-chip main` only). | Rules at `creators.js:50` and `creators.js:53`; grep of the file finds no `class="cr-chip txt"` and no other use. | Delete both rules. |
| minor | `web/feat/creators.js:144-148,171` | The Track row is permanently "Not set" on every card: the backend never stores a track, so the row is dead weight on every card, and the only explanation of what a track is sits in the page footer below the cards. | `trackLine` renders "Not set" whenever `c.track` is missing; `DEFAULTS` has no `track` key (`studio/creators.py:17-23`), `_clean` copies only DEFAULTS keys (`studio/creators.py:56`), and a repo-wide grep for `"track"` in `studio/*.py` returns 0 matches. The footer discloses it (`creators.js:280-282`). | Render the row only when the server actually sends `c.track`, and drop the now-unneeded footer sentence — the card stays honest without a permanently empty row. |
| minor | `web/feat/creators.js:133` | Usability: "No accounts picked, so nothing is posted for them" — a beginner does not know where accounts get "picked", and the copy does not point at the Setup button directly beneath it. | Copy at `creators.js:133`; the card's Setup button is at `creators.js:175`. | Rename to "No accounts connected yet - clips are not posted anywhere until you add one in Setup." |

## What passed (no finding)

- Page shell 200; all four API routes exist and their shapes match what the file reads.
- Every `data-act` has a live handler; `go` deep-links to the creator's setup/clips tab in one click.
- Loading, empty, read-failure and partial-failure states all present, each in plain language.
- All text contrast passes 4.5:1 except the one pill above; borders and chips are fine.
- No element wider than a 390px viewport; rows and grid collapse correctly.
- No console-risky code: every response access is guarded, `node --check` passes, `esc()` used on all interpolations.
- `tests/test_menu_pages.py` and `tests/test_feat_files.py`: all `creators` checks ok.
