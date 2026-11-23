"""What a clip is made of, for the sound picker: its words on the clip's own clock, its pauses, how loud it is.

Everything here is measured, not guessed, and none of it needs the AI:

    words      the clip's words with times from the start of the clip file (the transcript is on the stream's
               clock; the clip file starts at the clip's start)
    lines      the words grouped at the pauses, each with how long the quiet after it lasts, so a sound can be
               put IN a pause instead of over a word
    loudness   the clip file's own sound, every tenth of a second, and the level of the streamer's voice, so a
               scream is marked and a meme sound is set to sit at the voice's level, not over or under it
    frames     a few pictures from the clip file at chosen seconds, for an AI that can look

`lines_text()` is the transcript as the reader and the pickers see it: numbered lines, each with its seconds,
(LOUD) where the voice was far above its usual level, and the quiet that follows.
"""
from __future__ import annotations

import io
import json
import math
import subprocess
from pathlib import Path
from typing import List, Optional, Sequence

from . import media

LINE_GAP = 0.45          # a pause this long ends a line
LINE_MOST = 12           # and a line never runs past this many words
LINE_SOFT = 6            # past this many, a sentence ending ends the line too
LOUD_DB = 6.0            # this far above the voice's usual level is a shout


def clip_words(words: Sequence[dict], start: float, end: float) -> List[dict]:
    """The words inside the clip, on the clip's own clock (0 is the first frame of the clip file)."""
    out: List[dict] = []
    for w in words or []:
        if not isinstance(w, dict):
            continue
        try:
            s, e = float(w.get("s")), float(w.get("e"))
        except (TypeError, ValueError):
            continue
        text = str(w.get("w") or "").strip()
        if not text or e < start or s > end:
            continue
        out.append({"w": text, "s": round(max(0.0, s - start), 2), "e": round(max(0.0, min(e, end) - start), 2)})
    out.sort(key=lambda w: w["s"])
    return out


def lines_of(words: Sequence[dict], span: float) -> List[dict]:
    """Words grouped into lines at the pauses: [{"n", "s", "e", "text", "words", "quiet_after"}]."""
    lines: List[dict] = []
    cur: List[dict] = []

    def flush(next_start: Optional[float]):
        if not cur:
            return
        s, e = cur[0]["s"], cur[-1]["e"]
        after = (next_start if next_start is not None else span) - e
        lines.append({"n": len(lines) + 1, "s": s, "e": e, "text": " ".join(w["w"] for w in cur),
                      "words": list(cur), "quiet_after": round(max(0.0, after), 2)})

    for i, w in enumerate(words):
        ends = cur and cur[-1]["w"][-1:] in ".?!"
        if cur and (w["s"] - cur[-1]["e"] >= LINE_GAP or len(cur) >= LINE_MOST or (ends and len(cur) >= LINE_SOFT)):
            flush(w["s"])
            cur = []
        cur.append(w)
    flush(None)
    return lines


def loudness(path, step: float = 0.1) -> List[float]:
    """The clip file's sound level in dB, one value per `step` seconds. Empty when it cannot be read."""
    try:
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "s16le", "-"], capture_output=True, timeout=120, creationflags=media.NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired):
        return []
    import numpy as np
    x = np.frombuffer(p.stdout or b"", "<i2").astype(float)
    w = max(1, int(16000 * step))
    n = len(x) // w
    if n < 2:
        return []
    r = np.sqrt((x[: n * w].reshape(n, w) ** 2).mean(1)) + 1e-3
    return [round(20 * math.log10(v / 32768.0), 1) for v in r]


def voice_level(levels: Sequence[float], words: Sequence[dict], step: float = 0.1) -> Optional[float]:
    """The streamer's usual level while talking: the middle of the levels heard during words."""
    vals = []
    for w in words:
        a, b = int(w["s"] / step), int(math.ceil(w["e"] / step))
        vals += [levels[i] for i in range(max(0, a), min(len(levels), b))]
    if not vals:
        vals = [v for v in levels if v > -60]
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


def mark_loud(lines: List[dict], levels: Sequence[float], voice: Optional[float], step: float = 0.1) -> None:
    """Mark the lines said far above the voice's usual level (a shout, a scream, a laugh)."""
    if voice is None or not levels:
        return
    for l in lines:
        a, b = int(l["s"] / step), int(math.ceil(l["e"] / step)) + 1
        seg = [levels[i] for i in range(max(0, a), min(len(levels), b))]
        l["loud"] = bool(seg) and max(seg) >= voice + LOUD_DB


def level_row(levels: Sequence[float], voice: Optional[float], span: float, every: float = 1.0,
              step: float = 0.1) -> str:
    """The loudness through the clip as one short row: one number per second, 0 is the voice's usual level."""
    if not levels or voice is None:
        return ""
    out = []
    k = max(1, int(every / step))
    for i in range(0, min(len(levels), int(span / step) + 1), k):
        out.append(f"{max(levels[i:i + k]) - voice:+.0f}")
    return " ".join(out)


def lines_text(lines: Sequence[dict]) -> str:
    """The transcript as the sound team reads it: one numbered line per phrase, with its seconds, (LOUD), and
    how long it stays quiet afterwards."""
    if not lines:
        return "(nobody says anything in this clip)"
    rows = []
    for l in lines:
        quiet = f"   ...then {l['quiet_after']:.1f}s quiet" if l["quiet_after"] >= 0.4 else ""
        rows.append(f"L{l['n']} [{l['s']:.2f}-{l['e']:.2f}] {'(LOUD) ' if l.get('loud') else ''}"
                    f"{_safe(l['text'], 300)}{quiet}")
    return "\n".join(rows)


def _safe(v, limit=200) -> str:
    """Text from the video on its way into a prompt: one line, and unable to close our tags."""
    return " ".join(str(v or "").split()).replace("<", "‹")[:limit]


def word_at(lines: Sequence[dict], line_no, word: str = "", when: str = "after") -> Optional[dict]:
    """The word a beat points at: line `line_no`, the named word in it (the last one with that spelling for
    "after", the first for "on"), or the line's last word for "after" and first for "on" when it is not named."""
    try:
        n = int(str(line_no).strip().lstrip("Ll"))
    except (TypeError, ValueError):
        return None
    line = next((l for l in lines if l["n"] == n), None)
    if not line:
        return None
    ws = line["words"]
    want = "".join(ch for ch in str(word or "").lower() if ch.isalnum())
    if want:
        hits = [w for w in ws if "".join(ch for ch in w["w"].lower() if ch.isalnum()) == want]
        if not hits:
            hits = [w for w in ws if want in "".join(ch for ch in w["w"].lower() if ch.isalnum())]
        if hits:
            return hits[0] if when == "on" else hits[-1]
    return ws[0] if when == "on" else ws[-1]


def next_word_after(words: Sequence[dict], t: float) -> Optional[dict]:
    """The first word that starts after second `t`."""
    later = [w for w in words if w["s"] > t + 0.01]
    return min(later, key=lambda w: w["s"]) if later else None


def talking_between(words: Sequence[dict], a: float, b: float) -> float:
    """How many seconds of talking fall between `a` and `b`."""
    return round(sum(max(0.0, min(b, w["e"]) - max(a, w["s"])) for w in words), 2)


# ---------------------------------------------------------------- pictures
def frame(path, sec: float, width: int = 480) -> bytes:
    """One JPEG of the clip at `sec` seconds, or b"". An mp4 is jumped into, which lands on the exact frame."""
    try:
        p = str(Path(path).resolve())
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, float(sec)):.2f}", "-i", p, "-frames:v", "1",
               "-vf", f"scale={width}:-2", "-q:v", "4", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"]
        out = subprocess.run(cmd, capture_output=True, timeout=30, creationflags=media.NO_WINDOW)
        return out.stdout if out.stdout[:2] == b"\xff\xd8" else b""
    except Exception:  # noqa: BLE001 - no frame is simply no picture
        return b""


def sheet(shots) -> bytes:
    """Frames side by side, two to a row, each marked with its second: one picture for one question."""
    from PIL import Image, ImageDraw
    ims = []
    for t, jpg in shots:
        try:
            im = Image.open(io.BytesIO(jpg)).convert("RGB")
            im.thumbnail((420, 420))
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 96, 24], fill=(0, 0, 0))
            d.text((6, 6), f"{t:.1f}s", fill=(255, 255, 255))
            ims.append(im)
        except Exception:  # noqa: BLE001
            continue
    if not ims:
        return b""
    w, h = max(i.width for i in ims), max(i.height for i in ims)
    cols = 2 if len(ims) > 1 else 1
    rows = (len(ims) + cols - 1) // cols
    out = Image.new("RGB", (w * cols, h * rows), "black")
    for k, im in enumerate(ims):
        out.paste(im, ((k % cols) * w, (k // cols) * h))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def words_for(job: dict, clip: dict) -> List[dict]:
    """The transcript a clip was made from: its own corrected words, the job's, or the live recording's file."""
    got = clip.get("fixed_words") or job.get("words")
    if not got:
        try:
            got = json.loads((Path(job["dir"]) / "words.json").read_text(encoding="utf-8"))
        except (KeyError, OSError, ValueError, TypeError):
            got = []
    words = [dict(w) for w in got if isinstance(w, dict)]
    try:
        # Clips made before the "chad" fix still carry the engine's mishearing; the team reads it put right.
        from . import transcribe
        transcribe.fix_words(words)
    except Exception:  # noqa: BLE001 - the words as heard are still usable
        pass
    return words
