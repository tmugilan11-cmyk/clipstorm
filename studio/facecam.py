"""Where the facecam is.

A gaming stream is a game with a small webcam picture in one corner of it. The
short that comes out of it is better when the game fills the screen and the
webcam sits in the corner of it, instead of the whole 16:9 frame squeezed into
a band with blurred fill above and below.

The webcam is found by the one thing a webcam always has and a game almost never
has: a straight border that stays in the same place in every frame. A wall in
the game moves, a HUD bar changes, but the edge of the webcam box does not move
at all. A second thing tells the webcam apart from the game's own panels, which
have straight borders too: the picture inside a webcam is almost still, while
the game behind a panel keeps moving.

Metric: for every column and every row, how much the picture changes at that
line, counted over frames spread through the video. A border of the webcam box
stands out from the rest.

One frame can also be shown to the AI (`detect(path, ask=...)`), which is better
than any measurement at telling a person from a game character. Its answer is
measured again on the picture before it is used, so being wrong costs a search,
not a clip.

Only numpy and ffmpeg, which are already here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

W, H = 320, 180            # the picture is looked at small: only the lines matter
MAX_FRAMES = 24            # frames spread through the video
MIN_SIZE = 0.12            # the smallest a webcam may be, as a part of the width or height
MAX_SIZE = 0.60            # and the largest
ASPECT_MIN = 0.55          # the narrowest: a phone held upright is about 0.56
ASPECT_MAX = 3.20          # the widest: a banner or a ticker is wider than this
STILL_FRAC = 0.35          # how much of the game's own movement a webcam picture may have
STILL_MIN = 6.0            # and the floor, for a game that itself is almost still
STILL_SHARE = 0.30         # at most this much of a webcam picture may be moving, or the game is showing through
EDGE_FLUSH = 0.02          # a side this close to the frame's own edge is the edge
MATCH = 0.35               # how much a box the AI points at must cover a measured box to be that box
EDGE = 2.2                 # how much brighter than the average line a border must be
MIN_COV = 0.08             # the least of a whole column or row that must be still for a webcam to be on it
IN_COV = 0.30              # and the least of a line inside the box itself
GAP = 0.08                 # a moving stretch this short inside a webcam is the person, not the end of the box
CALM_OUT = 0.15            # at most this much of the picture outside the box may be still, or there is no game round it
DRIFT_SHARE = 0.50         # a person in front of a webcam moves: up to half the box may, when it is found by stillness


def _frames(path: str | Path, count: int = MAX_FRAMES) -> np.ndarray:
    """The video as a few grey frames, spread through it."""
    try:
        dur = _duration(path)
        rate = max(count / dur, 0.02) if dur > 0 else 0.2
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path),
             "-vf", f"fps={rate:.4f},scale={W}:{H},format=gray",
             "-frames:v", str(count), "-f", "rawvideo", "-"],
            capture_output=True, timeout=180)
    except Exception:  # noqa: BLE001 - no ffmpeg or an unreadable file: no facecam, not a failure
        return np.zeros((0, H, W), dtype=np.uint8)
    raw = proc.stdout or b""
    size = W * H
    n = len(raw) // size
    if n < 4:
        return np.zeros((0, H, W), dtype=np.uint8)
    return np.frombuffer(raw[:n * size], dtype=np.uint8).reshape(n, H, W)


def _duration(path: str | Path) -> float:
    try:
        proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                               "-of", "default=nw=1:nk=1", str(path)],
                              capture_output=True, text=True, timeout=60)
        return float((proc.stdout or "").strip() or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def _profiles(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(vertical lines, horizontal lines): how much changes at each column and each row.

    The median over the frames is used, so one busy moment cannot invent a line."""
    if len(frames) < 4:
        return np.zeros(W), np.zeros(H)
    f = frames.astype(np.int16)
    gx = np.median(np.abs(np.diff(f, axis=2)).sum(axis=1), axis=0)   # change across each column boundary
    gy = np.median(np.abs(np.diff(f, axis=1)).sum(axis=2), axis=0)   # change across each row boundary
    return gx, gy


def _peaks(profile: np.ndarray, limit: int) -> list[tuple[int, float]]:
    """The lines that stand out: (where, how much)."""
    if len(profile) < 3:
        return []
    med = float(np.median(profile)) or 1.0
    out = []
    for i in range(1, len(profile) - 1):
        if profile[i] >= profile[i - 1] and profile[i] > profile[i + 1] and profile[i] > EDGE * med:
            out.append((i, float(profile[i] / med)))
    return sorted(out, key=lambda p: -p[1])[:limit]


def _size(path: str | Path) -> tuple[int, int]:
    proc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height", "-of", "default=nw=1", str(path)],
                          capture_output=True, text=True, timeout=60)
    w = h = 0
    for line in (proc.stdout or "").splitlines():
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        try:
            if k.strip() == "width":
                w = int(v.strip())
            elif k.strip() == "height":
                h = int(v.strip())
        except ValueError:
            continue
    return w, h


def _stillness(frames: np.ndarray) -> np.ndarray:
    """How much each pixel changes over the frames.

    A webcam picture barely changes: a person sits in a room and shifts a little. The game changes every
    frame. This is the one thing that tells a webcam apart from the game's own panels, which have straight
    borders too and are drawn over the game with the game showing through them."""
    return frames.astype(np.float32).std(axis=0)


def _plausible(x0, y0, x1, y1, still, light, game, share=STILL_SHARE):
    """Could this rectangle be a webcam picture? Judged on its shape, its stillness and its light.

    Returns how much it moves, or None. Nothing here says which corner it is in: a webcam may sit in a
    corner, along one edge, or with a margin all round."""
    bw, bh = (x1 - x0) / W, (y1 - y0) / H
    if not (MIN_SIZE <= bw <= MAX_SIZE and MIN_SIZE <= bh <= MAX_SIZE):
        return None
    # measured in pixels: a 4:3 picture is 1.33, a phone held upright is 0.56
    aspect = (bw * W) / max(1e-6, bh * H)
    if not (ASPECT_MIN <= aspect <= ASPECT_MAX):
        return None
    a, b, c, d = int(x0), int(y0), int(x1), int(y1)
    inside = still[b:d, a:c]
    if not inside.size:
        return None
    cut = max(STILL_MIN, STILL_FRAC * game)
    moving = float(np.median(inside))
    if moving > cut:
        return None                    # it changes with the game: it is the game
    if float((inside > cut).mean()) > share:
        return None                    # a good part of it moves: the game is showing through
    if float(light[b:d, a:c].mean()) < 0.30 * float(light.mean()):
        return None                    # a black hole, not a picture
    return moving


def _local(vpeaks, hpeaks, still, light):
    """Every rectangle the strong straight lines can make, that still looks like a camera.

    Returns them best first: the one whose weakest border is the strongest, and of those the bigger."""
    game = float(np.median(still))
    xs = sorted({0.0, float(W)} | {float(x) for x, _ in vpeaks[:10]})
    ys = sorted({0.0, float(H)} | {float(y) for y, _ in hpeaks[:10]})
    vs = {float(x): s for x, s in vpeaks}
    hs = {float(y): s for y, s in hpeaks}
    out = []
    for i, x0 in enumerate(xs):
        wx = [vs[v] for v in (x0,) if v in vs]
        for x1 in xs[i + 1:]:
            wscore = wx + [vs[v] for v in (x1,) if v in vs]
            for j, y0 in enumerate(ys):
                hy0 = [hs[v] for v in (y0,) if v in hs]
                for y1 in ys[j + 1:]:
                    score = wscore + hy0 + [hs[v] for v in (y1,) if v in hs]
                    if len(score) < 2:
                        continue       # a box needs two borders of its own, or it is just the frame
                    moving = _plausible(x0, y0, x1, y1, still, light, game)
                    if moving is None:
                        continue
                    key = (min(score), (x1 - x0) * (y1 - y0))
                    out.append({"key": key, "x": x0, "y": y0, "x1": x1, "y1": y1,
                                "score": round(min(score), 2), "moving": moving})
    return sorted(out, key=lambda c: c["key"], reverse=True)


def _runs(profile: np.ndarray, floor: float, gap: int) -> list[tuple[int, int]]:
    """Stretches of a profile that stay at or above `floor`, as (first, one past last).

    A dip shorter than `gap` does not end a stretch: a person moving in the middle of a webcam picture
    makes exactly such a dip, with the still room on either side of them."""
    out, start, last = [], None, None
    for i, v in enumerate(profile):
        if v >= floor:
            if start is None:
                start = i
            elif i - last - 1 > gap:
                out.append((start, last + 1))
                start = i
            last = i
    if start is not None:
        out.append((start, last + 1))
    return out


def _drift(still: np.ndarray, light: np.ndarray) -> list[dict]:
    """Webcam boxes found by stillness alone, for a stream whose webcam has no border the lines can find.

    A webcam drawn straight onto the game, with no frame round it, gives the line search nothing to hold.
    But it is still an island of calm against one side of a picture that never stops moving. So, from each
    side of the frame in turn: walk inwards for as long as the columns stay still (that is how wide the box
    is), then look only inside that strip for the rows that are still (a webcam a fifth of the frame wide
    is lost in a profile of the whole width), then measure the width again inside those rows, and once
    more. What is left is checked like any other box. Best first."""
    h, w = still.shape
    game = float(np.median(still))
    cut = max(STILL_MIN, STILL_FRAC * game)
    found = {}
    for side in ("left", "right", "top", "bottom"):
        # turn the picture so the side being tried is always column 0
        m = still <= cut
        if side == "right":
            m = m[:, ::-1]
        elif side == "top":
            m = m.T
        elif side == "bottom":
            m = m.T[:, ::-1]
        mh, mw = m.shape
        gap_c, gap_r = max(1, int(GAP * mw)), max(1, int(GAP * mh))
        lo_c, hi_c = MIN_SIZE * mw, MAX_SIZE * mw
        lo_r, hi_r = MIN_SIZE * mh, MAX_SIZE * mh

        def depth(cols, least):
            """How far in from the side the still columns reach, or 0."""
            near = cols[: max(1, int(lo_c))]
            floor = max(least, 0.5 * float(near.max()))
            runs = [r for r in _runs(cols, floor, gap_c) if r[0] <= 1]
            return runs[0][1] if runs else 0

        def band(rows, least):
            """The still rows, as (first, one past last): the stretch with the most stillness in it."""
            if not len(rows):
                return None
            floor = max(least, 0.5 * float(rows.max()))
            runs = [r for r in _runs(rows, floor, gap_r) if lo_r <= r[1] - r[0] <= hi_r]
            return max(runs, key=lambda r: float(rows[r[0]:r[1]].sum())) if runs else None

        x1 = depth(m.mean(axis=0), MIN_COV)
        if not (lo_c <= x1 <= hi_c):
            continue
        rows = None
        for _ in range(3):
            rows = band(m[:, :x1].mean(axis=1), IN_COV)
            if rows is None:
                break
            again = depth(m[rows[0]:rows[1], :].mean(axis=0), IN_COV)
            if not (lo_c <= again <= hi_c):
                rows = None
                break
            if again == x1:
                break
            x1 = again
        if rows is None:
            continue
        y0, y1 = rows
        cover = float(m[y0:y1, :x1].mean())
        if cover < 0.5:
            continue
        # An island of calm needs a sea round it. When a good part of the rest of the picture is still as
        # well, this is not a webcam on a game: it is a camera filling the frame, or a menu, or a pause.
        rest = m.size - (y1 - y0) * x1
        if rest <= 0 or (float(m.sum()) - float(m[y0:y1, :x1].sum())) / rest > CALM_OUT:
            continue
        # back onto the picture the right way round
        if side == "left":
            box = (0, y0, x1, y1)
        elif side == "right":
            box = (w - x1, y0, w, y1)
        elif side == "top":
            box = (y0, 0, y1, x1)
        else:
            box = (y0, h - x1, y1, h)
        moving = _plausible(*box, still, light, game, share=DRIFT_SHARE)
        if moving is None:
            continue
        area = (box[2] - box[0]) * (box[3] - box[1])
        cand = {"key": (cover * area, area), "x": float(box[0]), "y": float(box[1]), "x1": float(box[2]),
                "y1": float(box[3]), "score": round(cover, 2), "moving": moving}
        old = found.get(box)
        if old is None or cand["key"] > old["key"]:
            found[box] = cand
    return sorted(found.values(), key=lambda c: c["key"], reverse=True)


def _inside(a: dict, b: dict) -> float:
    """How much of box `a` lies inside box `b`, 0 to 1."""
    ix = max(0.0, min(a["x1"], b["x1"]) - max(a["x"], b["x"]))
    iy = max(0.0, min(a["y1"], b["y1"]) - max(a["y"], b["y"]))
    area = (a["x1"] - a["x"]) * (a["y1"] - a["y"])
    return ix * iy / area if area > 0 else 0.0


def _overlap(a, box) -> float:
    """How much two boxes cover the same ground: 1 when they are the same, 0 when they do not touch."""
    ax0, ay0, ax1, ay1 = a["x"], a["y"], a["x1"], a["y1"]
    bx, by, bw, bh = box
    bx0, by0, bx1, by1 = bx * W, by * H, (bx + bw) * W, (by + bh) * H
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    inter = ix * iy
    union = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / union if union > 0 else 0.0


def _full_frame(path: str | Path) -> np.ndarray | None:
    """One grey frame at full size, from the middle of the video: where the borders are measured."""
    w, h = _size(path)
    if not w or not h:
        return None
    try:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, _duration(path) / 2.0):.1f}", "-i", str(path),
             "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True, timeout=120).stdout or b""
    except Exception:  # noqa: BLE001
        return None
    if len(raw) < w * h:
        return None
    return np.frombuffer(raw[:w * h], dtype=np.uint8).reshape(h, w).astype(np.float32)


def _best(profile: np.ndarray, approx: float, span: float) -> float:
    """The strongest change near a guessed line."""
    lo, hi = max(0, int(approx - span)), min(len(profile), int(approx + span) + 1)
    seg = profile[lo:hi]
    return float(lo + seg.argmax()) if len(seg) else float(approx)


def _snap(path: str | Path, box, w: int, h: int, span: float = 0.0):
    """A box on the small grid, put onto the borders that are really in the picture.

    A border the small grid found is a pixel or two out; a box a model proposed can be a good part of the
    frame out, which is what `span` is for. A side within a hair of the frame's own edge is the edge."""
    frame = _full_frame(path)
    if frame is None:
        return None
    fh, fw = frame.shape
    col = np.abs(np.diff(frame, axis=1)).sum(axis=0)
    row = np.abs(np.diff(frame, axis=0)).sum(axis=1)
    # The small grid is a quarter of the picture, so a border found on it is a few pixels out; one the
    # model proposed can be a good part of the frame out, which is what `span` is for.
    spread = max(4.0, span * max(fw, fh), 1.5 * max(fw / W, fh / H))

    def line(profile, approx, edge, extent):
        if abs(approx - edge) <= EDGE_FLUSH * extent:
            return float(edge)
        return _best(profile, approx, spread)

    x0, y0, x1, y1 = box
    return (line(col, x0 * fw / W, 0, fw), line(row, y0 * fh / H, 0, fh),
            line(col, x1 * fw / W, fw, fw), line(row, y1 * fh / H, fh, fh))


def _corner(x0, y0, x1, y1, w, h) -> str:
    """What part of the frame the box is on: its corner, its edge, or the middle."""
    near = EDGE_FLUSH
    left, right = x0 <= w * near, x1 >= w * (1 - near)
    top, bottom = y0 <= h * near, y1 >= h * (1 - near)
    if left and top:
        return "top-left"
    if right and top:
        return "top-right"
    if left and bottom:
        return "bottom-left"
    if right and bottom:
        return "bottom-right"
    if left or right:
        return "right" if right else "left"
    if top or bottom:
        return "bottom" if bottom else "top"
    return "middle"


def _finish(path: str | Path, found: dict, w: int, h: int, still: np.ndarray) -> dict | None:
    """The box in source pixels, with how sure it is that this is really a camera."""
    snapped = _snap(path, (found["x"], found["y"], found["x1"], found["y1"]), w, h)
    if not snapped:
        return None
    x0, y0, x1, y1 = snapped
    if x1 - x0 < w * MIN_SIZE or y1 - y0 < h * MIN_SIZE:
        return None
    inside = still[int(found["y"]):int(found["y1"]), int(found["x"]):int(found["x1"])]
    game = float(np.median(still))
    moving = float(np.median(inside)) if inside.size else 99.0
    # sure of it when the picture inside hardly moves while the game around it is racing
    conf = "high" if moving <= max(3.0, 0.25 * game) else "low"
    return {"x": int(round(x0)), "y": int(round(y0)), "w": int(round(x1 - x0)), "h": int(round(y1 - y0)),
            "corner": _corner(x0, y0, x1, y1, w, h), "score": found.get("score", 0.0), "conf": conf}


def _frame_jpeg(path: str | Path, width: int = 768) -> bytes:
    """One frame of the stream, small, as a JPEG: what a model is shown."""
    try:
        return subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, _duration(path) / 2.0):.1f}", "-i", str(path),
             "-frames:v", "1", "-vf", f"scale={width}:-2", "-pix_fmt", "yuvj420p", "-q:v", "4",
             "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
            capture_output=True, timeout=120).stdout or b""
    except Exception:  # noqa: BLE001
        return b""


def _asked(path: str | Path, ask):
    """One frame to the model: (did it look, its box as parts of the frame or None)."""
    jpeg = _frame_jpeg(path)
    if not jpeg:
        return False, None
    try:
        answer = ask(jpeg) or {}
    except Exception:  # noqa: BLE001 - a model that cannot look is not a failure
        return False, None
    return bool(answer.get("looked")), answer.get("box")


def _seen(path: str | Path, box, w: int, h: int, still: np.ndarray, light: np.ndarray) -> dict | None:
    """A box the model proposed, put onto the picture's real borders and checked like any other.

    A model reads a picture well but places a box roughly, and it can be wrong about the whole thing. So
    its box is only believed where the borders are really there and the picture inside really is still."""
    fx, fy, fw, fh = box
    snapped = _snap(path, (fx * W, fy * H, (fx + fw) * W, (fy + fh) * H), w, h, span=0.12)
    if not snapped:
        return None
    x0, y0, x1, y1 = snapped
    if x1 - x0 < w * MIN_SIZE or y1 - y0 < h * MIN_SIZE:
        return None
    small = (x0 * W / w, y0 * H / h, x1 * W / w, y1 * H / h)
    # The model has already said a person is here, so the picture inside is allowed to move more than a
    # measured box would be; what it may not be is the game itself.
    if _plausible(*small, still, light, float(np.median(still)), share=1.0) is None:
        return None
    found = {"x": small[0], "y": small[1], "x1": small[2], "y1": small[3], "score": 0.0}
    return _finish(path, found, w, h, still)


def detect(path: str | Path, ask=None) -> dict | None:
    """The facecam's box in the source, in source pixels, or None.

    The box is given as x, y, width, height, with the confidence in "score" and
    how sure we are that it is a camera in "conf".

    `ask` is shown one frame of the stream and says where the webcam is (brain.look_for_facecam). Its
    answer is measured again on the picture before it is believed, so a model that is wrong costs the
    search an idea, not a broken clip. Without `ask` nothing outside the file is looked at, which is how
    the tests run and how a job with no AI set still works."""
    frames = _frames(path)
    if len(frames) < 4:
        return None
    w, h = _size(path)
    if not w or not h:
        return None
    still = _stillness(frames)
    light = frames.astype(np.float32).mean(axis=0)
    looked, hinted = (False, None)
    if ask is not None:
        looked, hinted = _asked(path, ask)
        if looked and not hinted:
            return None                    # it looked, and there is no webcam on this stream
    vx, hy = _profiles(frames)
    vpeaks, hpeaks = _peaks(vx, 40), _peaks(hy, 40)
    found = _local(vpeaks, hpeaks, still, light) if (vpeaks and hpeaks) else []
    # A webcam with no straight border to hold on to is still an island of calm against a side of the
    # frame. When the lines found nothing that is the answer; when they found a box round the same place
    # the calm one is used, because the lines also take in whatever is drawn next to the webcam (a counter
    # under it, a name above it) and the calm does not.
    calm = _drift(still, light)
    if calm and (not found or _inside(calm[0], found[0]) >= 0.8):
        found = calm + found
    else:
        found = found + calm
    if looked and hinted:
        # The model is better than any measurement at saying "that is a person", and worse at saying
        # exactly where the lines are. So it picks which of the measured boxes it is, and only if it
        # matches none of them is its own box measured and used.
        match = max(found, key=lambda c: _overlap(c, hinted)) if found else None
        if match and _overlap(match, hinted) >= MATCH:
            return _finish(path, match, w, h, still)
        seen = _seen(path, hinted, w, h, still, light)
        if seen:
            return seen
    if not found:
        return None
    return _finish(path, found[0], w, h, still)


CENTER_MIN = 3.0        # the least average movement a webcam picture must have to say where the person is
CENTER_SPREAD = 0.85    # if the movement is spread over more than this much of the width, there is no one place


def _center_of(still: np.ndarray):
    """The horizontal centre (0..1) of the part of a webcam picture that moves, or None when it cannot be told.

    `still` is the per-pixel movement inside the box (rows x columns). The room behind a person is still and the
    person is the part that moves, so the columns are weighted by how much they move above the quietest ones."""
    if still.ndim != 2 or still.shape[1] < 4 or still.shape[0] < 2:
        return None
    col = still.mean(axis=0).astype(np.float64)
    if float(col.mean()) < CENTER_MIN and float(col.max()) < CENTER_MIN * 2:
        return None
    wgt = np.clip(col - float(np.percentile(col, 25)), 0, None)
    total = float(wgt.sum())
    if total <= 0 or float(wgt.max()) < CENTER_MIN:
        return None
    wgt = np.where(wgt >= 0.25 * float(wgt.max()), wgt, 0.0)       # ignore faint noise far from the person
    total = float(wgt.sum())
    if float((wgt > 0).mean()) > CENTER_SPREAD:
        return None
    cx = float((wgt * (np.arange(len(wgt)) + 0.5)).sum() / total / len(wgt))
    return min(0.8, max(0.2, cx))


def person_center(path, box):
    """Where the person is inside the webcam box, as a fraction 0..1 of the box's width. `box` is [x, y, w, h] in
    the source's own pixels. None when the movement is too weak or too spread out to tell."""
    try:
        x, y, w, h = (float(v) for v in box)
        sw, sh = _size(path)
        if w < 8 or h < 8 or not sw or not sh:
            return None
        frames = _frames(path)
        if len(frames) < 4:
            return None
        still = _stillness(frames)
        x0, x1 = int(round(x / sw * W)), int(round((x + w) / sw * W))
        y0, y1 = int(round(y / sh * H)), int(round((y + h) / sh * H))
        x0, y0 = max(0, x0), max(0, y0)
        return _center_of(still[y0:max(y1, y0 + 2), x0:max(x1, x0 + 4)])
    except Exception:  # noqa: BLE001 - never costs anyone a clip
        return None
