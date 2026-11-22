# Audit: igcaption API area (agent-150)

Server: http://127.0.0.1:8798 (live, running). No browser used; all evidence from
`ops_grep` / `ops_inspect_local_file` / `curl`. Shared-state care: every PUT was
restored to the original values afterwards; the 429 throttle was deliberately NOT
tripped (it is keyed to the one built-in owner and would lock `generate` for the
whole swarm for 300 s).

## Files and routes owned

- `studio/api_igcaption.py` — `GET /api/igcaption/looks` (:53), `GET`/`PUT /api/jobs/{jid}/clips/{cid}/igcaption` (:60, :68), `POST .../igcaption/generate` (:89). Router included at `studio/server.py:261`.
- `studio/igcaption.py` — the model behind those routes (validate_text, default, for_post, view, generate).
- Consumer read for cross-checking (not edited): `web/feat/igcaption.js`.

## Checks run (all against the live server)

| # | Check | Result |
|---|---|---|
| 1 | `GET /api/igcaption/looks` | 200; `formats` 4 items with `{id,label}`, `langs` 3 bare IDs, `limit` 2200, plain-language `note` |
| 2 | `GET /api/jobs` | 200; real job `20261122-122201-798840cfbf`, clip `clip01` used for all clip tests |
| 3 | `GET .../igcaption` (real clip) | 200; correct default view `{"caption":"Loud moment","enabled":false,"lang":"original","format":"natural","limit":2200}` |
| 4 | `GET` with bad jid | 404 `"No such video."` |
| 5 | `GET` with bad cid | 404 `"No such clip."` |
| 6 | `PUT` body `not json` | 400 `"Send the caption as a JSON object."` |
| 7 | `PUT` body `[]` | 400 `"Send the caption as a JSON object."` |
| 8 | `PUT {"lang":"klingon"}` | 400 `"Choose a language and writing style from the list."` |
| 9 | `PUT {"enabled":"yes"}` | 400 `"Choose whether to use a separate Instagram caption."` |
| 10 | `PUT {"caption":null}` | 400 `"The Instagram caption must be text."` |
| 11 | `PUT` 2201-char caption | 400 `"An Instagram caption can have up to 2,200 characters, including hashtags."` |
| 12 | `PUT` caption with control char (0x0C, payload bytes verified via `od -c` as `{"caption":"a\fb"}`) | 400 `"The caption contains a control character. Remove it and save again."` |
| 13 | `PUT` real newline + `enabled:true` | 200; newline round-trips in the view |
| 14 | State after 6 rejected PUTs | unchanged (the api_igcaption.py:82 "invalid update leaves the previous caption untouched" guarantee holds) |
| 15 | `PUT` restore of original values | 200; final state identical to the pre-audit default view |
| 16 | `POST .../generate` realistic (`{"lang":"original","format":"natural"}`) | 200; AI draft `source:"ai"`, `saved:false`; clip verified unchanged after |
| 17 | `POST generate` bad lang | 400 (same choose-from-list message; no AI call) |
| 18 | `POST generate` body `zzz` | 400 `"Send the caption as a JSON object."` |
| 19 | `POST generate` bad jid | 404 `"No such video."` |
| 20 | Source-escaping verification | hex row 672 of `studio/igcaption.py` decodes to `text = text.replace("\r\n", "\n").replace("\r", "\n")` — single backslashes, correctly escaped (an initial suspicion of double-escaped source was a display artifact) |
| 21 | Helper existence | `ai.models` ai.py:113, `ai.ready` ai.py:162, `ai.explain` ai.py:276, `auth.AuthError` auth.py:25, `auth.throttle` auth.py:57 — all exist; AuthError is a ValueError subclass and is caught before ValueError in api_igcaption.py:96-103 (correct order) |
| 22 | `ai.explain` fallback | returns `""` for unrecognized errors (ai.py:288); handler `(ai.explain(e) or str(e))[:240]` (api_igcaption.py:106) preserves the actionable "Set up AI before generating a caption. You can still type and save your own." message |
| 23 | Throttle message | auth.py:68 `"Too many attempts. Wait a few minutes and try again."` → 429 (message readable; path not fired live, see note above) |
| 24 | Contrast (computed) | `--dim` #A3A3A3 on `--card` #111111 = 7.48:1; `--bad` #F87171 on `--card` = 6.83:1 (palette web/index.html:19-21). Both pass 4.5:1 for the 12px text igcaption.js paints with |
| 25 | UI consumer safety | igcaption.js escapes everything through `esc()` (:6-7), has loading (:117), error (:123), empty-hide (:10) states, `role="status"` (:64), and revision-based race handling (:92, :100, :103) |
| 26 | Documentation cross-check | docs/IGCAPTION.md:17-24 matches the live routes and observed behavior exactly |

Checks NOT run live (and why): tripping the 429 throttle (would lock the shared
owner out of `generate` for 300 s — code-verified instead); the generate
"Add a title or description first" 400 (no clip without title/hook/description
exists on this install; path reviewed at igcaption.py:58-60); the disabled-account
403 (requires `PEAKCUT_ACCOUNTS=1`); live ja/zh generation (covered by
tests/test_igcaption.py:27-36 with ask_fn).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| minor | web/feat/igcaption.js:42, :58 | The UI hardcodes the 2,200-character limit instead of using the `limit` the API sends, so it can silently drift from `MAX_LENGTH` | `igcaption.py:11 MAX_LENGTH = 2200`; view (igcaption.py:51) and looks (api_igcaption.py:56) both send `limit: 2200`; the counter prints the literal `" / 2,200 characters"` and the textarea has `maxlength="2200"` | Use the API's `limit` in both the counter string and the textarea maxlength |
| minor | web/feat/igcaption.js:42 vs :58 | The visible counter and the textarea maxlength count different units: `Array.from(caption).length` counts code points, HTML maxlength counts UTF-16 units; with emoji the box blocks input while the counter still shows room (1,100 emoji → "1,100 / 2,200" but typing blocked) | measured: two different counting units on the same pair of controls; no data loss (the UI is only ever stricter than the server), but the numbers disagree | Drop `maxlength` and rely on the counter plus the server's clear 400, or align both to one counting unit |
| minor | studio/api_igcaption.py:53-57 | `GET /api/igcaption/looks` skips the `_me(request)` disabled-account check that every other route in this router performs | igcaption_for (:61-62), igcaption_write (:70), igcaption_generate (:91) all call `_me`; igcaption_looks does not. Impact is nil today (the response carries only constants, no user data) | Call `_me(request)` for consistency so the router gates uniformly |
| minor | studio/api_igcaption.py:55-56 | `/api/igcaption/looks` returns languages as bare IDs with no labels while formats carry `{id,label}`; a consumer reading this endpoint alone shows "ja"/"zh", which a beginner would not understand in five seconds | curl: `"langs":["original","ja","zh"]` next to `"formats":[{"id":"natural","label":"Natural"},…]`; `LANG_NAMES` (igcaption.py:19) already holds plain names ("the same language as the source", "Japanese", "Simplified Chinese") but is unused by this route; the shipped UI hardcodes its own labels (igcaption.js:52) so users are fine today | Return `[{"id","label"}]` for langs using `LANG_NAMES`, matching the formats shape |

No critical and no important bugs found: no 500s or crashes, no missing routes,
all eight distinct error messages correct and specific, the invalid-update
guarantee holds live, newline and control-character handling verified at byte
level, contrast passes, and the UI consumer escapes everything and has
loading/empty/error states.

## Verdict

The igcaption API area is solid. All four findings are minor polish/drift items.
