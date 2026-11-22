"""What the AI would change in a saved brand, offered as a preview and never applied on its own.

    POST /api/brandai/suggest    ask for a brand change, answered as a preview the person must accept

The judgement is `studio/brand_ai.py`: it maps the five settings the Improve engine may touch onto the
keys the saved brand document actually keeps, and refuses with sentences anything the document cannot
hold. This route reads the same facts the Improve engine reads (`studio/learn.facts`) and asks the AI
for values through `ai.call`, then answers with `brand_ai.preview` — before, after, and one line per
setting. It writes NOTHING: applying is the person pressing save on the brand they already control
(`PUT /api/brand`).

It deliberately does not import `server.py`, for the same circular-import reason as every other `api_` module.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import ai, auth, brand, brand_ai, learn, safe

router = APIRouter()

# The answer shape the AI must return. `ai.call` enforces it, so this route never parses a fence.
_SCHEMA = {"type": "object", "properties": {
    "style": {"type": "string"},
    "hook_words": {"type": "string"},
    "clip_len": {"type": "number"},
    "sound": {"type": "string"},
    "captions": {"type": "boolean"},
    "why": {"type": "string"},
}}


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if u is None:
        u = auth.local_user()
    if getattr(u, "disabled", False):
        raise HTTPException(403, "This account is switched off.")
    return u


def _throttle(key: str, limit: int, window: int, msg: str) -> None:
    """The same rate limit `server._throttle` applies, without importing server.py."""
    try:
        auth.throttle(key, limit, window)
    except auth.AuthError:
        raise HTTPException(429, msg)


@router.post("/api/brandai/suggest")
async def brandai_suggest(request: Request) -> dict:
    """Ask the AI for brand values, answered as a preview that changes nothing.

    One ask is slow by design: an answer that must match the schema can take about half a
    minute (measured 41.0 s here), so a page that sends this should say so under the button."""
    u = _me(request)
    _throttle("bsg:" + u.id, 10, 300,
              "That is a lot of brand suggestions at once. Give it a moment; even one ask can take about half a minute.")
    if not ai.ready():
        raise HTTPException(400, "No AI is set up, so PeakCut cannot suggest brand values. Set one up under AI.")
    try:
        raw = await request.json()
    except Exception:  # noqa: BLE001 - an empty body is allowed; every key is optional
        raw = {}
    about = str((raw or {}).get("about") or "").strip()[:400] if isinstance(raw, dict) else ""
    try:
        got = await run_in_threadpool(_work, u.id, about)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, "The suggestion did not finish: " + safe.friendly(e))
    return got


def _work(uid: str, about: str) -> dict:
    """The slow part: facts, the AI ask, and the preview. Runs off the event loop."""
    facts = []
    try:
        got = learn.facts(28)
        facts = [str(x)[:200] for x in (got.get("lines") or [])][:8]
    except Exception:  # noqa: BLE001 - facts are context, not a requirement
        facts = []
    names = ", ".join(sorted(brand_ai.known())) or "none this build accepts"
    ask_text = (
        "You may suggest new values for a short-video brand. The settings that can change: "
        + names + ". "
        + ("The person adds this about what they want: " + about + ". " if about else "")
        + "Here is what PeakCut knows about their results so far: "
        + (" ".join(facts) if facts else "nothing measured yet.") + " "
        + "Leave out any key you have no better value for. Never invent a look or a sound that was not "
        + "listed, and say why in one short sentence.")
    last = None
    out = None
    for model in ai.models():
        try:
            out, _sent, _wrote = ai.call(model, ask_text, _SCHEMA, 60.0)
            break
        except Exception as e:  # noqa: BLE001 - the next model may answer where this one failed
            last = e
    if out is None:
        said = ai.explain(last) if last else ""
        said = said or (f"{type(last).__name__}: {last}" if last else "")
        raise RuntimeError(f"The AI did not answer: {said or 'no model tried'}")
    values = out if isinstance(out, dict) else {}
    changes = {k: values[k] for k in values if k in brand_ai.known()}
    why = str(values.get("why") or "").strip()[:300]
    if not changes:
        return {"ok": True, "changes": {}, "lines": [], "before": brand.load(uid), "why": why,
                "note": "The AI answered, but with nothing this brand accepts. Nothing was suggested.",
                "facts": facts}
    got = brand_ai.preview(uid, changes)
    lines = [str(x) for x in (got.get("lines") or [])]
    return {"ok": True, "changes": changes, "lines": lines,
            "before": got.get("before") or brand.load(uid), "after": got.get("after"),
            "why": why, "facts": facts}
