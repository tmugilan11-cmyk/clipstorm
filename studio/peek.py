"""Frames of a pick before it is rendered: four moments of one clip stitched into one strip."""
from __future__ import annotations

import shutil
import tempfile
import time
import uuid
from pathlib import Path

from . import config, media, safe

# Read through frame_count()/frame_height(), so an operator can change them without a restart.
FRAMES = 4              # samples per clip
FRAME_H = 240           # px tall: what a preview needs, and no more
INSET = 1.0             # seconds trimmed off each end, where a cut's fade is not picture yet
SEEK_TIMEOUT = 60       # seconds, one frame
STACK_TIMEOUT = 120     # seconds, the hstack that joins them
DL_TIMEOUT = 90         # seconds per download attempt; media.download_section takes no timeout, kept for parity
DL_TRIES = 2


def _env_int(name: str, default: int, low: int) -> int:
    """An operator override, or the default when it is missing or is not a number."""
    try:
        return max(low, int(config.env(name, str(default)) or default))
    except (TypeError, ValueError):
        return default


def frame_count() -> int:
    """How many frames one strip holds: PEAKCUT_PEEK_FRAMES, else FRAMES. Read per call, never cached."""
    return _env_int("PEAKCUT_PEEK_FRAMES", FRAMES, 2)


def frame_height() -> int:
    """How tall each frame is: PEAKCUT_PEEK_HEIGHT, else FRAME_H."""
    return _env_int("PEAKCUT_PEEK_HEIGHT", FRAME_H, 120)


def times(start: float, end: float, n: int = 4) -> list[float]:
    """Where to look inside [start, end]: one second in, then even thirds, one second from the end.

    Always inside the window and always ascending: the cut snaps to sentences, and a frame from
    outside the window would be a lie about what the clip shows. A short window (a 3 s clip) gives
    fewer, deduplicated times rather than the same moment twice."""
    count = max(2, int(n or frame_count()))
    a, b = float(start), float(end)
    if b <= a:
        return [a]
    span = b - a
    if span <= 2 * INSET:                                    # no room for the insets: spread evenly instead
        pts = [a + span * (k + 1) / (count + 1) for k in range(count)]
    elif count == 4:
        pts = [a + INSET, a + span / 3, a + span * 2 / 3, b - INSET]
    else:                                                    # operator overrode the count: same insets, even steps
        lo, hi2 = a + INSET, b - INSET
        pts = [lo + (hi2 - lo) * k / (count - 1) for k in range(count)]
    hi = max(a, b - 0.05)                                    # never seek onto the very last frame
    out = sorted({round(min(max(t, a), hi), 3) for t in pts})
    return out or [a]


def frames(src: Path, start: float, end: float, out_dir: Path,
           off: float = 0.0, height: int = 0, n: int = 0) -> list[Path]:
    """Up to N frames of [start, end] out of `src`, as small JPEGs in `out_dir`.

    `off` is the video-time of the file's second zero: a downloaded slice starts at the clip's own
    start, so every sample time is shifted down by it. A frame ffmpeg will not produce is skipped,
    never raised - a missing frame is not a missing preview."""
    h = int(height or frame_height())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    got = []
    for i, t in enumerate(times(start, end, n or frame_count())):
        f = out_dir / f"f{i}.jpg"
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-ss", f"{max(t - off, 0.0):.2f}", "-i", str(src),    # -ss before -i: seek, do not decode
               "-frames:v", "1", "-vf", f"scale=-2:{h}", str(f)]     # -2: even width, or hstack refuses it
        try:
            media.run(cmd, timeout=SEEK_TIMEOUT)
        except Exception:  # noqa: BLE001 - one bad seek is not a failed peek
            continue
        if f.exists() and f.stat().st_size > 0:
            got.append(f)
    return got


def stack(jpgs: list[Path], out: Path) -> Path:
    """Left-to-right strip of the frames. One frame passes through as-is, because hstack needs two."""
    if not jpgs:
        raise RuntimeError("no frames")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for f in jpgs:
        cmd += ["-i", str(f)]
    cmd += ["-filter_complex", f"hstack=inputs={len(jpgs)}" if len(jpgs) > 1 else "null", str(out)]
    media.run(cmd, timeout=STACK_TIMEOUT)
    return out


class _Scratch:
    """A throwaway folder that is path-like and deletes itself best-effort, like tempfile.TemporaryDirectory.

    Made with `mkdir` rather than `tempfile.mkdtemp` on purpose. On Windows a mkdtemp folder carries an ACL that
    grants only the account that made it, and ffmpeg — a separate process, and on some hosts a differently
    sandboxed one — cannot write its frames into it. The frames then fail one by one, `frames()` skips each as it
    is written to do, and the peek comes back empty with no error to point at. A plain folder has no such ACL."""

    def __init__(self, parent: Path):
        stamp = "%d-%s" % (time.time() * 1000, uuid.uuid4().hex[:8])
        self.name = str(Path(parent) / ("pkpeek" + stamp.replace(".", "")))
        Path(self.name).mkdir(parents=True, exist_ok=False)

    def __fspath__(self):
        return self.name

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.cleanup()

    def cleanup(self):
        shutil.rmtree(self.name, ignore_errors=True)


def _tempdir():
    """A scratch folder for the still frames. The system temp folder is tried first because short paths are what
    ffmpeg wants; a machine where nothing may write there gets PeakCut's own `tmp` folder instead."""
    for parent in (Path(tempfile.gettempdir()), config.TMP_DIR / "peek"):
        try:
            got = _Scratch(parent)
            probe = Path(got.name) / ".w"
            probe.write_bytes(b"1")
            probe.unlink()
            return got
        except OSError:
            try:
                got.cleanup()
            except (NameError, OSError):
                pass
    raise RuntimeError("No folder PeakCut can write scratch files into.")


def strip(src: Path, start: float, end: float, out: Path, off: float = 0.0) -> Path:
    """The whole feature: the frames of one window, stacked into one JPEG at `out`."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with _tempdir() as tmp:
        return stack(frames(Path(src), start, end, Path(tmp), off), out)


def source(job: dict, clip: dict, work: Path) -> tuple[Path, float]:
    """The video to sample from, and the video-time of its second zero.

    The clip's own piece first (free), then the job's uploaded file, then a throwaway 240p slice."""
    p = clip.get("src")
    if p:
        return Path(p), float(clip.get("src_offset") or 0.0)
    sp = job.get("source_path")
    if sp:
        return Path(sp), 0.0
    url = (job.get("source") or {}).get("url") or ""
    if url and media.site_allowed(url):                      # the server fetches this: known sites only
        work = Path(work)
        work.mkdir(parents=True, exist_ok=True)
        for attempt in range(DL_TRIES):
            try:
                piece = media.download_section(url, work, "peek", float(clip["start"]), float(clip["end"]),
                                               height=frame_height(), exact=True)
                return piece, float(clip["start"])           # the slice's own second zero is the clip's start
            except media.YouTubeBlocked:
                raise                                        # a refusal: retrying is what causes it
            except Exception:  # noqa: BLE001 - second try, then give up
                if attempt == DL_TRIES - 1:
                    raise
        raise RuntimeError("no piece")
    raise RuntimeError("There is no video to take frames from yet.")


def make(job: dict, clip: dict) -> dict:
    """Frames for one clip, written beside its siblings. Returns the clip keys to set.

    Raises on failure; the caller decides whether that is fatal (it never is)."""
    d = Path(job["dir"]) / "clips"
    name = f'{clip["id"]}_peek.jpg'
    start, end = float(clip["start"]), float(clip["end"])
    with _tempdir() as tmp:
        src, off = source(job, clip, Path(tmp))
        strip(src, start, end, d / name, off)
    return {"peek": name,
            "peek_at": [round(t, 2) for t in times(start, end, frame_count())],
            "peek_version": int(clip.get("peek_version") or 0) + 1}


def strip_bytes(job: dict, clip: dict) -> bytes:
    """The strip as JPEG bytes, for showing to a model. b"" when there is none."""
    name = clip.get("peek")
    if not name:
        return b""
    p = Path(job["dir"]) / "clips" / Path(str(name)).name     # bare filename only: never a path from job JSON
    try:
        return p.read_bytes() if p.is_file() else b""
    except OSError:
        return b""


def _stem(raw) -> str:
    """A clip id made safe for a filename: names arrive from job JSON, not from us."""
    s = "".join(c if (c.isalnum() or c in "_-") else "_" for c in str(raw or "").strip())
    return s[:60] or "peek"


def grab(src: Path, moments: list[dict], out_dir: Path) -> dict:
    """Strips for many moments of one local video, each written to `out_dir` as `<id>_peek.jpg`.

    The batch driver: it never raises, and one bad moment never stops the rest. It reads a file that
    is already on disk, so it takes nothing from the network and does no rendering."""
    src, out_dir = Path(src), Path(out_dir)
    report = {"src": str(src), "count": 0, "made": 0, "frames": frame_count(),
              "files": [], "at": {}, "failed": []}
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        report["failed"].append({"id": "", "error": safe.friendly(e, 200)})
        return report
    for pos, m in enumerate(moments or [], 1):
        report["count"] += 1
        if not isinstance(m, dict):
            report["failed"].append({"id": f"peek{pos}", "error": "A moment must be a dict of start and end."})
            continue
        cid = _stem(m.get("id") or m.get("name") or f"peek{pos}")
        try:
            start, end = float(m["start"]), float(m["end"])
            name = f"{cid}_peek.jpg"
            strip(src, start, end, out_dir / name, float(m.get("off") or 0.0))
            report["made"] += 1
            report["files"].append(name)
            report["at"][name] = [round(t, 2) for t in times(start, end, report["frames"])]
        except Exception as e:  # noqa: BLE001 - a preview is never worth failing a run over
            report["failed"].append({"id": cid, "error": safe.friendly(e, 200)})
    return report
