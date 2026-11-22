# Fix report: api_overlay.py + overlay.py

Fixer: agent-173. Assigned sections: `## studio/api_overlay.py` and `## studio/overlay.py` in `docs/qa/FINDINGS.md`; audit read: `docs/qa/audit/api-overlays.md`.

## Files owned

- `studio/api_overlay.py`
- `studio/overlay.py`

No other file was edited. `web/index.html` untouched (lead owns it). The server on 127.0.0.1:8798 was never restarted or killed.

## Fixes

### 1. [critical] Unparseable or non-object JSON body answered with a plain-text 500

Where: `studio/api_overlay.py` templates save, clip overlay write, preview, and job layout toggle (formerly lines 130, 173, 217, 295; now 145, 190, 232, 308).

Before: each route read `await request.json()` bare and then checked `isinstance(body, dict)`. A body that failed to parse raised before any guard, so `{{{` came back as an unhandled 500 with a stack trace. The `isinstance` guard only caught parseable non-objects.

Fix: one helper, `studio/api_overlay.py:38`:

```python
async def _obj(request: Request, said: str) -> dict:
    try:
        body = await request.json()
    except ValueError as e:
        raise HTTPException(400, said) from e
    if not isinstance(body, dict):
        raise HTTPException(400, said)
    return body
```

All four sites now call it with their own message: `studio/api_overlay.py:145` ("Send the layout as an object."), `:190` ("Send the overlay as an object."), `:232` ("Send the arrangement as an object."), `:308` ("Send the layout as an object."). This matches the sibling pattern already in `api_brand.py:58-63`. `grep` confirms `await request.json()` now appears exactly once in the file, inside `_obj`.

Proof: `python -m py_compile studio/api_overlay.py studio/overlay.py` (COMPILE_OK, exit 0). Live before/after probes of the new code were not possible without restarting the server (lead owns the restart); the pre-fix 500s were confirmed by read-only probes of the running server.

### 2. [important] Same root cause at the templates-save route

Covered by fix 1 (`studio/api_overlay.py:145`): a malformed body now gets a 400, not a 500.

Proof: same as fix 1.

### 3. [minor] Empty layout saved and answered 200 while drawing nothing

Where: `studio/api_overlay.py` templates save (formerly 133-137; now 149-153).

Before: `{"items": []}` (or no `items` at all) passed every check, was saved, and came back 200 with a template that draws nothing. The page already guards against this (`web/feat/pictures.js:590` only sends the PUT when pictures exist), but the route's contract did not match its own guard.

Fix: after the existing refusal for non-empty-but-invalid lists, an empty or missing `items` is now refused (`studio/api_overlay.py:150`):

```python
    if not items:
        # a layout with no pictures on it would draw nothing: saving one is a claim the page cannot show
        raise HTTPException(400, "There is nothing to save yet: this layout has no pictures on it. "
                                 "Place a picture first, then save it.")
```

Proof: `python -m py_compile` (as above).

### 4. [minor] Clip-layout toggle silently replaced clips that had picked their own layout

Where: `studio/api_overlay.py` job layout toggle (formerly 303-305; now 316-328).

Before: `clip["overlay_template"] = tid` ran unconditionally over every clip, so a clip that had its own layout lost it with no word about it in the response.

Fix: the clips that had picked their own layout (and differ from the new job-level one) are counted before the overwrite, and the response note says how many (`studio/api_overlay.py:317-328`):

```python
        picked = sum(1 for clip in job.get("clips") or []
                     if str(clip.get("overlay_template") or "") and str(clip.get("overlay_template") or "") != tid)
```

The note gains, when any were picked: " N of them had picked their own layout; this one replaces it." (singular) or "…their own layouts; this one replaces them." (plural). `clips: false` in the request body still leaves every clip's own layout alone (audit probe E3 behaviour unchanged; `body.get("clips", True)` default kept).

Proof: `python -m py_compile` (as above).

### 5. [minor] A real JPEG was stored as .png and served as image/png

Where: `studio/overlay.py` `make_slug` hardcoded the `.png` extension and `store()` moved the file in under that name with no check of what the bytes really are; `studio/api_overlay.py:109-111` then serves the file with a MIME type derived from the stored name, so a JPEG's `FF D8 FF` bytes went out with `Content-Type: image/png`.

Fix, in three parts:

- `studio/overlay.py:34`: `EXT_OF_CODEC = {"png": "png", "mjpeg": "jpg", "jpeg": "jpg", "webp": "webp"}` (ffprobe names a JPEG `mjpeg`).
- `studio/overlay.py:114-133`: `_identify` now asks ffprobe for `stream=width,height,codec_name` and returns the codec alongside width and height.
- `studio/overlay.py:85-127`: `store()` derives the real extension from the codec, re-spells the name (`stem = slug.rsplit(".", 1)[0]`), refuses a codec it does not keep, and never replaces a different existing picture (a name already taken gets a `-2`, `-3` suffix). Docstring updated.

Since the stored file name now matches the bytes' real format, the existing `_mime` mapping answers with a true `Content-Type`; no edit was needed in `api_overlay.py` for this finding.

Proof: `python -m py_compile` (as above). No live probe of the new store path without a restart; the mis-storing was confirmed pre-fix by audit probes M1/M2.

## Skipped

- `GET /api/overlays/image/{name}` answering 307 on a dotted name: finding raised outside my two sections, and the audit itself concludes "Not worth a fix in the route".
- `tests/test_updates.py` failing in `tests/run.py` (three FAIL lines then an IndexError at `tests/test_updates.py:60`): pre-existing. The baseline run started before any of my edits failed it identically; it concerns `studio/updates.py` git version detection, not the overlay routes, and I own neither file. Not fixed, reported to lead.

## Gates

- `python -m py_compile studio/api_overlay.py studio/overlay.py`: COMPILE_OK.
- `python tests/run.py` (full suite, 42 groups, throwaway server): every group passes except the one pre-existing failure, `FAILED: the new-version notice` (testrun exit 1), whose three FAIL lines are identical to the baseline run before any edit. 41 of 42 groups green.

Fixed Python routes take effect only after the lead's final server restart.
