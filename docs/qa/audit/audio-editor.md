# Audit: audio editor (`/app/audio-edit` + `web/feat/audio-edit.js`)

Auditor: agent-133 (audio-editor). Date: 2026-11-22. Contract: `docs/qa/CONTRACT.md`.
Skill loaded first: `systematic-debugging`.

## Pages / files owned

| What | Path | State |
|---|---|---|
| Page | `/app/audio-edit` | shell 200 |
| Feature file | `web/feat/audio-edit.js` (839 lines, read fully) | parses (`node --check` OK) |

The page is a `hidden: true` plugin page (`web/feat/audio-edit.js:724`, supported by
`web/plugins.js:82-85`). Its only entry is the clip editor's "Edit audio" button
(`web/index.html:2796`) with a not-loaded guard that toasts instead of breaking the
button (`web/index.html:3216-3218`).

## Every check run

1. **Page shell**: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8798/app/audio-edit` -> **200**.
2. **Full read** of `web/feat/audio-edit.js` (839/839 lines) and of every backend handler it calls.
3. **Routes**: all 9 routes used by the file exist in `studio/api_memesound.py` and `studio/server.py`
   (GET/PUT `/api/jobs/{jid}/clips/{cid}/sounds` at 235/244, `sounds/suggest` 280, `sounds/hear` 354,
   `memesounds/library` 130, `memesounds/search` 81, `memesounds/keep` 138, `memesounds/play/{slug}` 198,
   `/media/{jid}/{name}` at server.py:1176).
4. **Live probes** against http://127.0.0.1:8798: `/api/memesounds/library` -> 200;
   `/api/memesounds/search?q=bruh&limit=24` -> 200 with rows `bruh`, `bruh-meme-44087`;
   `/api/memesounds/play/bruh` -> 404; `/api/memesounds/play/does-not-exist` -> 404
   (`{"detail":"That sound is not on this machine yet."}`);
   `/api/jobs/x/clips/y/sounds` -> 404 `{"detail":"That job is not here."}` (custom body = route exists, not a 404 route);
   `/assets/feat/audio-edit.js` -> 200.
5. **Orphaned-handler grep**: `data-act="aed-keep"` renders in **0** elements across all of `web/`
   (handler registered at `web/feat/audio-edit.js:769`; 0 hits in any other web file).
6. **Contrast**: WCAG 2.2 ratios computed with `(L1+0.05)/(L2+0.05)`, threshold 0.03928 (the same
   formula `web/feat/polish-contrast.js:36-46` exposes). Measured pairs:
   - `.aed-empty` `#6E6E6E` on `#111111` -> **3.7:1** (needs 4.5 at 11.5px) - FAIL
   - `.aed-ruler b` `#7C7C7C` on `--track2 #161616` -> **4.34:1** (needs 4.5 at 10px) - FAIL (marginal)
   - proposed ruler fix `#8C8C8C` on `#161616` -> 5.38:1 - pass
   - `.aed-chip` `#F5F5F5` on `#2A1A12` -> 15.35:1; chip time `--brand-deep #FFB27A` -> 9.48:1;
     AI cyan `#22D3EE` -> 9.26:1; `.aed-cue .meta` `--dim #A3A3A3` on `--card` -> 7.49:1;
     `.aed-hint` `--faint` (lifted to `#A0948C` by `web/feat/polish-contrast.js:29`, scope `#main, dialog`)
     on `--card` -> 6.39:1 (app's own header records 6.86); `.aed-note.bad/.ok/default` -> 7.16 / 10.3 / 7.85:1. All pass.
7. **Markup nesting**: found `<button>` inside `<button>` in the shelf list (see B2). HTML spec
   13.2.6.4.7: a `button` start tag while a button is open closes it, so the fragment parser relocates
   the inner button as a sibling of the row.
8. **Conformance**: `node --check web/feat/audio-edit.js` -> OK; `esc()` on every interpolated value
   (line 135-137, used in every drawer); no absolute origins; ids `aed_*` clash with nothing in
   `web/index.html`; one plug-in named after the file (both `P.page` and `P.add` are `"audio-edit"`).
9. **Integration**: clip-editor handover reads `stateOf().audioFrom` (line 730) which
   `web/index.html:3221-3222` writes; client/server limits agree (MAX_CUES 12: line 172 vs
   `studio/memesound.py:41`; MIN_GAP 0.35: line 456 vs `studio/memesound.py:42`); `tests/test_feat_files.py`
   checks parsing/registration/esc/id only - it would not catch the nesting bug.
10. **States**: loading ("Reading this clip." line 230), empty states for track (370-372), cues (392-395),
    shelf list (436-440), error path on every fetch via `say(..., "bad")`; no console-risky code found
    (no `innerHTML` of unescaped server text, `try/catch` around pointer capture, seek and `v.load()`).

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| critical | `web/feat/audio-edit.js:769,584,444,538-540` | The download control is missing: handler `data-act="aed-keep"` is registered but no element in any web file renders it, so `keep()` (POST `/api/memesounds/keep`) is unreachable from the editor. The page's own AI instruction "Keep N of them on this machine before saving: use Find on the right" (538-540) is a dead end - Find shows rows with only "Add" (444), which calls `addAt` (adds a cue, downloads nothing, 757). Saving such a cue fails 400: `studio/memesound.py:474-475` "The sound {slug} is not on this machine yet." -> `studio/api_memesound.py:258-261`. Proven live: search returns `bruh` (200) while `play/bruh` -> 404. | grep: `data-act="aed-keep"` = 0 elements in web/; HTTP 404 on `play/bruh`; `cue_ok` at memesound.py:474 | Render a Keep button on shelf rows not yet kept (`data-act="aed-keep"` already works through `web/plugins.js:151-166`), or make Add auto-keep (call `keep(slug)` then `addAt`), or reword the AI note to point at the Audio page |
| important | `web/feat/audio-edit.js:442-445` | Nested `<button>` inside `<button>` in the shelf list. The HTML fragment parser closes the outer row at the inner `button` start tag (spec 13.2.6.4.7), so the Add button becomes a sibling of the row: the row's second grid column (`.go`, line 120) renders empty and Add dangles below the row instead of right-aligned inside it; hovering Add no longer highlights the row | lines 442-445 markup; `tests/test_feat_files.py` checks only `node --check`/registration/esc/id, so nothing catches it | Make the outer element `<div class="aed-row" role="button" tabindex="0">` (drag is delegated on `[data-sound]` and keeps working), or render Add as `<span role="button" data-act="aed-add">` inside the row |
| important | `web/feat/audio-edit.js:82` (+ 68, 370-372, 393) | Empty-state guidance text below AA: `.aed-empty{color:#6E6E6E}` measures 3.7:1 on its backgrounds (lane `#111` line 68; cues list on `--card:#111111`), needs 4.5:1 at 11.5px. It is the only instruction the empty track and the empty cues list give | measured 3.7:1 (`#6E6E6E` on `#111111`); palette pairs around it measure 7.49:1 (`--dim`) and 6.39:1 (`--faint` lifted) | Use `var(--dim)` (#A3A3A3 -> 7.49:1) or `var(--faint)` (#A0948C -> 6.39:1) |
| minor | `web/feat/audio-edit.js:66` | Ruler tick labels marginally below AA: `.aed-ruler b{color:#7C7C7C}` on `--track2 #161616` measures 4.34:1 at 10px (needs 4.5). Hardcoded, so the `polish-contrast.js` lift of `--faint` does not reach it | measured 4.34:1; `#8C8C8C` on the same bg = 5.38:1 | Change to `#8C8C8C` (5.38:1) or `var(--dim)` |
| minor | `web/feat/audio-edit.js:532-535, 480` | Stale selection: `ask()` and `save()` replace `E.cues` (AI list / server's tidied list) without resetting `E.sel`, so the highlight can land on a different chip (378: `i === E.sel`) and Delete/Backspace (786-793) then splices whatever now sits at that index - the wrong sound | `E.sel` not reset at either replace site; splice uses the raw index at 787 | Set `E.sel = -1` after replacing `E.cues` in `ask()` and `save()` |
| minor | `web/feat/audio-edit.js:560` | Play-failure copy is false for un-kept sounds: "The browser would not play it. It is still fine when mixed in." - for a cue whose slug is not kept, `play/<slug>` answers 404 "That sound is not on this machine yet." (`studio/api_memesound.py:209-210`, proven with `play/bruh`) and mixing fails too (`cue_ok`) | HTTP 404 body on `play/bruh`; message text at line 560 | Say "The sound is not on this machine yet. Keep it first.", or HEAD-probe the play route first (the route advertises HEAD for exactly this, api_memesound.py:202-203) |
| important (usability) | `web/feat/audio-edit.js:224, 532-535` | "Ask the AI to place them" silently REPLACES every cue on the track with no confirm and no undo. The label reads as "add", and the backend is explicit that the saved list is the whole truth: "a cue missing from it is removed from the clip" (`studio/api_memesound.py:248`). A beginner with hand-placed sounds loses them on one press | `E.cues = cues.map(...)` at 532-535; button label at 224 | Confirm before replacing when cues exist and are not all AI-sourced ("Replace the 3 sounds on the track with the AI's picks?"), or add AI cues alongside existing ones |
| important (usability) | `web/feat/audio-edit.js:786-793, 243` | The keyboard shortcut is undocumented: Delete/Backspace removes the selected chip, but neither the shelf hint (243) nor the empty-track text (370-372) mentions it | handler at 786-793; hint text at 243 | Extend the hint: "Drag one onto the track, press it and then press the track, or select a sound and press Delete." |
| minor (usability) | `web/feat/audio-edit.js:228, 421` | Two play controls with different behavior and near-identical copy: "Hear it here" plays the clip from the first cue minus 1s (770-779); the per-cue "Play" plays only that sound and seeks the video (551-567) | both handlers; labels at 228/421 | Rename "Hear it here" to "Play the clip"; give both buttons title tooltips |
| minor (usability) | `web/feat/audio-edit.js:827-837, 240` | Search-as-you-type does nothing: the `input` listener handles only the emptied case, so typing updates nothing until Find is pressed, while the placeholder "Search the catalogue" implies live search | listener at 827-837; placeholder at 240 | Debounced `find()` on input, or reword the placeholder to "Type, then press Find" |

## What passed

- Page shell 200; every route the feature calls exists in `studio/*.py` and answers live.
- `node --check` OK; `esc()` everywhere; no id clash; one plug-in per file; no absolute origins.
- All other contrast pairs pass (chips 15.35/9.48/9.26, meta 7.49, hints 6.39, notes 7.16/10.3/7.85).
- Touch targets: `.aed-mini{min-height:44px}` at <=760px (line 131); 390px viewport collapses to one
  column; the track keeps `min-height:300px` and the lane's chips stay inside it.
- Loading / empty / error states present on every region; client and server limits agree (12 cues, 0.35s gap).
- The clip-editor handover (`S.audioFrom`) is wired both ways, with a not-loaded guard on the entry button.
