# Audit: api-overlays (the picture editor's routes)

Auditor: agent-149 (QA swarm, audit wave). Rules: docs/qa/CONTRACT.md.

## Files owned

- `studio/api_overlay.py` — every route behind the picture editor: the shelf
  (GET/POST/DELETE `/api/overlays*`), templates (GET/PUT/DELETE
  `/api/overlays/templates*`), one clip's overlay (GET/PUT
  `/api/jobs/{jid}/clips/{cid}/overlay`), previews (POST/GET
  `/api/jobs/{jid}/clips/{cid}/overlay/preview`), and the every-clip toggle
  (PUT `/api/jobs/{jid}/overlay-template`).
- `studio/overlay.py` — the shelf store, slug guard, placement cleaner,
  template file, and the ffmpeg chain the preview and the render share.
- Read for context (owned by other auditors, not edited): `web/feat/pictures.js`,
  `web/feat/pictures-dialog.js`, `studio/server.py` (the request gate),
  `studio/peek.py`, `studio/render.py`.

All 12 routes live in `studio/api_overlay.py` and are mounted at
`studio/server.py:262` (`app.include_router(api_overlay.router)`); `server.py`
adds no overlay routes of its own. The live server is http://127.0.0.1:8798.

## Every check run

All HTTP numbers below were measured with curl against http://127.0.0.1:8798
during the audit (13:07-13:20 local). Fixtures: the pre-existing shelf images
`logo-92b716.png`, `my-logo-86b716`-shelf pair, real jobs `20261120-200119-5fdd2d8f89`
(clip01, 2 overlay items, status done) and `20261122-122201-798840cfbf`
(clip01, no overlay, status done). Test images and the test template were
deleted afterwards; the shelf and templates were restored to their
pre-audit state (verified at the end: 2 images, 0 templates).

### The shelf

| # | Check | Result |
|---|---|---|
| A1 | POST `/api/overlays/upload` with a valid 1x1 PNG | 200, `{"ok":true,"image":{"name":"tiny-9b88d8.png","bytes":70,...}}` |
| A2 | POST upload with an empty file | 400 `That file is empty.` |
| A3 | POST upload with a text file named `.png` (content check) | 400 `That file is not a picture PeakCut can read. PNG, JPG or WebP work.` |
| A4 | POST upload 13 MB (> the claimed 12 MB cap) | 413 `That request is too large.` — the gate fires before the route (see finding 2) |
| A5 | GET `/api/overlays/image/tiny-9b88d8.png` | 200, `content-type: image/png`, 70 bytes |
| A6 | GET image with a nonexistent name | 404 `That picture is not on the shelf.` |
| A7 | GET `/api/overlays/image/..` | 307 redirect to `/api/overlays` (see finding 4) |
| A7b | GET image with encoded traversal `..%2F..%2Fetc%2Fpasswd` | 404 `Not Found` — the slug guard refuses it before any file access (`studio/overlay.py:56-59`) |
| A8 | DELETE `/api/overlays/{name}` (uploaded image) | 200 `{"ok":true,"gone":"tiny-9b88d8.png"}` |
| A8b | DELETE the same name again | 404 `That picture is not on the shelf.` |
| A8c | DELETE a name that is not a slug | 404 `That picture is not on the shelf.` |
| A9 | POST upload a real small logo (2,154 bytes) | 200, stored `small-ae09b6.png`, 700x500 |
| A10 | POST upload a real ordinary 1,051,924-byte PNG logo | 413 `That request is too large.` (see finding 2) |
| M1 | POST upload a real JPEG | 200, stored as `jpegshot-8ec437.png` — a `.png` name (see finding 3) |
| M2 | GET the stored JPEG | 200, `content-type: image/png`, bytes begin `FF D8 FF E0` (JPEG magic) — see finding 3 |
| M4 | POST upload without the `file` field | 422, FastAPI's proper validation detail `Field required` |

### Templates

| # | Check | Result |
|---|---|---|
| B1 | PUT `/api/overlays/templates` with `{"id":"","name":"QA test layout","items":[...]}` | 200, new template `tcfd67c`, placements cleaned (rot 15 -> 15.0, alpha 0.8 kept) |
| B2 | PUT with an item naming a missing image | 400 `None of those pictures are on the shelf, so the layout would draw nothing. Add the pictures first, then place them.` |
| B3 | PUT with an unparseable body (`not json at all`) | **500 `Internal Server Error`** (finding 1) |
| B4 | PUT with an empty body | **500 `Internal Server Error`** (finding 1) |
| B5 | PUT with JSON `null` body | 400 `Send the layout as an object.` — handled |
| B6 | PUT with `items` as a string instead of a list | 400 (the "would draw nothing" message) — handled |
| B7 | PUT replacing an existing template id | 200, name and items replaced |
| B8 | DELETE `/api/overlays/templates/tcfd67c` | 200 `{"ok":true,"gone":"tcfd67c"}` |
| B8b | DELETE the same id again | 404 `No such layout.` |
| B9 | GET `/api/overlays` and GET `/api/overlays/templates` (empty state) | 200 with the beginner notes `No pictures yet. Add a logo or a poster...` / `No layouts yet. Put a picture where you want it...` (`studio/api_overlay.py:65,122`) |

### One clip's overlay

| # | Check | Result |
|---|---|---|
| C1 | GET `/api/jobs/{jid}/clips/{cid}/overlay` (real clip) | 200 with items, `line` (a page-printable description), `templates`, `on`, and a note |
| C2 | GET with a bad job id | 404 `No such video.` |
| C3 | GET with a bad clip id | 404 `No such clip.` |
| C4 | PUT clip overlay with an unparseable body (`{{{`) | **500 `Internal Server Error`** (finding 1) |
| C5 | PUT clip overlay with an empty body | **500 `Internal Server Error`** (finding 1) |
| C9 | PUT with valid items on a done clip | 200 `Saved. The next re-make draws them.` |
| C10 | PUT with `template` naming a layout that does not exist (and is not the clip's current) | 400 `No such layout.` |
| C11 | PUT with a real template id and `items: []` | 200, clip inherits the template |
| K1 | PUT with a template id that was deleted but is still the clip's current one | 200, template cleared to `""`, own items kept — the keep-editable branch (`studio/api_overlay.py:183-186`) works |
| — | PUT on a clip that is `rendering`/`queued` (409 branch, `studio/api_overlay.py:178-179`) | not reachable live (no queued clip existed); branch read and is sound |

### Previews

| # | Check | Result |
|---|---|---|
| P1 | GET preview `?base=true` (clean frame for the editor's layers) | 200 `image/jpeg`, 105,978 bytes |
| P2 | GET preview with a template (items empty -> template's items drawn) | 200 `image/jpeg`, 111,827 bytes |
| P3 | POST preview with explicit items | 200 `image/jpeg`, 108,670 bytes |
| P4 | POST preview with only a template | 200 `image/jpeg`, 111,827 bytes — byte-identical to P2, so both routes draw the same frame |
| P5 | POST preview with an unparseable body | **500 `Internal Server Error`** (finding 1) |
| — | Preview error path (no video source) | read: `peek.source` raises, caught at `studio/api_overlay.py:265-266` -> 502 `That preview could not be drawn: ...` |

### The every-clip toggle

| # | Check | Result |
|---|---|---|
| E1 | PUT `/api/jobs/{jid}/overlay-template` with a real template | 200, note `Every clip of this video now draws QA test layout v2.` |
| E1b | GET the clip afterwards | clip inherited `tcfd67c` |
| E2 | PUT with a nonexistent template | 400 `No such layout.` |
| E3 | PUT `{"template":"","clips":false}` | 200, note `No layout. Clips draw what they were each given.` — and the clip kept its own `tcfd67c` (only the job level was cleared) |
| E4 | PUT with an unparseable body | **500 `Internal Server Error`** (finding 1) |

### Cross-cutting

- Auth: `_uid` raises 401 when there is no session (`studio/api_overlay.py:24-28`);
  sign-in is off by default so live calls passed the gate as the local owner.
- `ctx.bump()` is called on both writes that change what a user sees
  (`studio/api_overlay.py:201,307`).
- Cache headers: previews are `private, no-store` (`:270`), shelf images
  `private, max-age=600` (`:106`).
- Throttle branches (429 on upload/save/preview) call `auth.throttle`
  (`:31-35`); not live-tested here (they would pollute state), messages are
  plain-language.
- The shared drawing guarantee holds: the preview and the render both call
  `overlay.chain`, and `_preview` brings the frame to 1080x1920 before
  anything is placed on it (`studio/api_overlay.py:246-259`).
- `render._workdir()` returns a unique fresh temp folder per call
  (`studio/render.py:463-488`), so the preview's `shutil.rmtree` cleanup
  (`:268`) can never delete another job's files.
- The shipped editor never calls the POST preview route: the only
  `overlay/preview` caller in `web/` is the GET with `base=true`
  (`web/feat/pictures.js:189`); the editable arrangement is drawn in the DOM
  (`place()`, `web/feat/pictures.js:192-199`). Not a defect by itself, but it
  means the DOM preview, not the server's ffmpeg drawing, is what the person
  judges while placing.
- `tests/` has no direct test of these routes (`test_picture_controls.py`
  exercises the frontend against a mock api), so the server-side behaviour
  rests on this audit's curl checks.

## Findings

| severity | where | what | evidence | fix |
|---|---|---|---|---|
| critical | `studio/api_overlay.py:130,173,217,295` | Sending an unparseable JSON body (or no body) to any of the four body-reading routes crashes with a plain-text 500 instead of a 400. The `isinstance(body, dict)` guards only catch parseable non-dict bodies. | Measured: PUT `/api/overlays/templates` with `not json at all` -> 500 `Internal Server Error`; empty body -> 500; PUT clip overlay `{{{` -> 500; empty -> 500; POST preview `nope` -> 500; PUT job overlay-template `bad` -> 500; empty -> 500. JSON `null` body is handled (400), which proves the gap is exactly the parse step: `await request.json()` raises an unhandled `json.JSONDecodeError`. | Add one helper, e.g. `async def _obj(request) -> dict:` that reads the body, catches `ValueError`, and raises `HTTPException(400, "Send the layout as an object.")`, and use it at all four sites (templates save, clip overlay write, preview, job toggle). |
| important | `studio/server.py:121-122` cap vs `studio/overlay.py:29` (`MAX_BYTES = 12 * 1024 * 1024`) and `studio/api_overlay.py:76-78` | An ordinary real logo (1.0 MB) cannot be uploaded at all: the request gate cuts every non-`/api/upload` body at 256 KB and answers `That request is too large.` — no number, no guidance. The route's own 12 MB cap and its careful "shrink it and try again" message are unreachable, and the editor sends the file with no client-side size check, so the person only learns after the upload fails. | Measured A10: 1,051,924-byte ordinary PNG -> 413 `{"detail":"That request is too large."}`; A9: 2,154-byte logo -> 200. Gate cap: `cap = ... else 256 * 1024` for any path other than `/api/upload` (`studio/server.py:120-122`). Frontend: `web/feat/pictures.js:494-513` posts `FormData` without a size check. | Either let `/api/overlays/upload` through the gate up to `overlay.MAX_BYTES` (as `/api/upload` is), or make the two caps agree and put the number in the gate message ("The limit is 256 KB."). Also add a client-side check against `file.size` with the same limit so the message appears before the upload. |
| minor | `studio/overlay.py:66` (`stem, ext = spoken, "png"`) and `studio/api_overlay.py:109-111` | Every upload is stored under a `.png` name whatever its real format, and then served with `content-type: image/png` even when the bytes are JPEG. Browsers sniff and still render it, but the Content-Type header lies, and a file saved from the page carries a wrong extension. | Measured M1: a real JPEG uploaded -> stored `jpegshot-8ec437.png`. M2: GET it -> 200 `content-type: image/png` while the bytes begin `FF D8 FF E0` (JPEG magic). | Pick the extension from the format `_identify` already reads (ffprobe gives `codec_name`), or serve by sniffed content instead of the suffix. |
| minor | GET `/api/overlays/image/{name}` with a dot path | `/api/overlays/image/..` is answered with a 307 that redirects to the shelf list instead of a 404. Cosmetic: the slug guard (`studio/overlay.py:56-59`) runs before any file access, so nothing is ever served through it — the encoded form already 404s. | Measured A7: 307 with `location: http://127.0.0.1:8798/api/overlays`, followed -> 200 (the shelf JSON). A7b: `..%2F..%2Fetc%2Fpasswd` -> 404. | Not worth a fix in the route (Starlette normalizes the URL before routing). If desired, reject names whose slug form is not `clean_slug`-clean with 404 and document that the bare `..` case is a framework redirect. |
| minor | `studio/api_overlay.py:303-305` (the `clips` loop of PUT `/api/jobs/{jid}/overlay-template`) | The every-clip toggle silently replaces a clip's own layout choice: every clip's `overlay_template` is overwritten when `clips` is true (the default). Only clips with their own pictures keep drawing them (items win in the drawing logic). The UI hint only promises "unless a clip was given its own pictures" (`web/feat/pictures-dialog.js:47`), so copy and behaviour agree — but the person is never told their per-clip layout was replaced. | Code: `for clip in job.get("clips") or []: clip["overlay_template"] = tid` — unconditional. Measured E1b: the clip inherited the job template; E3 (`clips:false`) left the clip's own `tcfd67c` in place. | In the response note, say how many clips had their own layout and now wear this one (e.g. "3 clips had their own layout; they now draw X."), or skip clips whose `overlay_template` differs from the previous job-level value so a per-clip choice survives a toggle. |

## Not findings (checked and sound)

- All error messages are plain-language and specific, with one exception each
  covered above (the 413 and the 500). The 429 messages ("That is a lot of
  pictures at once. Give it a minute.") are exemplary.
- Empty states: both list routes carry beginner notes (`:65,122`), matched by
  the frontend.
- The preview cannot show the right arrangement over the wrong picture: the
  frame comes from `peek.source` (the clip's piece, the uploaded file, or a
  slice) and is fitted to 1080x1920 before placements are drawn (`:246-259`).
- Deleted-template references degrade safely: clips keep their own pictures
  editable (`:183-186`, verified K1) and the preview falls back to the clean
  frame.
- Ownership: every job/clip route checks `job.get("user") != ctx.uid()` ->
  404 (`:38-44`); the uid never comes from the body.
