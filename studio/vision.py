"""Game events: the big centred banners a game draws when something decisive happens (WASTED, BUSTED, MISSION
PASSED ...), the wanted stars in the corner and hard scene cuts, read from the picture about once a second so the
AI is told "(GAME WASTED)" on the transcript line under the banner, with every part of it optional so a server
that has no OCR engine simply finds nothing instead of failing a job.

How it reads a video: one picture a second, the middle band of it through OCR, and what comes back is matched
against a table of banners by character similarity, so an OCR slip like BUSTEO still counts as BUSTED. Anything
big, centred and shouted that the table does not know is kept as "TEXT ..." at a lower weight, which is how a game
nobody has written a table for still produces events. Sightings of the same label inside 15 seconds are one event
with a start, an end and a hit count, so a banner held on screen for four seconds is one event, not four.

Cost: OCR is about a second a frame, so a scan is minutes rather than seconds. Two gates keep that in hand - the
picture is only read when a colour that only a banner uses is on screen, or every fourth second anyway, and never
when the middle of the frame has not moved since the last look - and `budget_s` stops the whole thing.

Nothing here needs opencv or an OCR engine to import: both are looked for the first time `available()` is called,
and `AVAILABLE` (None until then, then True or False) plus `WHY` say whether banners can be read and what is
missing when they cannot."""

from __future__ import annotations

import difflib
import json
import logging
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from . import config

log = logging.getLogger(__name__)

_FFMPEG = "ffmpeg"
_FFPROBE = "ffprobe"

# ---------------------------------------------------------------- the label table
# What a game draws when something decisive happens: the spellings it may draw, and how much one sighting counts.
# This order is load-bearing. The first label that matches wins, so VICTORY ROYALE has to be asked about before
# VICTORY, and MISSION PASSED before anything shorter that might be a prefix of it.
_BUNDLED = (
    ("WASTED", ("WASTED",), .8),
    ("BUSTED", ("BUSTED",), .7),
    ("MISSION PASSED", ("MISSION PASSED", "MISSION COMPLETE"), .7),
    ("MISSION FAILED", ("MISSION FAILED",), .7),
    ("HEIST PASSED", ("HEIST PASSED", "HEIST COMPLETE"), .8),
    ("HEIST FAILED", ("HEIST FAILED",), .7),
    ("VICTORY ROYALE", ("VICTORY ROYALE",), .8),
    ("ELIMINATED", ("ELIMINATED", "YOU ELIMINATED"), .5),
    ("GAME OVER", ("GAME OVER",), .6),
    ("YOU DIED", ("YOU DIED",), .7),
    ("VICTORY", ("VICTORY",), .6),
    ("DEFEAT", ("DEFEAT",), .5),
    ("CHAMPION", ("CHAMPION", "YOU ARE THE CHAMPION"), .6),
)
# What a wanted-star rise, a hard cut and a banner no table knows are worth. A word keeps the weight in the table.
W_STARS, W_CUT, W_TEXT = .5, .3, .35
MATCH_RATIO = .8        # how close an OCR string has to be to a phrase to be it: BUSTEO vs BUSTED is 0.83
MIN_CHARS = 4           # shorter than this after norm() is glyph noise from a HUD, not a word

# ---------------------------------------------------------------- where to look
# Fractions of the frame, so a 720p capture and a 4K one are read the same way.
OCR_Y = (.20, .80)      # the middle band: the very top and the very bottom hold the HUD, never a banner
OCR_X = (.08, .92)
STAR_Y = (.10, .24)     # the GTA-5 wanted-star strip: top right
STAR_X = .72
CORE_W = 640            # every frame is looked at 640 wide; OCR time and error both grow with pixels
# The frame is worth a second look only if one of these is on screen. Gold is mission text, red is the WASTED
# screen, and grey is the death fade: a share of the middle band for the colours, a share of the usual
# saturation of the video for the fade.
CUE_GOLD, CUE_RED, CUE_GREY = .006, .004, .6
SAT_WINDOW = 40         # seconds of saturation kept, so "greyer than usual" means usual for this video
SWEEP = 4               # and the screen is read at least every 4th second, for a banner that held perfectly still
MOVE_MIN = 6.0          # ... but only once the middle of the frame has moved this much (0-255)
CUT_DIST = .55          # hue/saturation histogram distance between two frames that reads as a hard cut
BIG_TEXT = .06          # a banner is at least this much of the frame height
CENTER = (.3, .7)       # and sits in the middle horizontally
CONF_WORD = .6          # how sure OCR must be for a known word ...
CONF_TEXT = .85         # ... and how sure it must be for a banner nobody has a name for (those are noisy)

# ---------------------------------------------------------------- the engine, once
# Both are imported on first use and never at the top: a server that has neither still boots and still clips.
_cv_mod = None
_cv_done = False
_ocr_engine = None
_ocr_lock = threading.RLock()

# None until available() has been asked once, then True or False. WHY says what is missing.
AVAILABLE = None
WHY = "not checked yet"

try:
    _SLOTS = threading.BoundedSemaphore(max(1, int(float(config.env("PEAKCUT_OCR_SLOTS", "2")))))
except (TypeError, ValueError):
    _SLOTS = threading.BoundedSemaphore(2)


def _cv():
    """opencv, or None when it is not installed. Asked once."""
    global _cv_mod, _cv_done
    if not _cv_done:
        _cv_done = True
        try:
            import cv2
            _cv_mod = cv2
        except Exception:  # noqa: BLE001 - a broken install is the same as no install
            _cv_mod = None
    return _cv_mod


def _engine():
    """The one OCR engine this process uses, built the first time it is asked for.

    Raises when the package is not installed, which is what `available()` catches and turns into a False."""
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR      # hundreds of MB with the models, so never at import
            _ocr_engine = RapidOCR()
        return _ocr_engine


def available() -> bool:
    """Can this server read a banner? True when opencv imports and the OCR engine loads, asked once and cached.

    Never raises: a missing package is a False with the reason in WHY, which is what lets the feature be simply
    absent on a server that never installed it instead of stopping a job."""
    global AVAILABLE, WHY
    if AVAILABLE is None:
        if _cv() is None:
            AVAILABLE, WHY = False, "opencv is not installed"
        else:
            try:
                _engine()
            except Exception as e:  # noqa: BLE001 - no engine is a normal state, not an error
                AVAILABLE, WHY = False, f"no OCR engine ({type(e).__name__}: {e})"
            else:
                AVAILABLE, WHY = True, ""
        if not AVAILABLE:
            log.info("vision: game events are off: %s", WHY)
    return bool(AVAILABLE)


def _ocr(img) -> list:
    """(box, text, score) for every piece of text in the picture, one frame at a time per process.

    The engine is a singleton and is not known to be thread-safe, so the call itself is serialised: several jobs
    scanning at once queue here instead of running inference on one object together."""
    engine = _engine()
    with _ocr_lock:
        got, _ = engine(img, use_cls=False)
    return got or []


# ---------------------------------------------------------------- the table in use
_table = {"at": None, "words": None, "noted": None}


def _bundled() -> dict:
    return {lab: (list(phr), w) for lab, phr, w in _BUNDLED}


def norm(s) -> str:
    """Uppercase, delete everything that is not A-Z or a space, trim. The form the OCR text is compared in."""
    return re.sub(r"[^A-Z ]", "", str(s or "").upper()).strip()


def _clean_table(data) -> Optional[dict]:
    """A hand-written table as {label: (phrases, weight)}, or None when it is not one.

    A phrase that norm() would change could never match anything, so it is left out and said so once: a badly
    hand-edited file must cost the user their extra labels, not the feature."""
    if not isinstance(data, dict):
        return None
    rows = data.get("words")
    if not isinstance(rows, list):
        return None
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        phrases = row.get("phrases")
        if not label or not isinstance(phrases, list):
            continue
        keep = []
        for p in phrases:
            p = str(p or "")
            if not p:
                continue
            if norm(p) == p:
                keep.append(p)
            else:
                log.info("vision: the phrase %r is skipped, it would change under norm()", p)
        if not keep:
            continue
        try:
            weight = float(row.get("weight", .5))
        except (TypeError, ValueError):
            weight = .5
        out[label] = (keep, max(0.0, min(1.0, weight)))
    return out or None


def words_table() -> dict:
    """label -> (phrases, weight), in match order.

    The table above is the default. A `vision_words.json` in the data folder wins when it exists and reads
    cleanly, which is how a game PeakCut has never heard of gets its banners without a release."""
    f = config.DATA_DIR / "vision_words.json"
    try:
        at = f.stat().st_mtime_ns
    except OSError:
        at = 0
    if _table["at"] != at or _table["words"] is None:
        got = None
        if at and _table["noted"] != at:
            try:
                got = _clean_table(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError) as e:
                log.info("vision: %s could not be read (%s), the table built in is used", f, e)
            _table["noted"] = at
        _table.update(at=at, words=got or _bundled())
    return _table["words"]


def match_word(txt: str, table: Optional[dict] = None) -> Optional[str]:
    """The label this OCR text is, or None.

    A banner is usually read with something else beside it, so every run of words of the right length is tried and
    not only the whole line, and a near miss counts (ratio 0.8) - that is what makes a beaten-up OCR usable."""
    t = norm(txt)
    if len(t) < MIN_CHARS:
        return None
    table = words_table() if table is None else table
    tk = t.split()
    for label, (phrases, _w) in table.items():
        for p in phrases:
            n = len(p.split())
            cands = [t] + [" ".join(tk[i:i + n]) for i in range(max(1, len(tk) - n + 1))]
            if any(difflib.SequenceMatcher(None, c, p).ratio() >= MATCH_RATIO for c in cands):
                return label
    return None


# ---------------------------------------------------------------- one frame
def colour_cues(img) -> dict:
    """{"sat", "gold", "red"}: how saturated the frame is (0-1) and how much of its middle band is gold or red.

    Mean saturation is taken over the whole frame while the two colours are shares of the middle band, which is
    what the thresholds below were measured against."""
    zero = {"sat": 0.0, "gold": 0.0, "red": 0.0}
    xp = _cv()
    if xp is None or img is None or not getattr(img, "size", 0):
        return zero
    try:
        h, w = img.shape[:2]
        band = img[int(h * .25):int(h * .75)]
        if not band.size:
            return zero
        hsv = xp.cvtColor(band, xp.COLOR_BGR2HSV)
        full = xp.cvtColor(img, xp.COLOR_BGR2HSV)
        hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        return {"sat": float(full[..., 1].mean()) / 255,
                "gold": float(((hh > 15) & (hh < 35) & (ss > 110) & (vv > 170)).mean()),
                "red": float((((hh < 8) | (hh > 172)) & (ss > 140) & (vv > 120)).mean())}
    except Exception as e:  # noqa: BLE001 - a colour we cannot read is no cue, not a failure
        log.debug("vision: colour cues failed: %s", e)
        return zero


def banners(img) -> list:
    """(label or None, text, confidence, height of the text, x of its centre) for every word in the middle band.

    The height and the x are fractions of the whole frame, not of the crop, so the caller can ask "is this big and
    centred" without knowing how the picture was cut."""
    out = []
    try:
        h, w = img.shape[:2]
        y0, x0 = int(h * OCR_Y[0]), int(w * OCR_X[0])
        crop = img[y0:int(h * OCR_Y[1]), x0:int(w * OCR_X[1])]
        if not crop.size:
            return out
    except Exception as e:  # noqa: BLE001 - not a picture, nothing to read
        log.debug("vision: a frame could not be cropped: %s", e)
        return out
    try:
        found = _ocr(crop)
    except Exception as e:  # noqa: BLE001 - the engine died mid-job: no banners, no crash
        log.info("vision: the screen could not be read: %s", e)
        return out
    for item in found:
        try:
            box, txt, sc = item[0], str(item[1]), float(item[2])
            ys = [p[1] for p in box]
            xs = [p[0] for p in box]
            rh = (max(ys) - min(ys)) / h
            cx = (float(np.mean(xs)) + x0) / w
        except (IndexError, TypeError, ValueError, ZeroDivisionError):
            continue
        out.append((match_word(txt) if sc > CONF_WORD else None, txt, sc, rh, cx))
    return out


def detect_frame(img) -> list:
    """(kind, label, extra) for one frame: "word" for a banner the table knows, "text" for big centred capitals
    it does not.

    The gates for the second kind are all needed: big, sure, centred, four letters or more, and mostly capital
    letters. The source divides by the number of letters here, which is zero for digits or a script without case,
    so the count itself is required first - without it every "12345" on screen would be a banner."""
    ev = []
    try:
        cc = colour_cues(img)
        for lab, txt, sc, rh, cx in banners(img):
            if lab:
                ev.append(("word", lab, {"text": txt, "conf": round(sc, 2), "cues": cc}))
                continue
            letters = sum(c.isalpha() for c in txt)
            if (rh >= BIG_TEXT and sc > CONF_TEXT and CENTER[0] < cx < CENTER[1]
                    and len(norm(txt).replace(" ", "")) >= MIN_CHARS
                    and letters >= MIN_CHARS
                    and sum(c.isupper() for c in txt) >= .8 * letters):
                ev.append(("text", "TEXT " + norm(txt), {"text": txt, "conf": round(sc, 2), "cues": cc}))
    except Exception as e:  # noqa: BLE001
        log.debug("vision: a frame could not be judged: %s", e)
    return ev


def stars(img) -> int:
    """How many GTA-5 wanted stars are in the top-right strip: 0-5, or 0 when what is there is not stars.

    Off by default and not advertised: on real recordings six of seven hits were a chat overlay sitting in that
    corner, so it is only worth turning on for a source whose HUD is known."""
    xp = _cv()
    if xp is None or img is None:
        return 0
    try:
        h, w = img.shape[:2]
        roi = img[int(h * STAR_Y[0]):int(h * STAR_Y[1]), int(w * STAR_X):]
        if not roi.size:
            return 0
        hsv = xp.cvtColor(roi, xp.COLOR_BGR2HSV)
        mask = ((hsv[..., 0] > 15) & (hsv[..., 0] < 32)
                & (hsv[..., 1] > 120) & (hsv[..., 2] > 190)).astype(np.uint8)
        _n, _lab, st, _c = xp.connectedComponentsWithStats(mask)
        area = h * w
        # A star is a small square blob of bright yellow; a bar or a chat line is not square, and too many hits
        # means this is a HUD this code does not understand.
        keep = [s for s in st[1:]
                if .0004 * area < s[4] < .004 * area and .6 < s[2] / max(s[3], 1) < 1.5]
        return len(keep) if len(keep) <= 5 else 0
    except Exception as e:  # noqa: BLE001
        log.debug("vision: wanted stars could not be counted: %s", e)
        return 0


# ---------------------------------------------------------------- sightings into events
def merge(raw: list, gap: float = 15.0) -> list:
    """Collapse sightings into events: the same label seen again within `gap` seconds is one event.

    Every event carries t (first sighting), t_end (last), kind, label, hits and weight, plus whatever the sighting
    knew: the OCR text and the colour cues for a banner, the count for stars. Cut sightings all share the label
    CUT and therefore merge with each other, which is why cuts are not written into a transcript - see
    tag_transcript."""
    events, last = [], {}
    rows = sorted([r for r in (raw or []) if r], key=lambda r: float(r[0]))
    for row in rows:
        try:
            t, kind, label = float(row[0]), str(row[1]), row[2]
        except (IndexError, TypeError, ValueError):
            continue
        if not label:
            continue
        extra = row[3] if len(row) > 3 and isinstance(row[3], dict) else {}
        if label in last and t - last[label]["t_end"] <= gap:
            last[label]["t_end"] = round(t, 1)
            last[label]["hits"] += 1
            continue
        e = {"t": round(t, 1), "t_end": round(t, 1), "kind": kind, "label": label, "hits": 1,
             "weight": (words_table().get(label, ((), .5))[1] if kind == "word"
                        else {"stars": W_STARS, "cut": W_CUT}.get(kind, W_TEXT))}
        for k, v in extra.items():
            e.setdefault(k, v)
        events.append(e)
        last[label] = e
    for e in events:
        e["t_end"] = max(round(float(e["t_end"]), 1), e["t"])
    return events


def _attaches(e: dict) -> bool:
    """Whether this event may be written onto a transcript line.

    A cut never attaches (every cut merges into the one before it, so it says nothing about where a moment is), a
    banner nobody named needs three sightings (a passing sign is read once, a real banner stays up), and stars need
    to have reached three (one star is a HUD tick, not a chase)."""
    kind = e.get("kind")
    if kind == "cut":
        return False
    if kind == "text" and int(e.get("hits") or 0) < 3:
        return False
    if kind == "stars" and int(e.get("stars") or 0) < 3:
        return False
    return True


def _distance(line: dict, t: float, slack: float) -> Optional[float]:
    """How far the time is from a line, or None when it is further than `slack` seconds away beyond either end.
    Inside the line the distance is zero, so a line that covers the moment always beats its neighbours."""
    try:
        s, e = float(line["s"]), float(line["e"])
    except (KeyError, TypeError, ValueError):
        return None
    if t < s - slack or t > e + slack:
        return None
    if s <= t <= e:
        return 0.0
    return min(abs(t - s), abs(t - e))


def apply(lines: list, events: list, slack: float = 8.0) -> list:
    """Attach events to transcript lines: the heaviest label becomes line["game"], all of them line["games"].

    The rules are the source's, minus the text rewriting PeakCut has no use for: an event attaches to the line
    whose span it falls in, or to the nearest line within `slack` seconds of it. Returns new dicts; the lines
    passed in are not touched."""
    out = [dict(l) for l in (lines or []) if isinstance(l, dict)]
    got = {i: [] for i in range(len(out))}
    for e in events or []:
        if not isinstance(e, dict) or "t" not in e or not _attaches(e):
            continue
        try:
            t = float(e["t"])
        except (TypeError, ValueError):
            continue
        best, best_d = None, None
        for i, line in enumerate(out):
            d = _distance(line, t, slack)
            if d is not None and (best_d is None or d < best_d):
                best, best_d = i, d
        if best is not None:
            got[best].append(e)
    for i, line in enumerate(out):
        found = sorted(got[i], key=lambda e: float(e.get("t") or 0))
        labels = []
        for e in found:
            if e.get("label") and e["label"] not in labels:
                labels.append(e["label"])
        line["game"] = (max(found, key=lambda e: (float(e.get("weight") or 0), -float(e.get("t") or 0)))
                        .get("label") if found else None)
        line["games"] = labels
    return out


def _as_lines(words: list) -> list:
    """Lines from whatever the caller has: brain.make_lines output, or the raw [{'w', 's', 'e'}] words.

    Words are grouped the way brain.make_lines groups them (a pause, ten seconds, or a full stop ends a line).
    That grouping is repeated here on purpose: brain imports this module, so this one cannot import brain."""
    items = [w for w in (words or []) if isinstance(w, dict)]
    if not items:
        return []
    if any("text" in w for w in items):
        return [dict(w) for w in items]
    lines, cur = [], []

    def flush():
        if cur:
            lines.append({"s": cur[0]["s"], "e": cur[-1]["e"],
                          "text": " ".join(str(w.get("w", "")) for w in cur),
                          "loud": bool(any(w.get("loud") for w in cur))})
            cur.clear()

    for w in items:
        try:
            ws, we = float(w["s"]), float(w["e"])
        except (KeyError, TypeError, ValueError):
            continue
        if cur and (ws - cur[-1]["e"] > .7 or ws - cur[0]["s"] > 10
                    or (str(cur[-1].get("w", ""))[-1:] in ".?!" and len(cur) >= 4)):
            flush()
        cur.append({"w": str(w.get("w", "")), "s": ws, "e": we})
    flush()
    return lines


def tag_transcript(events: list, words: list, slack: float = 8.0) -> list:
    """The transcript with game events attached: every line comes back with "game" (the best label) and "games".

    `words` is either the word list from transcribe or lines already grouped by brain.make_lines; both are
    accepted, and lines come back either way."""
    return apply(_as_lines(words), events, slack)


# ---------------------------------------------------------------- reading a file
def _size(path: Path):
    """(width, height) of the first video stream, or (0, 0) when ffprobe cannot say."""
    try:
        proc = subprocess.run([_FFPROBE, "-v", "error", "-select_streams", "v:0",
                               "-show_entries", "stream=width,height", "-of", "default=nw=1", str(path)],
                              capture_output=True, text=True, timeout=60)
    except Exception:  # noqa: BLE001 - no ffprobe: the default shape below is used
        return 0, 0
    w = h = 0
    for line in (proc.stdout or "").splitlines():
        k, _, v = line.partition("=")
        try:
            if k.strip() == "width":
                w = int(v)
            elif k.strip() == "height":
                h = int(v)
        except ValueError:
            continue
    return w, h


def _duration(path: Path) -> float:
    try:
        proc = subprocess.run([_FFPROBE, "-v", "error", "-show_entries", "format=duration",
                               "-of", "default=nw=1:nk=1", str(path)],
                              capture_output=True, text=True, timeout=60)
        return max(0.0, float((proc.stdout or "").strip()))
    except Exception:  # noqa: BLE001 - no duration means no percentage, and the scan still runs
        return 0.0


def _frames(path: Path, start: float, end: Optional[float], rate: float, h2: int):
    """BGR frames from `path`, `rate` a second, 640 x `h2`, one at a time as ffmpeg produces them.

    Raw frames straight down a pipe, so nothing is written to disk. Closing the generator stops ffmpeg, which is
    how a scan that runs out of budget does not leave a decoder behind."""
    cmd = [_FFMPEG, "-v", "error", "-nostdin"]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(path)]
    if end is not None and end > start:
        cmd += ["-t", f"{max(.1, end - start):.3f}"]
    cmd += ["-vf", f"fps={rate:.6g},scale={CORE_W}:{h2}", "-an",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    size = CORE_W * h2 * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=size * 2)
    try:
        while True:
            buf = proc.stdout.read(size) if proc.stdout is not None else b""
            if not buf or len(buf) < size:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape(h2, CORE_W, 3).copy()
    finally:
        if proc.stdout is not None:
            try:
                proc.stdout.close()
            except OSError:
                pass
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass


def _budget_default() -> float:
    """The scan budget in seconds: the setting when the wiring has added one, otherwise this module's own."""
    got = getattr(config, "OCR_BUDGET_S", None)
    if got:
        return float(got)
    try:
        return float(config.env("PEAKCUT_OCR_BUDGET", "240"))
    except (TypeError, ValueError):
        return 240.0


def detect(source, start: float = 0.0, end: Optional[float] = None, *, fps: float = 1.0,
           want_stars: bool = False, budget_s: Optional[float] = None,
           max_frames: Optional[int] = None, on_progress: Optional[Callable[[float], None]] = None,
           meta: Optional[dict] = None) -> list:
    """Every game event between `start` and `end` seconds of `source`, in the source's own absolute time.

    The window narrows what is read, never the timestamps: an event at 3600 s is reported at 3600 s whatever was
    scanned, because that is the base the transcript is in.
    `budget_s` stops the scan early, returning what it has; it defaults to `config.OCR_BUDGET_S` or 240 s.
    `max_frames` caps the sampled frames. `on_progress` receives 0-1 as the file is consumed, and `meta`, when a
    dict is passed, is filled with what the caller needs to save the result honestly (window, scan_s, budget_hit).
    Returns [] when the feature is unavailable, the file cannot be read, or nothing was found. Never raises."""
    if not available():
        return []
    try:
        path = Path(str(source or ""))
        ok = path.is_file()
    except (OSError, ValueError):
        ok = False
    if not ok:
        log.info("vision: %s is not a file, so the picture is not read", source)
        return []

    rate = float(fps) if fps and float(fps) > 0 else 1.0
    t_start = float(start or 0.0)
    t_end = float(end) if end is not None else None
    if t_end is not None and t_end <= t_start:
        return []
    budget = _budget_default() if budget_s is None else float(budget_s)

    # One scan of a long video cannot starve every other job's render: the slot is waited for, and given up on.
    if not _SLOTS.acquire(timeout=max(1.0, min(budget, 60.0))):
        log.info("vision: every scan slot is busy, so %s was not read", path.name)
        return []

    started = time.time()
    hits = 0
    frames = 0
    budget_hit = False
    raw = []
    try:
        xp = _cv()
        w, h = _size(path)
        h2 = max(2, int(round(h * CORE_W / w / 2)) * 2) if w and h else 360
        total = 0
        dur = (t_end - t_start) if t_end is not None else _duration(path)
        if dur > 0:
            total = max(1, int(dur * rate))

        def say(frac):
            if on_progress is not None:
                try:
                    on_progress(max(0.0, min(1.0, frac)))
                except Exception:  # noqa: BLE001 - a progress callback must never cost a scan
                    pass

        prev_h = None          # the last hue/saturation histogram, for the cut test
        prev_band = None       # the last 80x40 centre band that was actually read
        sats = []              # the saturation of the frames read so far, newest last
        last_n = 0             # the last wanted-star count
        ocr_ok = True
        step = _frames(path, t_start, t_end, rate, h2)
        try:
            for i, f in enumerate(step):
                if max_frames is not None and i >= int(max_frames):
                    break
                if budget and time.time() - started > budget:
                    budget_hit = True
                    break
                frames += 1
                t = t_start + i / rate

                # A hard cut is a frame whose colours have nothing to do with the one before it. Brightness is
                # left out of the histogram on purpose, so a fade to black does not read as a cut.
                hsv = xp.cvtColor(f, xp.COLOR_BGR2HSV)
                hist = xp.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
                hist = xp.normalize(hist, hist).flatten()      # the source's default norm, which 0.55 was tuned on
                if prev_h is not None and xp.compareHist(prev_h, hist, xp.HISTCMP_BHATTACHARYYA) > CUT_DIST:
                    raw.append((t, "cut", "CUT", {}, None))
                prev_h = hist

                band = xp.resize(f[int(h2 * .2):int(h2 * .8)], (80, 40)).astype(np.int16)
                cc = colour_cues(f)
                sats.append(cc["sat"])
                if len(sats) > SAT_WINDOW:
                    del sats[:-SAT_WINDOW]
                usual = float(np.median(sats)) if sats else 0.0
                cue = (cc["gold"] > CUE_GOLD or cc["red"] > CUE_RED
                       or (usual > 0 and cc["sat"] < CUE_GREY * usual))
                moved = prev_band is None or float(np.abs(band - prev_band).mean()) > MOVE_MIN
                if ocr_ok and (cue or i % SWEEP == 0) and moved:
                    try:
                        for kind, label, extra in detect_frame(f):
                            hits += 1
                            raw.append((t, kind, label, extra, None))
                    except Exception as e:  # noqa: BLE001 - one unreadable frame is not the end of a scan
                        ocr_ok = False
                        log.info("vision: the screen could not be read any more (%s), carrying on without it", e)
                    prev_band = band

                if want_stars:
                    n = stars(f)
                    if n != last_n and n:
                        if n > last_n:
                            raw.append((t, "stars", f"STARS {n}", {"stars": n}, None))
                        last_n = n
                    elif not n:
                        last_n = 0

                if frames % 30 == 0:
                    if total:
                        say(frames / total)
                    elif budget:
                        say((time.time() - started) / budget)
        finally:
            step.close()
        say(1.0)
    except Exception as e:  # noqa: BLE001 - a picture pass that fails must never cost the clips
        log.info("vision: reading %s stopped: %s", getattr(path, "name", source), e)
    finally:
        _SLOTS.release()

    events = merge(raw)
    if meta is not None and isinstance(meta, dict):
        meta.update({"src": str(path), "fps": rate, "scan_s": round(time.time() - started, 1),
                     "window": [round(t_start, 1), round(t_end, 1) if t_end is not None else None],
                     "frames": frames, "budget_hit": bool(budget_hit), "events": len(events)})
    log.info("vision: %s: %d frames read, %d frames of text, %d events%s", path.name, frames, hits, len(events),
             " (the time budget ran out)" if budget_hit else "")
    return events


def scan(path: str, fps: float = 1.0, **more) -> list:
    """Every game event in a file, read `fps` times a second: the short form of detect() for a whole video."""
    return detect(path, fps=fps, **more)


# ---------------------------------------------------------------- what is kept, and what is shown
def summary(events: list) -> dict:
    """What a job may show the browser: {"count", "labels", "stars_max"}.

    Counts every event, but only names the ones a person would recognise: the cut events are a machine's way of
    knowing something changed and would only add "CUT: 41" to a job row."""
    labels, most, n = {}, 0, 0
    for e in events or []:
        if not isinstance(e, dict):
            continue
        n += 1
        lab = str(e.get("label") or "")
        if lab and e.get("kind") != "cut":
            labels[lab] = labels.get(lab, 0) + 1
        try:
            most = max(most, int(e.get("stars") or 0))
        except (TypeError, ValueError):
            continue
    return {"count": n, "labels": labels, "stars_max": most}


def save(job_dir, events: list, meta: Optional[dict] = None) -> Path:
    """Write <job_dir>/events.json and return its path. `meta` carries src, window, fps, scan_s, budget_hit.

    A failure is logged and the path is still returned: the caller only needs somewhere to point a route at, and
    losing the event file must not lose a finished clip."""
    d = Path(job_dir)
    f = d / "events.json"
    rows = [dict(e) for e in (events or []) if isinstance(e, dict)]
    body = {"version": 1}
    for k, v in (meta or {}).items():
        if k != "events":
            body[k] = v
    body["count"] = len(rows)
    body["events"] = rows
    try:
        d.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(body, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    except (OSError, TypeError, ValueError) as e:
        log.warning("vision: the game events could not be saved to %s: %s", f, e)
    return f


def load(job_dir) -> list:
    """The events saved for this job, or [] when there is no file or it cannot be read."""
    f = Path(job_dir) / "events.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        log.debug("vision: no events in %s: %s", job_dir, e)
        return []
    rows = data.get("events") if isinstance(data, dict) else data
    return [e for e in rows if isinstance(e, dict)] if isinstance(rows, list) else []
