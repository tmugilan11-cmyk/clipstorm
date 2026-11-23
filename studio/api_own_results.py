"""The doorway to `studio/own_results.py`: how this person's own posted clips did, and the guided YouTube connection.

    GET  /api/own-results                 the measured clips best to worst, and the sentences the judge is told
    POST /api/own-results/refresh         look at the numbers again now (starts at once, answers at once)
    GET  /api/own-results/youtube         where the YouTube connection stands: what is set, what is missing
    POST /api/own-results/youtube/test    a real tiny read against YouTube, answered in plain words

Saving the Google client id and secret goes through the existing PUT /api/apps, and the Connect button is the
existing /oauth/youtube/start. This file adds no way to see or change a secret: nothing here returns one.
It deliberately does not import `server.py`.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from . import accounts, auth, ctx, own_results

router = APIRouter()


def _me(request: Request):
    """The signed-in person, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u or not getattr(u, "id", None):
        raise HTTPException(401, "Please sign in.")
    return u


def _throttle(uid: str, limit: int = 30, window: int = 60) -> None:
    try:
        auth.throttle("ownresults:" + uid, limit, window)
    except auth.AuthError:
        raise HTTPException(429, "That is a lot of requests at once. Give it a moment.")


@router.get("/api/own-results")
async def results(request: Request) -> dict:
    u = _me(request)
    return await run_in_threadpool(own_results.report, u.id)


@router.post("/api/own-results/refresh")
async def refresh(request: Request) -> dict:
    u = _me(request)
    _throttle(u.id, 6, 60)
    started = own_results.refresh_async(u.id, force=True)
    got = await run_in_threadpool(own_results.report, u.id)
    got["started"] = started
    return got


@router.get("/api/own-results/youtube")
async def youtube(request: Request) -> dict:
    u = _me(request)

    def read():
        with ctx.as_user(u.id):
            return accounts.youtube_status()
    return await run_in_threadpool(read)


@router.post("/api/own-results/youtube/test")
async def youtube_test(request: Request) -> dict:
    u = _me(request)
    _throttle(u.id, 6, 60)
    return await run_in_threadpool(own_results.check_youtube, u.id)
