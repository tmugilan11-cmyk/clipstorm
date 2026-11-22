"""Posters, logos and stickers: where they sit on the clip, and how they get there.

Three jobs, kept apart so each one can be checked on its own:

  * the shelf - images the person uploaded, stored once and reused on every clip;
  * the template - a named arrangement of images over a 1080x1920 frame. A placement is a picture, a position, a
    width, a rotation and an opacity, all as fractions of the frame so it means the same thing on any clip;
  * the chain - the ffmpeg inputs and filter steps that draw that arrangement onto a rendered clip.

Why fractions: a template is made by looking at a preview and dragging, and the preview is never the final size.
Storing `x=0.5, y=0.12, w=0.4` means "half way across, an eighth down, two fifths as wide" at any resolution,
which is the only way a template made in a 540-wide editor can be right in a 1080-wide render.

Nothing here decides what looks good. It stores what the person dragged, checks that it is possible, and draws it.
"""

from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import config

# A picture big enough to print, small enough that a render never waits on reading it.
MAX_BYTES = 12 * 1024 * 1024
# How many pictures one clip may carry. Each one costs an ffmpeg input and a filter step.
MAX_ITEMS = 8
ALLOWED = ("png", "jpg", "jpeg", "webp")
# The file extension each codec is kept under: ffprobe names a JPEG "mjpeg", a PNG "png", a WebP "webp".
EXT_OF_CODEC = {"png": "png", "mjpeg": "jpg", "jpeg": "jpg", "webp": "webp"}
NAME = re.compile(r"^[a-z0-9][a-z0-9\-]{0,60}\.[a-z]{3,4}$")

_lock = threading.Lock()
_cache: Dict[str, tuple] = {}


def home() -> Path:
    """Where every uploaded picture lives. Made on first use, because most installs never touch this."""
    folder = config.DATA_DIR / "overlays"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def shelf() -> Path:
    folder = home() / "images"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _templates_file() -> Path:
    return home() / "templates.json"


def clean_slug(said: str) -> Optional[str]:
    """A file name we made, or nothing. This is a path guard: callers pass it straight to `shelf()`."""
    name = str(said or "").strip().lower()
    return name if NAME.match(name) else None


def make_slug(title: str, taken: Optional[set] = None) -> str:
    """A plain file name from whatever the person called the picture, unique on this shelf."""
    spoken = re.sub(r"[^a-z0-9]+", "-", str(title or "").strip().lower())
    spoken = spoken.strip("-_")[:48] or "picture"
    stem, ext = spoken, "png"
    base = f"{stem}-{_short()}"
    name = f"{base}.{ext}"
    taken = taken or set()
    n = 2
    while name in taken or (shelf() / name).exists():
        name = f"{base}-{n}.{ext}"
        n += 1
    return name


def _short() -> str:
    import secrets

    return secrets.token_hex(3)


def store(name: str, data: bytes) -> Path:
    """Write the bytes, refusing anything that is not a picture we can draw.

    The check is by content, not by extension: a `.png` that is really a text file would fail at render time, on a
    person who only wanted to add their logo, with an ffmpeg message nobody can act on.

    The name is also re-spelled to the real format: a JPEG is kept as .jpg, not .png, so the type a browser is
    told when it comes back is true. A name that is already taken gets a -2, -3 suffix instead of replacing it.
    """
    slug = clean_slug(name)
    if not slug:
        raise ValueError("That file name is not one PeakCut makes. Upload it again and the name is chosen for you.")
    if not data:
        raise ValueError("That file is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"That picture is {len(data) / 1048576:.1f} MB. The most PeakCut will keep is "
                         f"{MAX_BYTES // 1048576} MB, so shrink it and try again.")
    folder = shelf()
    part = folder / (slug + ".part")
    part.write_bytes(data)
    try:
        shape = _identify(part)
        if not shape or not shape.get("width") or not shape.get("height"):
            raise ValueError("That file is not a picture PeakCut can read. PNG, JPG or WebP work.")
        ext = EXT_OF_CODEC.get(shape.get("codec") or "")
        if not ext:
            raise ValueError("That file is not a picture PeakCut can read. PNG, JPG or WebP work.")
        # the name carries the real format: a JPEG kept under .png would come back with a lying Content-Type
        stem = slug.rsplit(".", 1)[0]
        final = f"{stem}.{ext}"
        n = 2
        while final != slug and (folder / final).exists():
            final = f"{stem}-{n}.{ext}"
            n += 1
        part.replace(folder / final)
    except Exception:
        part.unlink(missing_ok=True)
        raise
    forget_cache()
    return folder / final


def _identify(path: Path) -> dict:
    """Width, height and codec, read by ffprobe. A picture has one video stream and no audio."""
    import subprocess

    from . import media

    try:
        out = media.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=width,height,codec_name", "-of", "json", str(path)])
    except Exception:
        return {}
    try:
        streams = json.loads(out).get("streams") or []
    except ValueError:
        return {}
    if not streams:
        return {}
    s = streams[0]
    return {"width": int(s.get("width") or 0), "height": int(s.get("height") or 0),
            "codec": str(s.get("codec_name") or "")}


def library() -> List[dict]:
    """Every picture on the shelf, newest first, with its real pixel size."""
    rows = []
    for f in sorted(shelf().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not f.is_file() or f.suffix.lower().lstrip(".") not in ALLOWED:
            continue
        shape = length(f.name)
        rows.append({"name": f.name, "bytes": f.stat().st_size,
                     "width": shape.get("width", 0), "height": shape.get("height", 0)})
    return rows


def length(name: str) -> dict:
    """Pixel size of one picture, remembered per file so a page full of logos is not a page full of ffprobe runs."""
    slug = clean_slug(name)
    if not slug:
        return {}
    path = shelf() / slug
    try:
        at = path.stat().st_mtime
    except OSError:
        return {}
    hit = _cache.get(slug)
    if hit and hit[0] == at:
        return hit[1]
    got = _identify(path)
    _cache[slug] = (at, got)
    return got


def forget(name: str) -> bool:
    slug = clean_slug(name)
    if not slug:
        return False
    path = shelf() / slug
    gone = False
    if path.exists():
        path.unlink()
        gone = True
    forget_cache()
    return gone


def forget_cache() -> None:
    _cache.clear()


def path_for(name: str) -> Optional[Path]:
    slug = clean_slug(name)
    if not slug:
        return None
    path = shelf() / slug
    return path if path.exists() else None


# ---------------------------------------------------------------- placements


def _num(v, lo: float, hi: float, fallback: float) -> float:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return fallback
    if n != n:                                  # NaN
        return fallback
    return max(lo, min(hi, n))


def clean_item(raw: dict) -> Optional[dict]:
    """One placement, or nothing if it cannot be drawn.

    `x` and `y` are the CENTRE of the picture as a fraction of the frame, because a person dragging a logo thinks
    about where its middle is. `rot` is degrees clockwise, `alpha` 0..1.
    """
    if not isinstance(raw, dict):
        return None
    name = clean_slug(raw.get("name") or raw.get("slug") or "")
    if not name or not (shelf() / name).exists():
        return None
    return {
        "name": name,
        "x": round(_num(raw.get("x"), -0.5, 1.5, 0.5), 4),
        "y": round(_num(raw.get("y"), -0.5, 1.5, 0.5), 4),
        "w": round(_num(raw.get("w"), 0.02, 1.5, 0.34), 4),
        "rot": round(_num(raw.get("rot"), -180.0, 180.0, 0.0), 1),
        "alpha": round(_num(raw.get("alpha"), 0.0, 1.0, 1.0), 2),
    }


def clean_items(raw) -> List[dict]:
    """Up to MAX_ITEMS placements, later ones drawn on top of earlier ones."""
    if not isinstance(raw, list):
        return []
    out = []
    for row in raw[:MAX_ITEMS]:
        got = clean_item(row)
        if got:
            out.append(got)
    return out


# ---------------------------------------------------------------- templates


def _read_templates() -> dict:
    path = _templates_file()
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"templates": []}
    if not isinstance(got, dict):
        return {"templates": []}
    rows = got.get("templates")
    return {"templates": rows if isinstance(rows, list) else []}


def templates() -> List[dict]:
    """Every saved arrangement. A template with no items is kept: it is a template being built."""
    out = []
    for row in _read_templates().get("templates", []):
        if not isinstance(row, dict):
            continue
        tid = str(row.get("id") or "").strip()[:40]
        if not tid:
            continue
        out.append({"id": tid, "name": str(row.get("name") or "Template")[:60],
                    "items": clean_items(row.get("items")), "at": row.get("at") or 0})
    return out


def template(tid: str) -> Optional[dict]:
    want = str(tid or "").strip()
    for row in templates():
        if row["id"] == want:
            return row
    return None


def save_template(tid: str, name: str, items) -> dict:
    """Create or replace one template. An empty `tid` makes a new one."""
    rows = _read_templates().get("templates", [])
    rows = [r for r in rows if isinstance(r, dict)]
    want = str(tid or "").strip()[:40]
    said = clean_items(items)
    import time

    now = int(time.time())
    if not want:
        want = "t" + _short()
        rows.append({"id": want, "name": str(name or "Template")[:60], "items": said, "at": now})
    else:
        for row in rows:
            if str(row.get("id") or "") == want:
                row["name"] = str(name or row.get("name") or "Template")[:60]
                row["items"] = said
                row["at"] = now
                break
        else:
            rows.append({"id": want, "name": str(name or "Template")[:60], "items": said, "at": now})
    _write(rows)
    return template(want) or {"id": want, "name": name, "items": said, "at": now}


def drop_template(tid: str) -> bool:
    rows = [r for r in _read_templates().get("templates", []) if isinstance(r, dict)]
    want = str(tid or "").strip()
    keep = [r for r in rows if str(r.get("id") or "") != want]
    if len(keep) == len(rows):
        return False
    _write(keep)
    return True


def _write(rows: List[dict]) -> None:
    with _lock:
        path = _templates_file()
        part = path.with_suffix(".part")
        part.write_text(json.dumps({"templates": rows}, indent=1), encoding="utf-8")
        part.replace(path)


# ---------------------------------------------------------------- the chain


def chain(items: List[dict], work: Path, frame_w: int, frame_h: int,
          start_input: int = 1) -> Tuple[List[str], str]:
    """ffmpeg input flags and the filter steps that draw `items` on a full-frame picture.

    Returns `(inputs, steps)` where `inputs` are the `-i` halves (each picture is one input) and `steps` is a filter
    fragment that consumes `[v0]` and produces `[vout]`. The caller appends the inputs after its own and joins the
    steps into its filter graph.

    Scale-then-rotate: rotating a 2000 px logo wastes memory for a 1080 px frame, so the picture is scaled to its
    final width first. `rotate` with `ow=rotw()/oh=roth()` keeps the corners instead of cutting them off, which is
    what a person expects of a tilted sticker.
    """
    inputs: List[str] = []
    steps: List[str] = []
    if not items:
        return inputs, ""
    # each picture is copied into the work folder under a plain name: the shelf name is already safe, but the work
    # folder is short and ffmpeg cannot open a Windows path over 260 characters
    feed = start_input
    last = "v0"
    for i, it in enumerate(items):
        src = path_for(it["name"])
        if not src:
            continue
        local = work / f"ov{i}{src.suffix.lower()}"
        try:
            shutil.copyfile(src, local)
        except OSError:
            continue
        inputs += ["-i", local.name]
        width = max(8, int(round(it["w"] * frame_w)))
        alpha = it["alpha"]
        rot = it["rot"]
        # place by centre: overlay wants the top-left corner
        x = int(round(it["x"] * frame_w))
        y = int(round(it["y"] * frame_h))
        tag = f"ov{i}"
        parts = [f"[{feed}:v]scale={width}:-1"]
        if rot:
            parts.append(f"rotate={rot}*PI/180:ow=rotw({rot}*PI/180):oh=roth({rot}*PI/180):c=none")
        if alpha < 1.0:
            parts.append(f"format=rgba,colorchannelmixer=aa={alpha:.2f}")
        else:
            parts.append("format=rgba")
        parts.append(f"setsar=1[{tag}p]")
        steps.append(",".join(parts))
        # `overlay` takes the top-left corner; the offsets below centre the picture on (x, y)
        px = f"({x}-w/2)"
        py = f"({y}-h/2)"
        # No `shortest=1` here. A still picture is one frame long, so `shortest` would end the whole video at that
        # frame: a rendered clip came out 7 seconds long with a single frame in it. Overlay's own `eof_action`
        # repeats the picture's last frame to the end of the clip, which is exactly what a logo wants.
        steps.append(f"[{last}][{tag}p]overlay=x={px}:y={py}:eof_action=repeat[{tag}]")
        last = tag
        feed += 1
    if last == "v0":
        return inputs, ""
    steps.append(f"[{last}]null[vout]")
    return inputs, ";".join(steps)


def describe(items: List[dict]) -> str:
    """One line a page can print, in the order the pictures are drawn."""
    if not items:
        return "no pictures"
    bits = []
    for it in items:
        bits.append(f"{it['name']} at {int(round(it['x'] * 100))}% across, {int(round(it['y'] * 100))}% down, "
                    f"{int(round(it['w'] * 100))}% wide" + (f", tilted {it['rot']:.0f} degrees" if it["rot"] else ""))
    return "; ".join(bits)
