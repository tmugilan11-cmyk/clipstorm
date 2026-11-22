"""Read, edit or draft the plain-text Instagram caption. Nothing here renders a frame."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import auth, creators, ctx, igcaption, jobs

router = APIRouter()


def _me(request):
    user = getattr(request.state, "user", None)
    if user is None:
        user = auth.local_user()
    if getattr(user, "disabled", False):
        raise HTTPException(403, "This account is switched off.")
    return user


def _clip(jid, cid):
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such video.")
    clip = next((c for c in job.get("clips", []) if c.get("id") == cid), None)
    if clip is None:
        raise HTTPException(404, "No such clip.")
    return job, clip


def _creator(job):
    return (creators.get(job.get("creator")) if job.get("creator") else None) or {}


async def _body(request):
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Send the caption as a JSON object.")
    if not isinstance(body, dict):
        raise HTTPException(400, "Send the caption as a JSON object.")
    return body


def _choices(body, clip):
    lang = body.get("lang", clip.get("ig_language", "original"))
    form = body.get("format", clip.get("ig_format", "natural"))
    if not isinstance(lang, str) or not isinstance(form, str) or lang not in igcaption.LANGS or form not in igcaption.FORMATS:
        raise HTTPException(400, "Choose a language and writing style from the list.")
    return lang, form


@router.get("/api/igcaption/looks")
def igcaption_looks(request: Request) -> dict:
    # Same account check as the other routes in this router, so the gate is uniform.
    _me(request)
    # Languages carry labels like the formats do, so a reader of this endpoint alone
    # sees plain names instead of bare IDs such as "ja".
    return {"formats": [{"id": k, "label": v} for k, v in igcaption.FORMATS.items()],
            "langs": [{"id": k, "label": igcaption.LANG_NAMES.get(k, k)} for k in igcaption.LANGS],
            "limit": igcaption.MAX_LENGTH,
            "note": "Instagram captions are plain text under the post. Font, color and animation are controlled by Instagram."}


@router.get("/api/jobs/{jid}/clips/{cid}/igcaption")
def igcaption_for(jid: str, cid: str, request: Request) -> dict:
    user = _me(request)
    with ctx.as_user(user.id):
        job, clip = _clip(jid, cid)
        return igcaption.view(clip, _creator(job))


@router.put("/api/jobs/{jid}/clips/{cid}/igcaption")
async def igcaption_write(jid: str, cid: str, request: Request) -> dict:
    user = _me(request)
    body = await _body(request)
    with ctx.as_user(user.id):
        job, clip = _clip(jid, cid)
        lang, form = _choices(body, clip)
        enabled = body.get("enabled", clip.get("ig_caption_enabled", False))
        if not isinstance(enabled, bool):
            raise HTTPException(400, "Choose whether to use a separate Instagram caption.")
        try:
            text = igcaption.validate_text(body.get("caption", clip.get("ig_caption", "")))
        except ValueError as e:
            raise HTTPException(400, str(e))
        # Check the whole input first. An invalid update must leave the previous caption untouched.
        clip.update(ig_caption=text, ig_caption_enabled=enabled, ig_language=lang, ig_format=form)
        jobs.save(job)
        ctx.bump()
        return igcaption.view(clip, _creator(job))


@router.post("/api/jobs/{jid}/clips/{cid}/igcaption/generate")
async def igcaption_generate(jid: str, cid: str, request: Request) -> dict:
    user = _me(request)
    body = await _body(request)
    with ctx.as_user(user.id):
        job, clip = _clip(jid, cid)
        lang, form = _choices(body, clip)
        try:
            auth.throttle("igcaption:" + user.id, 10, 300)
        except auth.AuthError as e:
            raise HTTPException(429, str(e))
        try:
            return await run_in_threadpool(igcaption.generate, dict(clip), lang, form)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            from . import ai
            raise HTTPException(502, "The caption could not be generated. " + (ai.explain(e) or str(e))[:240])
