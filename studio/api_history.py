"""Per-clip version history: what was made, when, and which take the person wants to keep.

This is the doorway in front of the clip's own past:

    GET   /api/jobs/{jid}/clips/{cid}/history   every version of one clip, with what is on the disk right now
    PATCH /api/jobs/{jid}/clips/{cid}/history   {"keep": v} marks one version as the keeper

The render path calls `record_version` after each successful re-make, so this file never starts a render and never
renames a file: it only remembers names and reads the folder they land in. When a clip has no remembered history yet
(clips made before this existed), the clip's folder is read instead: `<clip>_v3.mp4` files, plus the clip's own file,
which every render so far has written over. Nothing is shown that is not really there: `exists` and `bytes` are
checked against the disk each time. `server.py` mounts this router like the other `api_*` ones.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request

from . import jobs

router = APIRouter()

VERSIONS_KEEP = 12        # how many versions a clip remembers; the oldest drop off as new ones arrive

_VERSION_FILE = re.compile(r"_v(\d+)\.mp4$")   # the name style of a remembered take: <clip>_v3.mp4


def _me(request: Request):
    """The signed-in person for this request, exactly as `server._me` would return them."""
    u = getattr(request.state, "user", None)
    if not u:
        raise HTTPException(401, "Sign in first.")
    return u


def _uid(request: Request) -> str:
    """The person's id as a plain string, which is what the data files are keyed by."""
    u = _me(request)
    return str(getattr(u, "uid", None) or getattr(u, "id", None) or getattr(u, "email", "") or "default")


def _now_iso() -> str:
    """The current moment as UTC ISO text, which is how versions remember when they were made."""
    return datetime.now(timezone.utc).isoformat()


def _vnum(v) -> int:
    """The number of a version, or -1 when it does not hold a plain number (a hand-edited entry)."""
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


def _plain_name(name: str) -> bool:
    """A bare file name with no folder parts in it, which is all a clip's own files are ever called."""
    return bool(name) and name not in (".", "..") and not any(sep in name for sep in ("/", "\\", "\x00"))


def record_version(clip: dict, file_name: str) -> None:
    """Remember one rendered file as the clip's newest version, the oldest entries dropping off after VERSIONS_KEEP.

    Only touches the clip dict; the caller saves the job afterwards, which is what `jobs.render_one` already does
    at the end of every render.
    """
    versions = clip.get("versions")
    if not isinstance(versions, list):
        versions = clip["versions"] = []
    # Numbered after the newest take, not after the list's length: once the cap starts dropping old takes the
    # length stops growing, and counting from it would hand every new take the same number.
    last = _vnum(versions[-1].get("v")) if versions else 0
    versions.append({"v": max(len(versions), last) + 1, "file": str(file_name or ""), "made_at": _now_iso()})
    del versions[:-VERSIONS_KEEP]


def _clip_or_404(jid: str, cid: str):
    """The job and the one clip of it, only when both belong to whoever this code runs for."""
    job = jobs.get(jid)
    if not job:
        raise HTTPException(404, "No such job.")
    clip = next((c for c in (job.get("clips") or []) if str(c.get("id")) == str(cid)), None)
    if not clip:
        raise HTTPException(404, "No such clip in this job.")
    return job, clip


def _clips_dir(job: dict) -> Path:
    """The folder a job's rendered clips land in, beside the job's own files."""
    return Path(job.get("dir") or "") / "clips"


def _mtime_iso(path: Path) -> str:
    """When a file last changed, as UTC ISO text; empty when the file cannot be looked at."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return ""


def _entry(v: dict, clips_dir: Path) -> dict:
    """One line of the history, with `exists` and `bytes` read from the disk this moment, never guessed."""
    name = str(v.get("file") or "")
    f = clips_dir / name if _plain_name(name) else None
    try:
        exists = bool(f and f.is_file())
        size = f.stat().st_size if exists else None
    except OSError:
        exists, size = False, None
    made = v.get("made_at")
    if not made and exists:
        made = _mtime_iso(f)               # an old entry without a time: the file itself remembers one
    return {"v": _vnum(v.get("v")), "file": name, "made_at": str(made or ""), "bytes": size, "exists": exists,
            "kept": bool(v.get("kept"))}


def _disk_versions(job: dict, clip: dict, cid: str) -> list:
    """Versions read back from the clips folder when the clip remembers none of its own.

    `<cid>_v3.mp4` files, oldest first, plus the clip's own current file, numbered as the clip counts itself. Times
    come from the files' own stamps and the clip's `made_at`; nothing is made up for a file that is not there.
    """
    clips_dir = _clips_dir(job)
    out = []
    try:
        pat = re.compile(re.escape(str(cid)) + r"_v(\d+)\.mp4$")
        for p in clips_dir.iterdir():
            m = pat.fullmatch(p.name)
            if m and p.is_file():
                out.append((int(m.group(1)), p.name, _mtime_iso(p)))
    except OSError:
        pass                                # a folder that cannot be read simply has nothing to show
    out.sort()
    current = str(clip.get("file") or "")
    if _plain_name(current) and (clips_dir / current).is_file():
        v = max(_vnum(clip.get("version")), 1)
        if all(v != found_v for found_v, _n, _t in out):
            made = clip.get("made_at")
            iso = (datetime.fromtimestamp(made, timezone.utc).isoformat()
                   if isinstance(made, (int, float)) and made > 0 else _mtime_iso(clips_dir / current))
            out.append((v, current, iso))
            out.sort()
    return out


def _history_payload(job: dict, clip: dict, cid: str) -> dict:
    """The history the page sees: {"versions": [...], "current": n}, oldest version first."""
    clips_dir = _clips_dir(job)
    remembered = clip.get("versions")
    if isinstance(remembered, list) and remembered:
        entries = [_entry(v, clips_dir) for v in remembered if isinstance(v, dict)]
        entries.sort(key=lambda e: e["v"])
    else:
        entries = [_entry({"v": v, "file": name, "made_at": made}, clips_dir)
                   for v, name, made in _disk_versions(job, clip, cid)]
    top = max((e["v"] for e in entries), default=0)
    current = max(_vnum(clip.get("version")), top, 0)
    return {"versions": entries, "current": current}


def _keep_mark(versions: list, want: int) -> bool:
    """Turn `kept` on for the version numbered `want` and off for all the others. True when that version exists."""
    hit = None
    for v in versions:
        if isinstance(v, dict) and _vnum(v.get("v")) == want:
            hit = v
            break
    if hit is None:
        return False
    for v in versions:
        if isinstance(v, dict):
            v["kept"] = v is hit
    return True


# ---------------------------------------------------------------- the routes
@router.get("/api/jobs/{jid}/clips/{cid}/history")
def clip_history(request: Request, jid: str, cid: str):
    """Every version of one clip, with what is really on the disk right now."""
    _uid(request)
    job, clip = _clip_or_404(jid, cid)
    return _history_payload(job, clip, cid)


@router.patch("/api/jobs/{jid}/clips/{cid}/history")
def keep_version(request: Request, jid: str, cid: str, body: dict = Body(...)):
    """Mark one version as the keeper, clearing the mark from the others, and remember that on the clip.

    When the clip has no remembered history yet, its files on the disk are read in first, so the mark lands on a
    version the person can actually see.
    """
    _uid(request)
    job, clip = _clip_or_404(jid, cid)
    try:
        want = int(str(body.get("keep")).strip())
    except (TypeError, ValueError):
        raise HTTPException(400, "Send the number of the version to keep, like {\"keep\": 2}.")
    if not (isinstance(clip.get("versions"), list) and clip["versions"]):
        clip["versions"] = [{"v": v, "file": name, "made_at": made}
                            for v, name, made in _disk_versions(job, clip, cid)]
    if not _keep_mark(clip["versions"], want):
        raise HTTPException(400, f"Version {want} is not in this clip's history. Look at the clip's history list and pick one of those.")
    jobs.save(job)
    return {"ok": True, "kept": want, **_history_payload(job, clip, cid)}
