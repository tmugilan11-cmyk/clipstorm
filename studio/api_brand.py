"""The brand document over HTTP: read it, save it, list the stock themes, put it back to nothing.

`studio/brand.py` already knows how to keep one document per person and what a safe one looks like; this module
is only the doorway. It lives in a router of its own so the whole brand feature stays in one file, and `server.py`
grows one line: `app.include_router(api_brand.router)`.

It deliberately does not import `server.py`. `server.py` imports this module to mount the router, so
`from .server import _me` would come back around on itself; the signed-in user is read off the request instead,
which is the very attribute `server._me` returns, filled in by the middleware before any route runs.

    GET   /api/brand          the saved document, the defaults, and the choices a settings page offers
    PUT   /api/brand          save a whole document; unknown keys are dropped by brand.normalise
    GET   /api/brand/themes   the stock theme names, sorted
    POST  /api/brand/reset    save an empty document, which is the neutral look

Every route is per-person: a brand belongs to whoever is signed in. None of them is admin-only, and one person's
brand is never shown to another."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import brand, ctx

router = APIRouter()


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them.

    Read off the request rather than imported from `server.py`, because `server.py` imports this module to mount
    the router and the import would come straight back. A request that somehow reaches a brand route with nobody
    signed in gets the same plain answer the rest of the app gives under /api."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


# Plain `def`, not `async def`: saving takes a file lock and touches the disk, so Starlette should run these on
# its worker pool rather than hold up every other request on the event loop.
@router.get("/api/brand")
def brand_get(request: Request) -> dict:
    """Everything the Brand tab needs: the saved document, the defaults, and the choices to offer."""
    return brand.public(_me(request).id)


@router.put("/api/brand")
async def brand_put(request: Request) -> dict:
    """Save one person's whole brand and hand back what was stored, which is what the page should show.

    The document may arrive on its own or wrapped in {"brand": ...}; both shapes are accepted, because a wrapper
    read as a document would look like an empty save and quietly wipe the brand.

    The body is read by hand instead of through `body: dict = Body(...)`: FastAPI answers a malformed body with its
    own 422 report, and a person who sees that learns nothing. Anything that is not a JSON object is a plain 400."""
    uid = _me(request).id
    try:
        body = await request.json()
    except ValueError as e:                       # malformed JSON, or an empty body
        raise HTTPException(400, "That brand could not be read. Save it again from the settings page.") from e
    if not isinstance(body, dict):
        raise HTTPException(400, "That brand could not be read. Save it again from the settings page.")

    inner = body.get("brand")
    doc = inner if isinstance(inner, dict) else body
    try:
        saved = await run_in_threadpool(brand.save, uid, doc)
    except ValueError as e:
        # brand.save wraps a disk problem in ValueError too, so this is the one place a bad save can surface.
        raise HTTPException(400, str(e) or "PeakCut could not save that brand.") from e
    ctx.bump(uid)          # another open tab polls /api/sync and refreshes on this
    return {"brand": saved}


@router.get("/api/brand/themes")
def brand_themes(request: Request) -> list:
    """The stock theme names a picker can offer. Sorted, so the order never depends on how the dict was built."""
    _me(request)
    return sorted(brand.THEMES)


@router.post("/api/brand/reset")
def brand_reset(request: Request) -> dict:
    """Back to the neutral look: an empty document, which brand.normalise fills in with the defaults.

    The saved theme goes with it — a reset that kept the theme would not look like a fresh account."""
    uid = _me(request).id
    try:
        saved = brand.save(uid, {})
    except ValueError as e:
        raise HTTPException(400, str(e) or "PeakCut could not reset that brand.") from e
    ctx.bump(uid)
    return {"brand": saved}
