"""The routes behind the picture editor: the shelf of images, and the templates that arrange them.

A template is what makes the toggle worth having. The person makes a poster and a logo once, saves them as a template,
and from then on a clip that is told to use that template comes out with them already on it, in the right places.

Nothing here draws. The drawing is `overlay.chain`, called from the render worker, so a preview and a finished clip
are made by the same code.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from . import auth, brand, ctx, jobs, overlay

router = APIRouter()


def _uid(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Sign in first.")
    return user.id


def _throttle(key: str, limit: int, window: int, said: str) -> None:
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, said)


async def _obj(request: Request, said: str) -> dict:
    """The request body as an object, or a 400 that says so.

    An empty body, or one that is not readable JSON, would otherwise escape as a 500: the four routes here are the
    only JSON handlers in the app that read the body by hand, so the catch lives with them.
    """
    try:
        body = await request.json()
    except ValueError as e:                       # malformed JSON, or an empty body
        raise HTTPException(400, said) from e
    if not isinstance(body, dict):
        raise HTTPException(400, said)
    return body


def _job_or_404(jid: str) -> dict:
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such video.")
    if job.get("user") != ctx.uid():
        raise HTTPException(404, "No such video.")
    return job


def _clip_or_404(job: dict, cid: str) -> dict:
    for clip in job.get("clips") or []:
        if clip.get("id") == cid:
            return clip
    raise HTTPException(404, "No such clip.")


# ---------------------------------------------------------------- the shelf


@router.get("/api/overlays")
async def overlays_list(request: Request) -> dict:
    """Every picture on the shelf, and every template."""
    _uid(request)
    rows = overlay.library()
    return {"ok": True, "images": rows, "count": len(rows),
            "templates": overlay.templates(),
            "most": overlay.MAX_ITEMS,
            "note": "" if rows else "No pictures yet. Add a logo or a poster and it stays here for every clip."}


@router.post("/api/overlays/upload")
async def overlays_upload(request: Request, file: UploadFile = File(...)) -> dict:
    """Keep one picture. The type is judged by its content, not by its name."""
    uid = _uid(request)
    _throttle(f"ovu:{uid}", 20, 300, "That is a lot of pictures at once. Give it a minute.")
    data = await file.read()
    if not data:
        raise HTTPException(400, "That file is empty.")
    if len(data) > overlay.MAX_BYTES:
        raise HTTPException(400, f"That picture is {len(data) / 1048576:.1f} MB. The most PeakCut will keep is "
                                f"{overlay.MAX_BYTES // 1048576} MB, so shrink it and try again.")
    title = Path(str(file.filename or "picture")).stem
    name = overlay.make_slug(title, {r["name"] for r in overlay.library()})
    try:
        path = overlay.store(name, data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    shape = overlay.length(path.name)
    return {"ok": True, "image": {"name": path.name, "bytes": path.stat().st_size,
                                  "width": shape.get("width", 0), "height": shape.get("height", 0)}}


@router.delete("/api/overlays/{name}")
async def overlays_drop(request: Request, name: str) -> dict:
    """Take one picture off the shelf. Templates that named it simply stop drawing it."""
    _uid(request)
    if not overlay.forget(name):
        raise HTTPException(404, "That picture is not on the shelf.")
    return {"ok": True, "gone": name}


@router.get("/api/overlays/image/{name}")
async def overlays_image(request: Request, name: str) -> FileResponse:
    """One picture, for the editor and for the preview. Only names PeakCut made are served."""
    _uid(request)
    path = overlay.path_for(name)
    if not path:
        raise HTTPException(404, "That picture is not on the shelf.")
    return FileResponse(str(path), media_type=_mime(path.suffix), headers={"Cache-Control": "private, max-age=600"})


def _mime(ext: str) -> str:
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(
        ext.lower().lstrip("."), "image/png")


# ---------------------------------------------------------------- templates


@router.get("/api/overlays/templates")
async def templates_list(request: Request) -> dict:
    _uid(request)
    rows = overlay.templates()
    return {"ok": True, "templates": rows, "count": len(rows),
            "note": "" if rows else "No layouts yet. Put a picture where you want it and save it as a layout."}


@router.put("/api/overlays/templates")
async def templates_save(request: Request) -> dict:
    """Create or replace one template. An empty id makes a new one."""
    uid = _uid(request)
    _throttle(f"ovt:{uid}", 40, 300, "That is a lot of layout saves at once.")
    body = await _obj(request, "Send the layout as an object.")
    items = overlay.clean_items(body.get("items"))
    if body.get("items") and not items:
        raise HTTPException(400, "None of those pictures are on the shelf, so the layout would draw nothing. "
                                 "Add the pictures first, then place them.")
    if not items:
        # a layout with no pictures on it would draw nothing: saving one is a claim the page cannot show
        raise HTTPException(400, "There is nothing to save yet: this layout has no pictures on it. "
                                 "Place a picture first, then save it.")
    got = overlay.save_template(body.get("id") or "", body.get("name") or "", items)
    return {"ok": True, "template": got}


@router.delete("/api/overlays/templates/{tid}")
async def templates_drop(request: Request, tid: str) -> dict:
    _uid(request)
    if not overlay.drop_template(tid):
        raise HTTPException(404, "No such layout.")
    return {"ok": True, "gone": tid}


# ---------------------------------------------------------------- on one clip


@router.get("/api/jobs/{jid}/clips/{cid}/overlay")
async def clip_overlay_read(request: Request, jid: str, cid: str) -> dict:
    """What this clip draws on itself right now, and whether it came from a template."""
    _uid(request)
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    tid = str(clip.get("overlay_template") or "")
    items = overlay.clean_items(clip.get("overlay") or [])
    tpl = overlay.template(tid) if tid else None
    return {"ok": True,
            "clip": {"id": clip.get("id"), "template": tid, "template_name": (tpl or {}).get("name", ""),
                     "items": items, "line": overlay.describe(items)},
            "templates": overlay.templates(),
            "on": bool(items),
            "note": ("This clip draws " + overlay.describe(items)) if items else "This clip draws no pictures."}


@router.put("/api/jobs/{jid}/clips/{cid}/overlay")
async def clip_overlay_write(request: Request, jid: str, cid: str) -> dict:
    """Set what this clip draws: a template, or its own placements, or both (its own wins over the template's)."""
    _uid(request)
    body = await _obj(request, "Send the overlay as an object.")
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    if clip.get("status") in ("rendering", "queued"):
        raise HTTPException(409, "That clip is being made right now. Wait for it to finish, then change it.")

    tid = str(body.get("template") or "").strip()
    if tid and not overlay.template(tid):
        if tid != str(clip.get("overlay_template") or ""):
            raise HTTPException(400, "No such layout.")
        # A deleted layout can still be referenced by old clips. Keep their own pictures editable.
        tid = ""
    wanted = body.get("items")
    if wanted is None:
        items = clip.get("overlay") or []
    else:
        items = overlay.clean_items(wanted)
        if wanted and not items:
            raise HTTPException(400, "None of those pictures are on the shelf, so nothing would be drawn.")
    if items == (clip.get("overlay") or []) and tid == str(clip.get("overlay_template") or ""):
        return {"ok": True, "clip": {"id": clip.get("id"), "template": tid, "items": items},
                "note": "Nothing about the pictures changed."}
    clip["overlay"] = items
    clip["overlay_template"] = tid
    clip["overlay_at"] = int(time.time())
    jobs.save(job)
    ctx.bump()
    return {"ok": True,
            "clip": {"id": clip.get("id"), "template": tid, "items": items,
                     "template_name": (overlay.template(tid) or {}).get("name", "")},
            "note": "Saved. The next re-make draws them."}


@router.post("/api/jobs/{jid}/clips/{cid}/overlay/preview")
async def clip_overlay_preview(request: Request, jid: str, cid: str) -> Response:
    """One still frame of the clip with the pictures drawn on it, so the arrangement can be judged before a render.

    This is the same drawing code as the real render - only the encode is shorter - so what is seen here is what
    comes out.
    """
    uid = _uid(request)
    _throttle(f"ovp:{uid}", 30, 300, "That is a lot of previews at once. Give it a moment.")
    body = await _obj(request, "Send the arrangement as an object.")
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    items = overlay.clean_items(body.get("items")) if body.get("items") is not None else \
        overlay.clean_items(clip.get("overlay") or [])
    tid = str(body.get("template") or "").strip()
    if tid and not items:
        tpl = overlay.template(tid)
        items = overlay.clean_items((tpl or {}).get("items") or [])
    return _preview(job, clip, items)


def _preview(job: dict, clip: dict, items: list) -> Response:
    """Renders one frame at the clip's middle second with the pictures on it.

    The frame comes from the same source the render would use (peek.source knows the three places a clip's video can
    be: the clip's own piece, the uploaded file, or a throwaway slice of a link), so a preview cannot show the right
    arrangement over the wrong picture.
    """
    from . import media, peek, render

    work = render._workdir()
    try:
        src, offset = peek.source(job, clip, work)          # offset is the video-time of the clip's second zero
        start = float(clip.get("start") or 0.0)
        end = float(clip.get("end") or start + 3.0)
        at = max(0.0, (start + end) / 2 - offset)
        args = ["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(src)]
        # The frame is brought to the size a finished clip is (1080x1920) BEFORE anything is placed on it. A slice of
        # a link comes back at a lower resolution, and placing a logo by fractions of 1080 on a 720-wide picture put
        # it off the right edge - a preview that is wrong about the one thing it exists to show.
        fit = (f"scale={render.W}:{render.H}:force_original_aspect_ratio=increase,"
               f"crop={render.W}:{render.H},setsar=1")
        if items:
            inputs, steps = overlay.chain(items, Path(work), render.W, render.H, start_input=1)
            if steps:
                args += inputs + ["-filter_complex", f"[0:v]{fit}[v0];" + steps, "-map", "[vout]"]
            else:
                args += ["-vf", fit]
        else:
            args += ["-vf", fit]
        args += ["-frames:v", "1", "-q:v", "3", "shot.jpg"]
        media.run(args, cwd=str(work))
        data = (Path(work) / "shot.jpg").read_bytes()
    except HTTPException:
        raise
    except Exception as e:      # noqa: BLE001 - a preview that cannot be made says why, in words
        raise HTTPException(502, "That preview could not be drawn: " + str(e)[:200])
    finally:
        shutil.rmtree(str(work), ignore_errors=True)
    return Response(content=data, media_type="image/jpeg",
                    headers={"Cache-Control": "private, no-store"})


@router.get("/api/jobs/{jid}/clips/{cid}/overlay/preview")
async def clip_overlay_preview_get(request: Request, jid: str, cid: str, base: bool = False) -> Response:
    """Draw the saved pictures or give the editor a clean frame for its editable layers."""
    _uid(request)
    job = _job_or_404(jid)
    clip = _clip_or_404(job, cid)
    if base:
        return _preview(job, clip, [])
    items = overlay.clean_items(clip.get("overlay") or [])
    tid = str(clip.get("overlay_template") or "")
    if tid and not items:
        items = overlay.clean_items((overlay.template(tid) or {}).get("items") or [])
    return _preview(job, clip, items)


# ---------------------------------------------------------------- the toggle on a job


@router.put("/api/jobs/{jid}/overlay-template")
async def job_template(request: Request, jid: str) -> dict:
    """The toggle: every clip of this job uses this layout, unless it was given its own."""
    _uid(request)
    body = await _obj(request, "Send the layout as an object.")
    job = _job_or_404(jid)
    tid = str(body.get("template") or "").strip()
    if tid and not overlay.template(tid):
        raise HTTPException(400, "No such layout.")
    job["overlay_template"] = tid
    picked = 0
    if body.get("clips", True):
        # clips that had picked their own layout lose it when this loop runs, so the note says how many
        picked = sum(1 for clip in job.get("clips") or []
                     if str(clip.get("overlay_template") or "") and str(clip.get("overlay_template") or "") != tid)
        for clip in job.get("clips") or []:
            clip["overlay_template"] = tid
    jobs.save(job)
    ctx.bump()
    tpl = overlay.template(tid) if tid else None
    note = (f"Every clip of this video now draws {tpl['name']}." if tpl
            else "No layout. Clips draw what they were each given.")
    if picked and tpl:
        note += (f" {picked} of them had picked their own layout; this one replaces it." if picked == 1
                 else f" {picked} of them had picked their own layouts; this one replaces them.")
    return {"ok": True, "template": tid, "name": (tpl or {}).get("name", ""), "note": note}
