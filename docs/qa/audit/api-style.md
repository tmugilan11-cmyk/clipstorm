# Audit — API area: caption styles, style preview/motion, formats, formats plan

Auditor: agent-152 (40-agent QA swarm, audit wave). Area: the catalogue routes over HTTP.

## Files owned

- `studio/api_style.py` — every route audited: `GET /api/captions/styles`, `GET /api/style/preview?style=`, `GET /api/style/motion?style=`, `GET /api/formats`, `POST /api/formats/plan`.
- `studio/captions.py` — read fully: the 42-look table, `ANIM`, `LABELS`, `FONT_FILES`, `build()`/`build_ass()`.
- Supporting reads: `studio/formats.py` (backs the plan route), `studio/brand.py` (`normalise`, which sanitises preview colour fields), `studio/render.py` (`STYLES`, the three house looks), `studio/server.py` (router mount, `/assets/font`), `web/feat/formats.js` and `web/feat/style-tiles.js` (the consumers).

## Checks run (all against the live server on 127.0.0.1:8798)

| # | Check | Result |
|---|---|---|
| 1 | `GET /api/captions/styles` | 200; `count:45`, 45 rows, 16 fonts, `default:"bounce"`; 3 house looks first (`bounce, hype, clean`), each with `{name,label,house,anim}` |
| 2 | `GET /api/formats` | 200 in 0.003 s; 8 shapes with `{id,label,needs_parts,hint}`, `count:8`, `default:"moment"` |
| 3 | `GET /api/style/preview?style=classic` | 200, `image/jpeg`, 39,547 bytes, 0.54 s |
| 4 | `GET /api/style/preview` (no style) | 200 — falls back to `bounce`, 43,161 bytes |
| 5 | `GET /api/style/preview?style=comic&c_text=FF00AA&c_key=00FFAA&hook=hello%20world` | 200, 45,778 bytes |
| 6 | `GET /api/style/preview?style=clean&c_text=zzz&font=notarealfont&lang=zz` (malformed values) | 200 — junk falls back via `brand.normalise` (`studio/brand.py:126-178`), no crash |
| 7 | `GET /api/style/preview?style=PUNCH` (upper-case input) | 200 — `.lower()` normalises (`studio/api_style.py:235`) |
| 8 | `GET /api/style/preview?style=notalook` | 400 with the full 45-name known list — correct status, correct message |
| 9 | `GET /api/style/preview?style=` 50 chars, `hook=` 150 chars | 422 (FastAPI `max_length` validation) — acceptable |
| 10 | `GET /api/style/motion?style=classic` | 200, `video/mp4`, 11,083 bytes, 0.58 s; second call 0.005 s (cache hit) |
| 11 | `GET /api/style/motion?style=notalook` | 400, same correct message |
| 12 | `POST /api/formats/plan` valid `{format:"compilation",words:[3]}` | 200; plan says `ok:false` + `warnings:["compilation needs at least 3 parts"]` — honest, not a 500 |
| 13 | `POST /api/formats/plan` bad JSON / `[1,2]` body / empty body | 400 `"That plan could not be read. Try again from the page."` |
| 14 | `POST /api/formats/plan` unknown format | 400 with the 8 known shapes |
| 15 | `words:"hello"` → 400 `"The words to plan against must be a list."`; `[{"w":"hi"}]` → 400 `"…each needs an 's' time."` | both correct 400s |
| 16 | `POST /api/formats/plan` with 4,001 words | 200, `ok:true` — silently truncated to `_MAX_WORDS=4000` (`studio/api_style.py:137`), documented in the code comment |
| 17 | `POST /api/formats/plan` `{"pick":{"format":"megaclip"}}` | 400 with the known list (name is read from `pick`) |
| 18 | `GET /assets/font/NotoSansJP-Black.ttf` (a URL `_fonts()` emits) | 200, 5,756,508 bytes — every catalogue font URL is servable |
| 19 | Render sweep: `bounce, hype, cream-ink, brainrot, word, punch, title-slide` on **both** preview and motion | 14/14 = 200 — no look fails to draw |
| 20 | Route-existence proof: all five routes registered in `studio/api_style.py:46,104,114,218,326`; router mounted `studio/server.py:250` | pass |

## Findings

| Severity | Where | What | Evidence | Fix |
|---|---|---|---|---|
| minor | `studio/api_style.py:114-145` | `POST /api/formats/plan` is a live route nothing calls. The formats page builds its cards from `GET /api/formats` alone, and no `web/feat/*.js` or `index.html` line names `formats/plan` (repo-wide grep: 5 hits, all in `docs/` or the module itself). The prior wave already recorded the gap at `docs/swarm4/wave4/formats.md:61`. Dead surface: it answers, but no person can ever reach it. | repo grep `formats/plan` → only `docs/port/18-clipper-ui-reference.md:136-137`, `docs/swarm4/wave4/formats.md:61`, `studio/api_style.py:13,114`; consumer list in `web/feat/formats.js:154,170` names `/api/formats` and `/api/captions/styles` only | Either wire it to a "try this shape" preview flow on the formats page, or remove the route. If kept, also read `words` out of `pick` (see next row) |
| minor | `studio/api_style.py:128-137` | The plan route reads `words` from the top-level body only, but `format` from `pick` **or** the body. A caller sending the documented nested shape `{"pick":{"format":"moment","words":[…]}}` silently loses the words and plans against an empty list, with no warning in the response. | `api_style.py:128` `pick = body.get("pick") … else body`; `api_style.py:134` `words = body.get("words")` — never consulted on `pick` | `words = pick.get("words") if body.get("pick") is None or not isinstance(body.get("pick"), dict) else (body.get("words") or pick.get("words"))` — or accept both and document which wins |
| minor | `studio/api_style.py:139` | Plan error copy is developer-speak: `"Those words are not in the shape PeakCut writes: each needs an 's' time."` A person reading this in a form cannot act on "an 's' time" — the words are speech with `s`/`e` seconds, which the page never explains. | HTTP 400 response, check 15; contract rule 6 (copy a beginner would not understand in five seconds) | `"Those words cannot be planned: each needs a spoken time ('s') and an end time ('e') in seconds."` |
| minor | `studio/api_style.py:263,277` (preview) and `:342,354` (motion) | The caches store the timestamp captured **before** the ffmpeg run, so every frame's TTL starts at request start, not at draw time. The 600 s preview TTL loses up to 60 s of fresh window (`timeout=60`, `api_style.py:209`); motion loses up to 90 s of its 3600 s. Negligible for a person, but the constant no longer means what its comment says ("seconds a drawn frame stays worth reusing"). | `now = _time.monotonic()` at `:263`/`:342`; stored unchanged at `:277` `_PREVIEW_CACHE[key] = (now, jpg)` and `:354` `_MOTION_CACHE[key] = (now, mp4)` | Store `_time.monotonic()` inside the same `with _PREVIEW_LOCK:` block that inserts the result, after the render returns |
| minor | `studio/api_style.py:264-275` (preview), `:343-352` (motion) | Concurrent identical requests both render. The lock guards only the cache probe and is released before `run_in_threadpool`, so two tabs (or two people) asking for the same uncached look at the same moment run ffmpeg twice and the second result overwrites the first. The formats page deliberately fires 4 stills + 3 motions at once (`web/feat/formats.js:234,322`), which makes same-look races reachable. | lock scope `:264-273` ends before `:275 jpg = await run_in_threadpool(…)`; same shape at `:343-351` → `:352` | Keep a per-key in-flight event (or hold the lock across the render for an already-pending key) so the second caller waits for the first result |

## What passed cleanly (no finding)

- No 500 anywhere; every invalid input returns a 400/422 with a sentence, never a traceback (`plan_format` wraps `formats.plan` in `except Exception` → 400, `api_style.py:141-144`).
- The catalogue never fails on one bad row: `anim` and `label` are each guarded (`api_style.py:61-64, 98-101`).
- Colour/font/lang junk in preview query fields cannot reach the renderer: `brand.normalise` drops unknown keys and `_hex`-guards `hook_text`/`hook_box` (`studio/brand.py:126-178`).
- `_fonts()` reads the same folder the asset route serves (`config.ROOT/"studio"/"fonts"` in `api_style.py:85`; `server.py:44` `FONTS = config.ROOT/"studio"/"fonts"`) — the emitted URLs are all real (check 18).
- The frontend consumers handle every state the API can produce: loading line, error box with the server's own sentence, `null` vs `[]` distinction, "Frame not drawn" tile, "Still frame" badge while motion draws (`web/feat/formats.js:216-227, 37-56, 311-319`) — no missing loading/empty/error state found in the consuming pages.
- Unauthenticated access behaves per `config.ACCOUNTS` default (single built-in owner); `_me` raises 401 only when accounts are on and nobody is signed in (`api_style.py:35-43`).
