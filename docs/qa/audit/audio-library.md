# QA Audit — Audio library (`/app/audio`, `web/feat/audio-page.js`)

Auditor: agent-132 (40-agent QA swarm, slug `audio-library`).
Server: http://127.0.0.1:8798. Contract: `docs/qa/CONTRACT.md` (read in full; binding).
Method: repo files + `curl` against the running server only — no browser tools (the lead owns the browser during this audit). Skill used: `systematic-debugging` (root cause before fixes).

## Pages / files owned

| What | Path | Result |
|---|---|---|
| Page | `/app/audio` | curl → **200** |
| File | `web/feat/audio-page.js` | read fully (602 lines) |
| Backing server file | `studio/api_memesound.py` (1–210) | read (routes + row shapes) |
| Backing server file | `studio/memesound.py` (rank/library/kept/take/forget/path_for) | grepped + read |

## Checks run

1. `docs/qa/CONTRACT.md` — read fully (50/50 lines).
2. `web/feat/audio-page.js` — read fully (602/602 lines), two passes.
3. `skill(systematic-debugging)` — loaded.
4. Page shell: `curl /app/audio` → **200**.
5. Data routes, live: `GET /api/memesounds/library`, `/trending?window=24h`, `/search?q=drum&limit=24`, `/for?situation=funny&limit=24` → all **200**; JSON row shapes captured.
6. Route existence: all 7 routes the page calls exist in `studio/api_memesound.py` (search:81, for:96, trending:111, library:130, keep:138, `DELETE library/{slug}`:154, `play/{slug}`:198 GET+HEAD); `upload`:162 exists and is wired in `web/feat/meme-timeline.js:143` (the clip editor), not by this page.
7. `studio/memesound.py`: `rank()` (194–208) and `library()` (381–382) add **no `kept` field** to any row; `kept()` = kept file > 512 bytes; `forget()` returns bool; `LISTED = 30` catalogue entries (page's `limit=24` stays under the cap).
8. Contrast palette from `web/index.html`: `--dim:#A3A3A3`, `--faint:#7C7C7C` base, overridden app-wide to `#A0948C` by `web/feat/polish-contrast.js:29` (`#main, dialog { --faint: #A0948C; }`); `--bg:#0A0A0A`, `--card:#111111`, `--muted:#111111`, `--brand:#FF8B33`, `--brand-soft:#2A1B10`, `--brand-deep:#FFB27A`.
9. Text contrast on the page (computed `(L1+0.05)/(L2+0.05)`): `.alb-sub` 7.85:1, `.alb-note`/`.alb-count` 6.70:1 (4.74:1 on the base faint — still passes), `.alb-mini` 7.85:1, `.alb-tools` labels 7.48:1, `.alb-wave.empty` 6.62:1, `.alb-ico` 9.42:1 — **all pass 4.5:1**. Board pills fail when pressed/hovered (finding B5).
10. Board pill colours, 9 swatches × base/hover(brightness 1.16)/pressed(brightness 1.22) — computed individually; white text on brightened `#B45309` and `#C2410C` fails WCAG AA (B5).
11. `web/index.html`: `music` icon is a real SVG path (line 958); `window.toast(msg, kind)` exists (line 1006) so the page's `say()` works.
12. `web/plugins.js`: `P.api(p,o)`, `P.send(p,b,m)`, `P.css`, `P.page` signatures match the page's calls; `grep alb_` in `web/index.html` → 0 matches (no id clash).
13. Live probes on the exact failure paths:
    - `GET /api/memesounds/play/chicken-on-tree-screaming-53890` (catalogue slug, not kept) → **404** `{"detail":"That sound is not on this machine yet."}`
    - `DELETE /api/memesounds/library/nonexistent-sound-00000` (no-op, no state change) → **`{"ok":false,...}`**
    - `GET /api/memesounds/trending?window=24h` tail → rows end with `"popularity":0}],` followed by top-level **`"kept":["dun-dun-dunnnnnnnn-68584","vine-boom-longer-22911","fart","vine-boom-sound-70972"]`** — the kept slug list is in the response and the page never reads it.
14. 390px-viewport walk-through of the page CSS (lines 25–105): content padding 22px; `grid-template-columns` → single column ≤640px; sidebar static and full-width; flex-wrap on head/bar/rows; fixed-width inputs overridden to 100% inside the sidebar; card grid `minmax(228px,1fr)` → one ~346px column at 390px. **No overflow, no clipped text.**
15. Every state a person can see has its copy: loading spinner + text, per-shelf empty states, error toasts, like/bookmark on-state. The failure paths that get the state wrong are findings B1–B3.

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| critical | `web/feat/audio-page.js:311` | **The Keep button never renders on any catalogue shelf.** `const kept = r.kept !== false;` assumes a per-row `kept` flag, but no server row carries one (catalogue rows: slug/title/about/…/popularity; library rows: slug/title/seconds/bytes), so `kept` is always `true` and the `alb-keep` "Keep" button (line 328) is unreachable dead code on Trending/Reaction/Funny/Fail/Hype and on every card. The one action the shelf note advertises ("Nothing is downloaded until you press Keep", line 218) cannot be performed. | `curl /api/memesounds/trending?window=24h` rows contain no `kept` key; the response carries a **top-level** `"kept":[…]` slug list (`studio/api_memesound.py:119`, live-verified) that the page never reads; `studio/memesound.py:194-208` `rank()` and `:381-382` `library()` add no kept field | Read the response's top-level kept list into a Set in `loadBoard`; compute `kept = keptSet.has(r.slug)` in `card()` |
| critical | `web/feat/audio-page.js:325-328, 491-499` | **Download and Remove offered for sounds that are not on this machine, and Remove reports a false success.** On catalogue shelves every card renders a Download link to `/api/memesounds/play/<slug>` — which 404s for un-kept sounds — and a Remove button; pressing Remove DELETEs a file that does not exist, the server answers `{"ok":false}`, and the page still toasts "Removed from this machine. The catalogue still has it." | `curl DELETE /api/memesounds/library/nonexistent-sound-00000` → `{"ok":false,…}` (live); `studio/api_memesound.py:209-210` play 404s for un-kept; the page ignores `ok` at lines 493–494 | Same kept-set fix; render Download/Remove only for kept rows; honor `ok:false` with "It was not on this machine." |
| important | `web/feat/audio-page.js:463-478` | **Play on an un-kept sound blames the browser.** The play route 404s for catalogue sounds; the catch (472–474) shows "The browser would not play it here. It is still fine on the clip." — wrong diagnosis; the sound simply is not downloaded. | `curl GET /api/memesounds/play/chicken-on-tree-screaming-53890` → **404** `{"detail":"That sound is not on this machine yet."}` (live) | Check the kept set before playing (or catch the 404) and say "Not on this machine yet — press Keep first." |
| important | `web/feat/audio-page.js:378-384, 407-444` | **One full-file download per card just to paint a decorative waveform.** `draw()` calls `bars(slug)` for every canvas; `bars()` fetches the complete mp3 (line 416) and decodes it, once per sound per visit. On the Saved shelf that is one full download per kept sound every time the page loads; on catalogue shelves every fetch 404s and leaves a blank box. | Live library has 4 sounds → 4 full mp3 fetches on load; no virtualization; decode cache is per-session only | Draw a deterministic placeholder from the slug hash, or decode lazily on intersection, or have the server send peak data |
| important | `web/feat/audio-page.js:38-44` | **Selected/hovered shelf pill text fails WCAG AA.** `.alb-cat` is white 11.5px bold; the pressed pill gets `filter:brightness(1.22)` and hover `brightness(1.16)`, brightening the orange pills past the limit. | White on brightness(1.22) `#B45309` = **3.55:1**; on `#C2410C` = **3.67:1**; hover `#B45309` = 3.89:1, `#C2410C` = 4.02:1 — all below the 4.5:1 required for 11.5px text (not large). Unpressed passes 5.02/5.18 | Keep the pressed/hover colour at the base (the inset ring already shows state) or darken instead of brighten; re-measure to ≥4.5:1 |
| important | `web/feat/audio-page.js:361-372` | **List view drops the row's main actions.** List rows render only Play/Like/Bookmark while the comment claims "the same information"; Download/Remove/Keep vanish, so the Saved shelf in list view cannot remove or download anything. | lines 363–372 vs `card()` 317–329 | Render the same trailing action the card shows |
| minor | `web/feat/audio-page.js:381` vs CSS `:82` | **The waveform "empty" fallback never shows.** On decode failure the code adds the class it already has (`cv.classList.add("alb-wave")`) instead of `"empty"`, so `.alb-wave.empty` ("no bars") is dead and a failed decode leaves a blank dark box with no explanation. | CSS line 82 defines `.alb-wave.empty`; markup never gains `empty` | Add `"empty"` and let the existing fallback text show |
| minor | `web/feat/audio-page.js:42, 65, 321, 338, 44, 410/442` | **Repo-rule violations and dead code.** `box-shadow` on the pressed pill (42) and view tab (65) — the repo rule is "no shadows"; `(liked ? icon("heart") : icon("heart"))` both branches identical (321); `icon("down")` never used (338); `.alb-cat b` CSS with no matching markup (44); `void audio` dead var (410, 442). | AGENTS.md rule "no shadows"; the lines above | Drop the shadows (state is already shown by colour/ring), the dead ternary, the unused icon, the dead CSS |
| minor | `web/feat/audio-page.js:293-298` | **The length filter silently does nothing on catalogue shelves.** `shown()` treats missing seconds as 0, so every unknown-length catalogue sound passes "Under 2s/5s/10s" — the filter claims a limit it does not apply. | Live trending rows carry no `seconds` key | Say "known lengths only" in the option text, or grey the filter when the shelf has no lengths |
| minor | `web/feat/audio-page.js:215, 385, 388-398, 540-544` | **Stale search results with an empty box after navigating away and back.** The page renders `alb_search` with no value and `load()` never clears `B.search`/`B.hits`, but `draw()` → `drawHits()` re-renders the old hits — results with no query visible. | lines 540–544 clear nothing; `drawHits()` runs unconditionally from `draw()` | Clear `B.search`/`B.hits` in `load()` (or restore the query into the box) |
| minor | `web/feat/audio-page.js:272-274` | **Silent drop of shelf clicks while a load is in flight.** `if (B.busy) return;` ignores a pill click during a load with no feedback, and the pill's pressed state stays on the old board (`barHtml` is only re-drawn inside `go()`). | line 273; `barHtml` assignment only inside `go()` | Disable the pills while busy, or queue the click |
| minor | `web/feat/audio-page.js:540-544` | **Board selection resets on every page re-entry.** `if (!B.rows.length) B.board = "kept";` bounces an empty Liked/Bookmarked/Mine shelf back to Saved whenever you leave and return to the page. | line 542 | Remember the last board regardless of row count (module state or localStorage) |
| important | `web/feat/audio-page.js:184-185, 291-299` vs `:213-218` | **Sidebar "Find" looks like the page's search but only filters the current shelf.** The sidebar label "Find" (a client-side filter of `B.rows`) sits above the real catalogue search ("Search every sound", below the list); a beginner types into "Find" expecting catalogue results and gets a silently shrinking shelf. | `shown()` filters only `B.rows` (291–299); the catalogue search is a separate control at 213–218 | Rename the label to "Filter this shelf" and add the hint "only filters the sounds above" |
| important | `web/feat/audio-page.js:186-189` | **"Longest" is not a readable label for a max-length filter.** `<label>Longest<select>` with options "Any length / Under 2s / Under 5s / Under 10s" — a beginner cannot parse "Longest → Under 2s" in five seconds. | line 186 | Rename to "Length" |
| important | `web/feat/audio-page.js:215, 222-224` | **"DankMachine" jargon is unexplained.** The placeholder "Search all of DankMachine" and the rights note name DankMachine with no explanation; a beginner has no idea it is the sound catalogue the page is searching. | lines 215, 222–224 | "Search the whole catalogue" / "The sound catalogue (DankMachine) marks most sounds…" |
| important | `web/feat/audio-page.js:481-489` | **Keep teleports you off the shelf you are browsing.** `keep()` always `go("kept")` after a successful keep — keeping a sound from Trending jumps you to Saved and you lose your place in the list. | line 485 | Stay on the current shelf and flip that card's action to Remove |
| minor | `web/feat/audio-page.js:263` | **Uploading your own file is a trip to another page.** The Mine shelf's empty state says "Upload one in the clip editor" — the claim is true (`POST /api/memesounds/upload` exists at `studio/api_memesound.py:162`, wired in `web/feat/meme-timeline.js:143`), but the library is the natural home; one button here would make it a one-step flow. | route + wiring above | Add an Upload button on the Mine board posting to `/api/memesounds/upload` |
| minor | `web/feat/audio-page.js:364` vs `:313` | **A lone "·" stands in the duration chip in list view.** For sounds with no length the card view shows a globe icon ("in the catalogue, not on this machine") but list view shows a meaningless "·". | `secsBare` fallback at 364 vs globe at 313 | Show the globe in list view too |

## What is right (no findings)

- Page shell 200; all 7 routes the page calls exist and return 200 with the shapes the page expects.
- Every visible state has copy: loading, per-shelf empty states, like/bookmark on-state, error toasts.
- All body text passes WCAG AA on this page (see check 9); the only contrast failures are the pill states in B5.
- No overflow at 390px; the grid, sidebar and bars all collapse to a single column with flex-wrap.
- Follows the feat-file contract: one plug-in named after itself, no id clash with `index.html`, `esc()` used on every interpolated value, no absolute origin.

## Summary

One critical root cause (the page invents a per-row `kept` flag the server never sends, while ignoring the top-level kept list it does send) breaks the Keep action on every catalogue shelf and produces false-success Remove and wrong Play error copy; four pill states fail WCAG AA; six usability findings, all with concrete fixes.
