"""Job pipeline: get video -> audio -> transcript -> AI picks -> rendered clips. One heavy task at a time."""
import collections
import json
import os
import math
import queue
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

from . import (brain, brand, captions, config, creators, ctx, facecam, formats, games, load, media, meme, memesound, moments,
               music, quality, render, roman, safe, signals, transcribe, usage)

class _FairQueue:
    """Whose video is next. Each person has their own line and the lines take turns, so someone who adds ten
    videos does not make everyone else wait behind all ten. Small tasks (re-making one clip) go first."""

    def __init__(self):
        self.cv = threading.Condition()
        self.quick = collections.deque()
        self.lines = {}                       # user -> their waiting videos, oldest first
        self.turn = collections.deque()       # users with something waiting, in the order they will be served
        self.epoch = 0                        # goes up whenever the line moves
        self._pos = (0.0, {})
        self.running = 0                      # videos being worked on right now
        self.last_start = 0.0
        self.held = False                     # videos are waiting only because the machine is near full

    def _room(self) -> bool:
        """May one more video start? One always may. More only while the machine has room, and a few seconds
        after the last one started, so its weight is already showing in the measurements."""
        if self.running == 0:
            return True
        return self.running < config.JOB_WORKERS and time.time() - self.last_start > 6 and not load.busy()

    def done(self):
        with self.cv:
            self.running = max(0, self.running - 1)
            self.cv.notify_all()

    def put(self, item, user=None):
        with self.cv:
            if user is None:
                self.quick.append(item)
            else:
                if user not in self.lines:
                    self.lines[user] = collections.deque()
                    self.turn.append(user)
                self.lines[user].append(item)
            self.epoch += 1
            self.cv.notify()

    def get(self, quick_only=False):
        with self.cv:
            while True:
                if self.quick:
                    self.epoch += 1
                    return self.quick.popleft()
                if not quick_only and self.turn:
                    if self._room():
                        break
                    if not self.held:
                        self.held = True
                        self.epoch += 1
                elif self.held:
                    self.held = False
                    self.epoch += 1
                self.cv.wait(1.0)             # looked at again every second: the line moves the moment there is room
            self.epoch += 1
            self.held = False
            self.running += 1
            self.last_start = time.time()
            user = self.turn.popleft()
            item = self.lines[user].popleft()
            if self.lines[user]:
                self.turn.append(user)
            else:
                del self.lines[user]
            return item

    def ahead(self) -> dict:
        """job id -> how many videos will start before it. Worked out at most once a second."""
        with self.cv:
            if time.time() - self._pos[0] < 1:
                return self._pos[1]
            out, lines, order, n = {}, {u: list(q) for u, q in self.lines.items()}, list(self.turn), 0
            depth = 0
            while order:
                nxt = []
                for u in order:
                    if depth < len(lines[u]):
                        out[lines[u][depth][1]] = n
                        n += 1
                        if depth + 1 < len(lines[u]):
                            nxt.append(u)
                order, depth = nxt, depth + 1
            self._pos = (time.time(), out)
            return out


_q = _FairQueue()
_live_q: "queue.Queue" = queue.Queue()   # live clips never wait behind a long video
_jobs: dict = {}
_by_user: dict = {}                       # user -> {job id: job}: listing one person's videos never scans everyone's
_lock = threading.RLock()
on_clip_ready: list = []   # callbacks (job, clip), run once when a clip first finishes

# The story of a whole video is read before its first part is judged only when the video is under an hour. A longer
# one builds its story part by part as it is judged: on the owner's 5 h 45 min stream the read-ahead was 36 long AI
# answers (about 2.5 minutes each, two at a time on that service), so no clip appeared for over 40 minutes.
WHOLE_STORY_MAX = 3600
JUDGE_AHEAD = 3     # parts of a video judged at the same time
ALL_CLIPS = 100     # what "0 = as many as possible" stops at, the same cap one live recording has
DEFAULTS = {"max_clips": 6, "min_len": 15, "max_len": 60, "style": "bounce", "layout": "blur", "quality": 1080,
            "range_start": None, "range_end": None, "captions": True, "format": None, "moment_labels": False,
            "bg": "", "censor": False, "cleanup": False}


LIMITS = {"max_clips": (0, 100), "min_len": (5, 120), "max_len": (10, 180), "quality": (360, 1440)}

# What can fill the frame behind a video that does not fill it. "" is the blurred copy of that video, which is the
# look most shorts use; the flat colours are for people who want the picture to sit on black or white instead.
BGS = ("", "black", "white")


def clean_options(options) -> dict:
    """Only known settings, each inside its allowed range. Raises ValueError on nonsense."""
    out = {}
    for k, v in (options if isinstance(options, dict) else {}).items():
        if k == "captions":
            if not isinstance(v, bool):
                raise ValueError("Captions must be on or off.")
            out[k] = v
            continue
        if k == "moment_labels":
            # Opt-in only: a job without this key gets exactly the clips it got before.
            if not isinstance(v, bool):
                raise ValueError("Moment labels must be on or off.")
            out[k] = v
            continue
        if k == "sound":
            # A sound under every clip of this job. Checked against the sounds that really exist, so a name left
            # over from an old build becomes "no sound" instead of a failed clip.
            word = str(v or "").strip().lower()[:20]
            out[k] = word if (word in meme.load_moods() or word in music.MOODS) else ""
            continue
        if k == "format":
            if v in ("", None):
                out[k] = None                    # no format named: pick the way we always did
                continue
            name = str(v).strip().lower()[:20]
            # A format we do not know falls back to the plain one, so an old page or a typo still makes clips.
            out[k] = name if name in formats.FORMATS else None
            continue
        if k not in DEFAULTS or v in ("", None):
            continue
        if k in LIMITS:
            lo, hi = LIMITS[k]
            v = max(lo, min(hi, int(float(v))))
        elif k == "style":
            # Both halves count: PeakCut's own three looks and the caption looks in captions.py. Checking only
            # render.STYLES silently turned every one of the other looks into bounce.
            v = v if (v in render.STYLES or v in captions.style_names()) else DEFAULTS["style"]
        elif k == "layout":
            v = v if v in render.LAYOUTS else DEFAULTS["layout"]
        elif k == "bg":
            # What shows behind a video that does not fill the frame. A name we do not know becomes the blurred
            # copy of the video, which is what every clip did before this setting existed.
            v = str(v).strip().lower()[:10]
            v = v if v in BGS else ""
        elif k in ("censor", "cleanup"):
            # Two switches, not a free value: anything that is not clearly on is off.
            v = v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "on", "yes")
        else:                                    # range_start, range_end: seconds into the video
            v = float(v)
            if not math.isfinite(v) or v < 0:
                raise ValueError("That part of the video isn't valid.")
        out[k] = v
    if out.get("range_end") is not None and out["range_end"] <= out.get("range_start", 0):
        raise ValueError("The end of the chosen part must be after its start.")
    return out


def job_dir(jid) -> Path:
    return Path(_jobs[jid]["dir"])


HIDDEN = ("dir", "user", "source_path", "recover")


def public(job) -> dict:
    """What the browser may see: no server paths, no owner id."""
    out = {k: v for k, v in job.items() if k not in HIDDEN}
    out["source"] = {k: v for k, v in job["source"].items() if k != "path"}
    out["clips"] = [{k: v for k, v in c.items() if k not in ("src", "fixed_words", "fixed_for")} for c in job["clips"]]
    ai = job.get("ai") or {}
    out["ai"] = {"tokens": ai.get("tokens", 0), "note": ai.get("note", ""), "used": bool(ai.get("model"))}   # never the model, never raw errors
    # How much of the video has actually been listened to, so a page can show a real picture of the work
    # rather than a spinner. `heard_to` is the second reached, `blocks_done` of `blocks_total` the parts
    # already written. Always sent (zero when nothing is known yet) so the shape never changes under a page.
    dur = float(job.get("duration") or 0)
    heard = float(job.get("heard_to") or 0)
    out["heard_to"] = round(heard, 1)
    out["watched_pct"] = round(min(100.0, 100.0 * heard / dur), 1) if dur > 0 else 0.0
    out["blocks_done"] = int(job.get("blocks_done") or 0)
    out["blocks_total"] = int(job.get("blocks_total") or 0)
    if job.get("status") == "queued":
        n = _q.ahead().get(job["id"])
        if n:
            out["stage"] = (f"High demand right now: {n} video{'s' if n != 1 else ''} ahead of yours" if _q.held else
                            f"Waiting in line: {n} video{'s' if n != 1 else ''} ahead of yours")
        elif n == 0 and _q.held:
            out["stage"] = "High demand right now: yours is next"
    return out


def save(job):
    ctx.bump(job.get("user"))
    with _lock:
        d = Path(job["dir"])
        for _ in range(5):
            try:
                text = json.dumps(job, indent=1)
                break
            except RuntimeError:  # changed mid-dump by another thread
                time.sleep(0.05)
        else:
            return
        tmp = d / "job.json.tmp"
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(d / "job.json")


def _set(job, **kw):
    with _lock:
        job.update(kw)
    save(job)


def _remap(path, folder: Path):
    """Paths saved before data moved into per-user folders (or on another machine): find the file by name."""
    if path and not Path(path).exists():
        cand = folder / Path(str(path).replace("\\", "/")).name
        if cand.exists():
            return str(cand)
    return path


def _load_file(f: Path, uid: str):
    try:
        job = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    job.update(dir=str(f.parent), user=uid)
    job.setdefault("kind", "video")
    job.setdefault("creator", None)
    job.setdefault("options", {}).setdefault("captions", True)
    if job.get("source_path"):
        job["source_path"] = _remap(job["source_path"], f.parent)
    if job.get("source", {}).get("path"):
        job["source"]["path"] = _remap(job["source"]["path"], f.parent)
    if job.get("status") in ("queued", "running") and job.get("kind") != "live" and job.get("stop"):
        # Stop was pressed and the server went down before it finished: it is not started again. A clip that was
        # still waiting says so and can be re-made by hand.
        for c in job.get("clips", []):
            if c.get("status") in ("queued", "rendering"):
                c.update(status="error", error="Stopped before this clip was made. Press Re-make to make it.")
        n = sum(1 for c in job.get("clips", []) if c.get("status") == "done")
        job.update(status="done", progress=1.0, resume=False,
                   stage=f"Stopped by you with {n} clip{'s' if n != 1 else ''}")
    if job.get("status") in ("queued", "running") and job.get("kind") != "live":
        # Picked up again as soon as the server is back (jobs.start), from the last finished part of the transcript.
        job.update(status="queued", stage="Picking up where it stopped", error=None, resume=True)
    if job.get("status") == "live":
        job.update(status="done", stage="Recording paused by a server update", was_live=True)
    buffered = job.get("kind") == "live" and any((f.parent / "buffer").glob("*.ts"))
    for c in job.get("clips", []):
        c.setdefault("captions", job["options"]["captions"])
        if c.get("plan") is not None and not isinstance(c["plan"], dict):
            c["plan"] = None                # an old or hand-edited plan must not reach the page as nonsense
        if c.get("moment") is not None and not isinstance(c["moment"], str):
            c.pop("moment", None)           # likewise a label we no longer understand
        if c.get("src"):
            c["src"] = _remap(c["src"], f.parent / "clips")
        if c.get("status") in ("rendering", "queued"):
            if buffered and not c.get("src"):
                c["status"] = "queued"  # the stream is still on disk: live.recover() finishes these
                job["recover"] = True
            elif job.get("resume"):
                c["status"] = "queued"  # the video is being picked up again: this clip is made then
            elif job.get("kind") != "live" and (f.parent / "words.json").is_file():
                c["status"] = "queued"  # a single clip being re-made: jobs.start() makes it again
                job.setdefault("remake", []).append(c["id"])
            else:
                c.update(status="error", error="Interrupted by a restart. Open it and press Save and re-make.")
    for item in [job.get("options", {})] + job.get("clips", []):
        if item.get("style") in captions.POST_ONLY_STYLES:
            item["style"] = DEFAULTS["style"]
    _jobs[job["id"]] = job
    _by_user.setdefault(uid, {})[job["id"]] = job


def load_user(uid: str):
    d = config.USERS_DIR / uid
    for f in list((d / "jobs").glob("*/job.json")) + list((d / "creators").glob("*/*/*/job.json")):
        _load_file(f, uid)


def load_all():
    for d in config.USERS_DIR.iterdir():
        if d.is_dir():
            load_user(d.name)


def all_jobs() -> list:
    """Every user's jobs. Only for background work; never send this to a browser."""
    with _lock:
        return list(_jobs.values())


def list_jobs():
    u = ctx.uid()
    with _lock:
        return sorted((dict(j) for j in _by_user.get(u, {}).values()), key=lambda j: -j["created"])


def get(jid):
    """The job, only if it belongs to whoever this code is running for."""
    job = _jobs.get(jid)
    return job if job and job["user"] == ctx.uid() else None


def busy_count() -> int:
    u = ctx.uid()
    return sum(1 for j in list(_by_user.get(u, {}).values()) if j["kind"] == "video" and j["status"] in ("queued", "running"))


def waiting_total() -> int:
    return sum(1 for j in list(_jobs.values()) if j["kind"] == "video" and j["status"] == "queued")


def queue_epoch() -> int:
    return _q.epoch


def running_now() -> int:
    return _q.running


def _brand_prefs(user) -> dict:
    """The parts of the brand document that decide what a job makes, as option defaults.

    The Brand page already decides how clips are dressed; this lets the same document decide what they are: the
    caption look, whether captions burn in, the length a clip starts from, and the sound under every clip. Every
    value is checked before it reaches a job, so a brand left over from an old build cannot break a new one.

    Only a value the person actually changed counts. The brand document carries its own defaults, and they are not
    the same as the ones a job uses, so passing them on would quietly overrule the job. A brand nobody has touched
    therefore adds nothing here."""
    try:
        doc = brand.load(user or "default")
    except Exception:  # noqa: BLE001 - a brand that will not load is the neutral look, never a failed job
        return {}
    said = brand.DEFAULTS
    out = {}
    style = str(doc.get("style") or "").strip().lower()
    if style != str(said.get("style") or "").lower() and (style in render.STYLES or style in captions.style_names()):
        out["style"] = style
    if isinstance(doc.get("captions"), bool) and doc["captions"] != said.get("captions"):
        out["captions"] = doc["captions"]
    try:
        span = float(doc.get("clip_len") or 0)
    except (TypeError, ValueError):
        span = 0.0
    if span and span != float(said.get("clip_len") or 0):
        out["max_len"] = max(LIMITS["max_len"][0], min(LIMITS["max_len"][1], int(span)))
    sound = str(doc.get("sound") or "").strip().lower()[:20]
    if sound and sound != str(said.get("sound") or "").lower():
        if sound in meme.load_moods() or sound in music.MOODS:
            out["sound"] = sound
    return out


def create(source: dict, options: dict, enqueue=True, creator=None, kind="video") -> dict:
    jid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:10]
    c = creators.get(creator) if creator else None
    if c:
        d = creators.root(c["id"]) / ("live" if kind == "live" else "videos") / jid
        base = {**DEFAULTS, **{k: c[k] for k in ("max_clips", "min_len", "max_len", "style", "layout", "captions")}}
    else:
        d, base, creator = config.user_dir(ctx.uid()) / "jobs" / jid, dict(DEFAULTS), None
    # What the person set on the Brand page is the starting point; a value typed on the form for this one job
    # still wins, because `options` is merged last.
    base = {**base, **_brand_prefs(ctx.uid())}
    opts = {**base, **clean_options(options)}
    opts.setdefault("sound", base.get("sound", ""))
    if opts["min_len"] >= opts["max_len"]:
        opts["min_len"] = max(5, opts["max_len"] - 5)
    job = {"id": jid, "user": ctx.uid(), "kind": kind, "creator": creator, "dir": str(d), "created": time.time(), "source": source,
           "options": opts, "status": "queued", "stage": "Waiting", "progress": 0.0,
           "title": source.get("name", ""), "uploader": "", "duration": 0, "clips": [], "error": None, "ai": {}}
    d.mkdir(parents=True)
    with _lock:
        _jobs[jid] = job
        _by_user.setdefault(job["user"], {})[jid] = job
    save(job)
    if enqueue:
        _q.put(("job", jid, None), user=job["user"])
    return job


def enqueue(job):
    save(job)
    _q.put(("job", job["id"], None), user=job["user"])


def submit(fn):
    """Run any heavy task (a render, a cleanup) on the single worker, in order."""
    _q.put(("fn", ctx.bind(fn), None))


def submit_live(fn):
    """Live-stream renders and cleanups: their own worker, so a long video can never hold them up."""
    _live_q.put(ctx.bind(fn))


def _live_worker():
    while True:
        fn = _live_q.get()
        try:
            fn()
        except Exception:  # noqa: BLE001
            traceback.print_exc()


def delete(jid):
    with _lock:
        job = _jobs.pop(jid, None)
        if job:
            _by_user.get(job["user"], {}).pop(jid, None)
    if job:
        ctx.bump(job["user"])
        shutil.rmtree(job["dir"], ignore_errors=True)
    return bool(job)


def request_render(jid, cid, changes: dict):
    job = _jobs[jid]
    clip = next(c for c in job["clips"] if c["id"] == cid)
    new = dict(clip)
    if "captions" in changes:
        new.update(clean_options({"captions": changes["captions"]}))
    for k in ("start", "end"):
        if k in changes:
            # A time that is not a number becomes a plain sentence, not Python's own complaint about float().
            try:
                new[k] = round(float(changes[k]), 2)
            except (TypeError, ValueError):
                raise ValueError("Times must be numbers, like 12.5.") from None
    if "src_offset" in clip:  # live clip: can only move inside the saved piece of stream
        new["start"] = max(new["start"], clip["src_offset"])
        new["end"] = min(new["end"], clip["src_end"])
    if not (math.isfinite(new["start"]) and math.isfinite(new["end"])) or new["start"] < 0:
        raise ValueError("Those times aren't valid.")
    if not 3 <= new["end"] - new["start"] <= 180:
        raise ValueError("A clip can be 3 to 180 seconds long.")
    for k in ("hook", "title", "description", "style", "layout"):
        if k in changes:
            new[k] = str(changes[k])[:{"hook": 60, "title": 100, "description": 2000}.get(k, 20)]
    if "format" in changes:
        # One clip can be given another format. A name we do not know means the plain one, not an error.
        new["format"] = (str(changes["format"]).strip().lower()[:20] if changes["format"] not in ("", None) else None)
        if new["format"] not in formats.FORMATS:
            new["format"] = None
        if new["format"] in formats.JOINS:
            # Callback, Compilation, Escalation and Then vs now join several clips of a video, so they are made from
            # the Montages page (studio/montage.py). One clip holds one moment: given one of these it is a plain clip.
            new["format"] = None
    if "chat" in changes:
        # The lines the Chat type pops up after the big moment. Clipstorm records how busy chat was, never what it
        # said, so the person types them. A list of short lines, or None for none at all.
        lines = changes["chat"]
        if lines in (None, ""):
            new["chat"] = None
        elif not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            raise ValueError("Chat lines must be a list of short lines of text.")
        else:
            lines = [" ".join(x.split())[:formats.CHAT_TEXT_MAX] for x in lines]
            new["chat"] = [x for x in lines if x][:formats.CHAT_MAX] or None
    if "mood" in changes:
        # One word names the sound. "" means no sound at all, which is different from "not mentioned".
        new["mood"] = str(changes["mood"] or "").strip().lower()[:20] or None
    if "bg" in changes:
        # What fills the frame behind a video that does not fill it. "" is the blurred copy of the video itself.
        word = str(changes["bg"] or "").strip().lower()[:10]
        new["bg"] = word if word in BGS else ""
    for flag in ("censor", "cleanup"):
        if flag in changes:
            # Swearing out, or the dead air out. Anything that is not clearly on is off, so a page that sends the
            # string "false" turns the switch off rather than on.
            said = changes[flag]
            new[flag] = said if isinstance(said, bool) else str(said).strip().lower() in ("1", "true", "on", "yes")
    if new.get("style") not in render.STYLES and new.get("style") not in captions.style_names():
        new["style"] = DEFAULTS["style"]
    if new.get("layout") not in render.LAYOUTS:
        new["layout"] = DEFAULTS["layout"]
    clip.update(new, status="queued")
    save(job)
    _q.put(("clip", jid, cid))


def _hook_words(job) -> str:
    """How this job's person asked for hooks to be written, or "" for whatever works best.

    The words live in the brand document, which is also what the Improve page changes when the numbers say the
    hooks are not holding people. Kept here rather than in the AI prompt so the same sentence dresses every place
    that writes a hook: the clip finder, the live checks, and a hand-made clip."""
    try:
        return str(brand.load(job.get("user") or "default").get("hook_words") or "")[:160]
    except Exception:  # noqa: BLE001 - a brand that will not load means no preference, never a failed clip
        return ""


def _brand_kwargs(job) -> dict:
    """The brand to render this clip with, as a keyword argument, or nothing at all.

    The Brand page saves a document per signed-in person, so the document that dresses a clip is the one belonging
    to the person who started the job. A brand that will not load is not worth failing a clip over: it comes back
    as None, so the clip is rendered in PeakCut's own look. A renderer that does not take a brand yet gets no
    keyword, so the two halves can land in either order."""
    doc = None
    try:
        import inspect

        takes_brand = "brand" in inspect.signature(render.render_clip).parameters
    except (TypeError, ValueError):
        takes_brand = False
    if takes_brand:
        try:
            doc = brand.load(job.get("user") or "default")
        except Exception:  # noqa: BLE001
            doc = None
    return {"brand": doc} if takes_brand else {}


def _webcam_in(job, src) -> list | None:
    """The webcam's box in this video, or None. The place already known for the job is tried first and only
    believed if its border is really in this picture; otherwise the picture is searched."""
    try:
        known = job.get("facecam")
        if known and len(known) == 4 and facecam.still_there(src, known):
            return [int(v) for v in known]
        box = facecam.detect(src)
        if box and box.get("conf") == "high":
            found = [box["x"], box["y"], box["w"], box["h"]]
            if not job.get("facecam"):
                job["facecam"] = found
            return found
    except Exception:  # noqa: BLE001 - no webcam is a layout, never a failed clip
        traceback.print_exc()
    return None


def render_one(job, clip, words):
    d = Path(job["dir"])
    clip["status"] = "rendering"
    save(job)
    try:
        if not clip.get("src") and not job.get("source_path"):
            _piece_again(job, clip)
        off = clip.get("src_offset", 0.0)
        src = Path(clip["src"]) if clip.get("src") else Path(job["source_path"])
        if not clip.get("src"):
            clip["end"] = min(clip["end"], job["duration"])
        local = dict(clip, start=clip["start"] - off, end=clip["end"] - off, hook=roman.to_roman(clip.get("hook") or ""))
        near = _caption_words(job, clip, words, off) if clip.get("captions", True) else []
        # How this clip is put together (its format, its spans, its chips). Worked out before the render so the
        # renderer and the page can both read it. Optional: a clip still renders when the plan cannot be made.
        try:
            plan = json.loads(json.dumps(formats.plan(local, near)))   # plain JSON: the plan is saved with the job
        except Exception:  # noqa: BLE001 - a plan is a nicety, never a reason to lose a clip
            plan = None
            traceback.print_exc()
        if plan is not None:
            clip["plan"] = local["plan"] = plan
        # A layout that shows the streamer has to know where the webcam is in THIS clip. A clip made before one
        # was found, or switched to such a layout in the editor, carries none - and the renderer then quietly
        # made a plain clip, so choosing "Facecam on top" appeared to do nothing. Look in the clip's own video.
        wants_face = local.get("layout") in ("gameplay", "stack") or (plan and plan.get("format") == "reveal")
        if wants_face and not (local.get("facecam") and len(local["facecam"]) == 4):
            box = _webcam_in(job, src)
            if box:
                clip["facecam"] = local["facecam"] = box
            else:
                clip["layout_note"] = "No webcam was found in this clip, so it was made without the streamer panel."
        elif clip.get("layout_note"):
            clip.pop("layout_note", None)
        # A Reveal keeps the streamer's face hidden until the payoff, so it needs the layout that has a face panel.
        if plan and plan.get("format") == "reveal" and local.get("facecam"):
            local["layout"] = "stack"
        out = render.render_clip(src, d / "clips", clip["id"], local, near, job["width"], job["height"],
                                 **_brand_kwargs(job))
        # The clip's type (Wait for it, Reveal...) is drawn onto the finished file. For a long time the plan was
        # worked out and then never used, so every type came out as the same clip. Never a reason to lose a clip.
        try:
            from . import format_finish
            if plan and out.get("layout") in ("stack", "gameplay") and local.get("hook"):
                # In these layouts the heading sits near the top, exactly where the type's tag is drawn, and the
                # two ended up printed over each other. The tag and its bar move up into the clear strip above it.
                for chip in plan.get("chips") or []:
                    if chip.get("kind") == "bar":
                        chip["y"] = 96
                    elif chip.get("kind") in ("tag", "badge") and int(chip.get("y") or 0) < 400:
                        chip.update(y=124, size=min(int(chip.get("size") or 80), 60))
            drawn = format_finish.finish(plan, d / "clips" / out["file"],
                                         bool(local.get("facecam")) and out.get("layout") == "stack")
            # why the chosen type is not on the clip, when it is not, so the page never shows a type that was not drawn
            clip["format_note"] = (drawn or {}).get("skipped") or None
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        _add_pictures(clip, out, d / "clips")
        _add_sound(clip, out, d / "clips")
        _add_cues(clip, out, d / "clips")
        clip.update(out, status="done", version=clip.get("version", 0) + 1, error=None)
        post = {k: clip[k] for k in ("title", "description", "hashtags", "hook", "start", "end", "score")}
        (d / "clips" / f"{clip['id']}.json").write_text(json.dumps(post, indent=1), encoding="utf-8")
        if clip["version"] == 1:
            clip.setdefault("made_at", time.time())
            creators.log(job["creator"], f"Clip ready (score {clip['score']}): {clip['title'] or clip['hook']}")
            save(job)
            for fn in on_clip_ready:
                try:
                    fn(job, clip)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
    except Exception as e:  # noqa: BLE001
        clip.update(status="error", error=safe.friendly(e, 400))
        creators.log(job["creator"], f"Clip failed: {safe.friendly(e, 200)}")
    save(job)


def _add_pictures(clip, out: dict, folder: Path) -> None:
    """Draws the clip's pictures (poster, logo, stickers) onto the file that was just rendered.

    A clip draws a template's arrangement, its own arrangement, or both: its own wins, because a placement made on
    this one clip is a decision about this one clip. The pictures are burned into the frames with the SAME code the
    preview uses (`overlay.chain`), so what was dragged in the editor is what comes out.
    """
    from . import overlay

    items = overlay.clean_items(clip.get("overlay") or [])
    tid = str(clip.get("overlay_template") or "")
    if tid and not items:
        tpl = overlay.template(tid)
        items = overlay.clean_items((tpl or {}).get("items") or [])
    if not tid and not items:
        return
    made = folder / out["file"]
    merged = list(items)
    if tid and (clip.get("overlay") or []):
        tpl = overlay.template(tid)
        merged = overlay.clean_items((tpl or {}).get("items") or []) + items
    if not merged:
        return
    tmp = folder / f".{made.stem}.pics.mp4"
    try:
        work = Path(render._workdir())
        try:
            inputs, steps = overlay.chain(merged, work, render.W, render.H, start_input=1)
            if not steps:
                return
            media.run(["ffmpeg", "-y", "-v", "error", "-i", str(made)] + inputs
                      + ["-filter_complex", "[0:v]null[v0];" + steps, "-map", "[vout]", "-map", "0:a?",
                         "-c:a", "copy", "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)],
                      cwd=str(work), timeout=render.RENDER_SECONDS)
            if tmp.is_file() and tmp.stat().st_size > 0:
                tmp.replace(made)
                out["pictures"] = len(merged)
        finally:
            shutil.rmtree(str(work), ignore_errors=True)
    except Exception as e:      # noqa: BLE001 - a picture that will not draw must never lose the clip
        print(f"The pictures were not drawn, so the clip keeps its own frames: {e}")
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _add_cues(clip, out: dict, folder: Path) -> None:
    """Puts the meme sounds written on a clip onto the file that was just rendered.

    This is the timeline half of the sound work: `_add_sound` below places ONE mood at the payoff, while a clip can
    also carry a list of cues, each with its own time, so a sound can land on any beat. They are mixed here, after
    the single mood, so a clip with both gets both.

    The picture is copied, never re-encoded, so this cannot change a frame. A failure leaves the file exactly as it
    was rendered and says why in the log: a clip must never be lost to a sound."""
    cues = clip.get("sounds")
    if not isinstance(cues, list) or not cues:
        return
    made = folder / out["file"]
    if not made.is_file():
        return
    try:
        plan = memesound.tidy(cues)
    except Exception as e:                         # noqa: BLE001 - a broken cue list is a log line, not a lost clip
        print(f"Meme sounds: {safe.friendly(e)}", flush=True)
        return
    if not plan:
        return
    tmp = folder / f".{made.stem}.cues.mp4"
    try:
        memesound.mix(made, plan, tmp)
        if tmp.is_file() and tmp.stat().st_size > 0:
            tmp.replace(made)
            out["sounds_mixed"] = len(plan)
        else:
            print("Meme sounds: ffmpeg wrote nothing, so the clip keeps its own audio.", flush=True)
    except (ValueError, RuntimeError) as e:
        print(f"Meme sounds were not added: {safe.friendly(e)}", flush=True)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def _add_sound(clip, out: dict, folder: Path) -> None:
    """Puts the clip's chosen sound on the file that was just rendered, before it is called done.

    A name can be a meme noise or a music bed, and `funny` and `hype` are both, so the meme table is asked first -
    a gag is what a person picked the sound for. Music only ever adds a bed under the voice, so it is the safe second
    guess. Nothing here can lose a clip: a failure leaves the picture as rendered and says why in the job log."""
    mood = str(clip.get("mood") or "").strip().lower()
    if not mood:
        return
    made = folder / out["file"]
    if not made.is_file():
        return
    tmp = folder / f".{made.stem}.sound.mp4"
    applied = False
    try:
        got = None
        try:
            if mood in meme.load_moods():
                got = meme.apply(made, mood, out=tmp)
        except Exception as e:                     # noqa: BLE001 - the picture is already good, keep it
            print(f"Sound {mood}: {safe.friendly(e)}", flush=True)
        if got is None and mood in music.MOODS:
            got = music.apply(made, mood, tmp)     # returns `made` untouched when it cannot mix
        if got and Path(got) != made and Path(got).is_file() and Path(got).stat().st_size > 0:
            Path(got).replace(made)
            applied = True
        # The cover is a frame of the finished file, so a gag that adds its own frames gets a new one.
        if applied and (folder / out["cover"]).is_file():
            span = float(clip.get("end") or 0) - float(clip.get("start") or 0)
            cover_t = min(1.2, span / 2) if span > 0 else 1.2
            media.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{cover_t:.2f}", "-i", str(made), "-frames:v", "1",
                       "-q:v", "3", str(folder / out["cover"])])
    except Exception as e:  # noqa: BLE001
        print(f"Sound {mood} was not added: {safe.friendly(e)}", flush=True)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    # Only a sound that really reached the file is written on the clip: the page shows this word as a fact.
    if applied:
        out["mood"] = mood
    else:
        print(f"Sound {mood} was not added, so the clip keeps its own audio.", flush=True)


def _caption_words(job, clip, words, off):
    span = [round(clip["start"], 2), round(clip["end"], 2), "en2"]      # "en2": captions made always-English
    if clip.get("fixed_for") == span and clip.get("fixed_words") and not any(
            roman.needs_roman(w.get("w", "")) for w in clip["fixed_words"]):
        raw = clip["fixed_words"]          # already tidied for this exact span: no second AI call
    else:
        raw = [w for w in words if clip["start"] - 1 <= w["s"] <= clip["end"] + 1]
        try:
            usage.set_context(job.get("creator"), job.get("title") or "")
            raw = brain.english_captions(raw, job.get("lang") or "", job.get("title") or "",
                                         youtube_english=lambda: _english_part(job, clip))
            clip.update(fixed_words=raw, fixed_for=span)
        except Exception:  # noqa: BLE001 - captions still render with the words as heard
            pass
    # the last word on it: whatever was said, nothing is drawn in Hindi or Urdu script
    return [dict(w, s=w["s"] - off, e=w["e"] - off) for w in roman.words(raw)]


CLIP_MINUTES = float(config.env("PEAKCUT_CLIP_MINUTES", "15"))     # the longest one clip may take to make


def _wait_for_clips(job, futures, began, workers):
    """Wait for a video's clips, but not for ever. A clip that hangs (a download that stalls, an encoder that
    freezes) used to keep the whole video "in progress", and no other clip could be re-made. Now it is marked as
    failed after CLIP_MINUTES and the video finishes with the clips that did work."""
    left, given_up = list(futures), 0
    late = "This clip took too long and was stopped. Open it and press Save and re-make to try again."
    while left:
        still = []
        for f, clip in left:
            if f.done():
                f.result()
                continue
            t = began.get(clip["id"])
            if (t and time.time() - t > CLIP_MINUTES * 60) or (not t and given_up >= workers):
                given_up += 1
                clip.update(status="error", error=late)
                creators.log(job["creator"], f"Clip stopped after {CLIP_MINUTES:g} minutes: {clip.get('title') or clip.get('hook') or clip['id']}")
                save(job)
                continue
            still.append((f, clip))
        left = still
        if left:
            time.sleep(1)


def _english_part(job, clip):
    """YouTube's English captions for just this clip, for a video in another language. Fetched once per video."""
    if (job.get("source") or {}).get("type") != "url":
        return None
    f = Path(job["dir"]) / "words_en.json"
    if f.is_file():
        en = json.loads(f.read_text(encoding="utf-8"))
    else:
        try:
            en = media.youtube_english_words(job["source"]["url"]) or []
        except Exception:  # noqa: BLE001 - YouTube often refuses its translations: the AI translates instead
            en = []
        f.write_text(json.dumps(en), encoding="utf-8")       # asked once per video, refused or not
    return [w for w in en if clip["start"] - 0.5 <= w["s"] <= clip["end"] + 0.5]


LONG_VIDEO = 40 * 60   # above this, fetch only the pieces that become clips
PAD = 8                # seconds kept either side of a fetched piece, so clips can be re-trimmed


def _piece_again(job, clip):
    """Remaking a clip whose own piece of the video was never fetched (its first try failed) and whose whole video
    is not here: fetch the piece now, cut exactly at the asked time, so no sound matching is needed."""
    src = job.get("source") or {}
    # A clip of a live recording whose stream pieces are gone can still be made once the stream is over: the
    # platform keeps the replay, and its clock is the recording's clock (measured on a six-hour stream: within
    # 0.03 s from start to end), so the same stretch is fetched from there.
    replay = src.get("type") == "live" and job.get("status") != "live"
    if (src.get("type") != "url" and not replay) or not src.get("url"):
        raise RuntimeError("The original video is no longer here, so this clip can't be made again. Add the video again.")
    d = Path(job["dir"])
    want = max(0.0, clip["start"] - PAD)
    until = clip["end"] + PAD if not job.get("duration") else min(job["duration"], clip["end"] + PAD)
    try:
        piece = media.download_section(src["url"], d / "clips", f"{clip['id']}.src", want, until,
                                       int(job["options"]["quality"]), exact=True)
        meta = media.probe(piece)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Could not fetch this part of the video: {safe.friendly(e, 250)}") from e
    clip.update(src=str(piece), src_offset=round(want, 2), src_end=round(want + meta["duration"], 2))
    clip["end"] = min(clip["end"], clip["src_end"])
    job.setdefault("width", meta["width"])
    job.setdefault("height", meta["height"])


def _fetch_piece(job, clip, full_audio):
    """Long videos: download just this clip's stretch and pin down exactly where it starts."""
    d = Path(job["dir"])
    o = job["options"]
    try:
        want = max(0.0, clip["start"] - PAD)
        piece = media.download_section(job["source"]["url"], d / "clips", f"{clip['id']}.src", want,
                                       min(job["duration"], clip["end"] + PAD), int(o["quality"]))
        wav = d / "clips" / f"{clip['id']}.wav"
        media.extract_audio(piece, wav)
        part = media.load_audio(wav)
        wav.unlink(missing_ok=True)
        meta = media.probe(piece)
        off = media.find_offset(full_audio, part, want)
        clip.update(src=str(piece), src_offset=round(off, 2), src_end=round(off + meta["duration"], 2))
        clip["start"], clip["end"] = max(clip["start"], clip["src_offset"]), min(clip["end"], clip["src_end"])
        job.setdefault("width", meta["width"])
        job.setdefault("height", meta["height"])
    except Exception as e:  # noqa: BLE001
        clip.update(status="error", error=f"Could not fetch this part of the video: {safe.friendly(e, 250)}")


BLOCK = 10 * 60         # long videos are transcribed and clipped one block at a time
PROGRESSIVE_FROM = 20 * 60


def _covers(words: list, start: float, end: float) -> bool:
    """Is a borrowed transcript good enough to find clips with? It has to reach the end of the part being clipped
    and have a normal amount of talking in it; otherwise our own model writes the transcript."""
    inside = [w for w in words if start <= w["s"] <= end]
    minutes = max(0.5, (end - start) / 60)
    return len(inside) >= 25 * minutes and inside[-1]["s"] >= start + 0.85 * (end - start)


def _facecam(job) -> list | None:
    """Where the webcam is in the source: once for the whole video, for every clip of it.

    Only a sure answer is used. A box that is a scoreboard drawn over the game would
    put a picture of a scoreboard in the corner of the clip. One frame is also shown to
    the AI, which tells a person from a game character better than any measurement can;
    what it says is measured again on the picture, so it cannot do any harm."""
    path = job.get("source_path")
    if not path or not Path(path).is_file():
        return None
    try:
        box = facecam.detect(path, ask=brain.look_for_facecam)
    except Exception:  # noqa: BLE001 - a missing facecam is not a failure
        return None
    if not box or box.get("conf") != "high":
        return None
    job["facecam"] = [box["x"], box["y"], box["w"], box["h"]]
    return job["facecam"]


def _moment_labels(job, audio, a: int, b: int, found: list, notes: list) -> None:
    """Say what kind of moment each picked clip is: a chase, a crash, a fight, a stunt, a reaction or a laugh.

    Only ever called when a job asks for it, and only for the part of the video the clips came from, so a
    normal job does no extra work. Nothing here can fail a clip: an unreadable part simply arrives unlabelled."""
    path = job.get("source_path") or ""
    t0 = a / 16000.0
    try:
        got = moments.analyse(audio=audio[a:b], path=path if path and Path(path).is_file() else None,
                              duration=(b - a) / 16000.0, t0=t0, seek=t0)
    except Exception as e:  # noqa: BLE001 - a label is a nicety, never a reason to lose a clip
        notes.append("The kind of moment could not be measured for one part: " + safe.friendly(e, 160))
        return
    spans = got.get("moments") or []
    if got.get("note"):
        notes.append(str(got["note"])[:160])
    if not spans:
        return
    for c in found:
        start, end = round(float(c["start"]) + t0, 2), round(float(c["end"]) + t0, 2)
        best, covered = "", 0.0
        for kind in moments.TYPES:
            got_s = moments.overlap(start, end, spans, kind)
            if got_s > covered:
                best, covered = kind, got_s
        if best and covered >= max(0.5, 0.15 * max(1.0, end - start)):
            c["moment"] = best
            c["moment_score"] = round(covered / max(1.0, end - start), 2)


UNMADE = "The video stopped before this clip was made."
HEAR_WAITS = (10, 30, 90)     # seconds before each new try of one part whose speech service hiccupped
_PASSING = ("timed out", "timeout", "handshake", "connection", "temporarily", "reset by peer", "unreachable",
            "502", "503", "504", "429", "ssl", "eof occurred", "remote end closed", "network")


def _passing(err) -> bool:
    """A network hiccup that is worth trying again (not a wrong key or a bad file)."""
    text = str(err).lower()
    return any(p in text for p in _PASSING)


def _hear_patiently(audio, on_progress=None):
    """One part of a video, heard. A speech service that times out once must not end a five-hour video: on the first
    whole-stream run one SSL handshake timeout at part 28 of 35 stopped everything and left 21 found clips unmade. A
    hiccup is tried again after 10, 30 and 90 seconds; anything else, or a fourth failure, is reported as before."""
    for wait in HEAR_WAITS + (None,):
        try:
            return transcribe.transcribe(audio, on_progress)
        except Exception as e:  # noqa: BLE001
            if wait is None or not _passing(e):
                raise
            time.sleep(wait)


def carry_on(jid) -> dict:
    """A video that failed part-way (the speech service or the AI went down) carries on from the last part it
    finished: the transcript, the clips and the AI answers it already has are kept, and the clips it had found but
    not made yet are made. Raises KeyError when it is not theirs, ValueError when there is nothing to carry on from."""
    job = get(jid)
    if not job:
        raise KeyError(jid)
    if job.get("status") != "error" or job.get("kind") == "live":
        raise ValueError("Only a video that stopped with an error can carry on.")
    if not (Path(job["dir"]) / "words.json").is_file():
        raise ValueError("It stopped before any of it was heard. Make it again instead.")
    for c in job.get("clips", []):
        if c.get("status") == "error" and c.get("error") == UNMADE:
            c.update(status="queued", error=None)
    # The person pressing Carry on is the signal that they fixed what was wrong (a VPN turned off, say), so YouTube is
    # tried at once instead of waiting out the pause a refusal starts.
    media._yt_refused_until = 0.0
    _set(job, status="queued", stage="Carrying on from where it stopped", error=None, resume=True, stop=False)
    _q.put(("job", jid, None), user=job["user"])
    return {"ok": True}


def stop(jid) -> dict:
    """The person pressed Stop on a video that is waiting or being made.

    A waiting video is simply not started. A running one stops looking for more moments at the next safe point
    (before the next part is judged); the clips it has already found are still finished, so nothing the person can
    already see is thrown away. Raises KeyError when the video is not theirs."""
    job = get(jid)
    if not job:
        raise KeyError(jid)
    if job.get("status") not in ("queued", "running"):
        return {"ok": True, "status": job.get("status")}
    if job.get("status") == "queued":
        _set(job, stop=True, resume=False, status="done", progress=1.0,
             stage="Stopped by you before it started" if not job.get("clips") else "Stopped by you")
    else:
        _set(job, stop=True, resume=False, stage="Stopping: finishing the part being read now")
    return {"ok": True, "status": job.get("status")}


def _run_job(job):
    import math
    from concurrent.futures import ThreadPoolExecutor
    if job.get("stop"):                  # Stop was pressed while it was still waiting its turn
        return
    d = Path(job["dir"])
    o = job["options"]
    src = job["source"]
    # Which game this is: what the creator set, or what the title says. It decides the extra rules the AI
    # reads and the tags every post carries.
    game = job.get("game") or ""
    if not game and job.get("creator"):
        try:
            game = (creators.get(job["creator"]) or {}).get("game") or ""
        except Exception:  # noqa: BLE001
            game = ""
    if not game:
        game = games.detect(job["title"], src.get("name"))[0] or ""
    if game and job.get("game") != game:
        job["game"] = game
    t0 = time.time()
    notes = []
    face = False       # where the webcam is in the source, found once; False means not looked for yet
    usage.set_context(job["creator"], job["title"] or src.get("name"))
    resuming = bool(job.pop("resume", False)) and (d / "words.json").is_file()
    if resuming:   # after a restart: keep the transcript parts, clips and AI answers already made, and carry on
        _set(job, status="running", stage="Picking up where it stopped", error=None)
    else:
        _set(job, status="running", stage="Getting the audio", progress=0.03, error=None, clips=[], ai={}, done_blocks=0)
    if not transcribe.cloud() and not transcribe.model_ready() and not transcribe.REMOTE:
        from . import fetch_model
        _set(job, stage="Getting the speech model (one time, about 480 MB)")
        fetch_model.ensure()
        _set(job, stage="Getting the audio")
    fetch = ThreadPoolExecutor(1)
    video = None
    if src["type"] == "url":
        meta = media.info(src["url"])
        if meta["kind"] != "video":
            raise RuntimeError("That link is a channel or playlist, not a single video. Paste the link of one video.")
        if ((o["range_end"] or meta["duration"]) - (o["range_start"] or 0)) > config.MAX_VIDEO_HOURS * 3600:
            raise RuntimeError(f"That is longer than {config.MAX_VIDEO_HOURS:g} hours. Choose a shorter part of it under Options.")
        if meta["is_live"]:
            raise RuntimeError("This link is a live stream, so it would never finish downloading. Open the creator, "
                               "put this link under Setup, and press Start recording instead.")
        _set(job, title=meta["title"], uploader=meta["uploader"], duration=meta["duration"])
        if not job.get("thumb") and media.save_thumb(d, url=src["url"]):
            _set(job, thumb=True)
        usage.set_context(job["creator"], meta["title"])
        span = (o["range_end"] or meta["duration"]) - (o["range_start"] or 0)
        pieces = span > LONG_VIDEO or meta["duration"] <= 0
        if not pieces:  # shorter video: fetch all of it in the background while the audio is worked on
            video = fetch.submit(media.download, src["url"], d, int(o["quality"]))
        audio_file = media.download_audio(src["url"], d, lambda p: _set(job, progress=0.03 + 0.1 * p))
    else:
        pieces, audio_file = False, Path(src["path"])
        info = media.probe(audio_file)
        if info["duration"] > config.MAX_VIDEO_HOURS * 3600:
            raise RuntimeError(f"That video is longer than {config.MAX_VIDEO_HOURS:g} hours, which is the limit.")
        _set(job, source_path=str(audio_file), width=info["width"], height=info["height"], duration=info["duration"])
        if not job.get("thumb") and media.save_thumb(d, video=audio_file):
            _set(job, thumb=True)
    wav = d / "audio.wav"
    media.extract_audio(audio_file, wav)
    audio = media.load_audio(wav)
    wav.unlink(missing_ok=True)
    if src["type"] == "url":
        audio_file.unlink(missing_ok=True)
    if not job["duration"]:
        job["duration"] = len(audio) / 16000
    lo = int((o["range_start"] or 0) * 16000)
    hi = min(len(audio), int(o["range_end"] * 16000)) if o["range_end"] else len(audio)
    span = (hi - lo) / 16000
    db = media.loudness_per_second(audio[lo:hi])

    vlock, vstate = threading.Lock(), {}

    def whole_video():
        """Wait for the background download once; retry it, or give up and use pieces."""
        with vlock:
            if "path" not in vstate:
                path = None
                try:
                    path = video.result()
                except Exception as e:  # noqa: BLE001 - sites sometimes refuse a download
                    notes.append(f"Video download refused once ({str(e)[-80:]}), retrying")
                    try:
                        path = media.download(src["url"], d, int(o["quality"]))
                    except Exception as e2:  # noqa: BLE001
                        notes.append(f"Whole-video download failed ({str(e2)[-80:]}), fetching clip parts instead")
                if path:
                    info = media.probe(path)
                    job.update(source_path=str(path), width=info["width"], height=info["height"])
                vstate["path"] = path
            return vstate["path"]

    exact = {}      # clip id -> (from, to, words): our own model's words for just that clip

    began = {}      # clip id -> when work on it started

    def make(clip, words_now):
        began[clip["id"]] = time.time()
        if src["type"] == "url" and (pieces or not whole_video()):
            _fetch_piece(job, clip, audio)
        if clip["status"] != "error" and clip.get("captions", True) and yt and yt[1].lower().startswith("en"):
            # The clip was found with YouTube's transcript. What is shown on screen comes from our own model,
            # run on just this clip: full punctuation, nothing blanked out, timings to the word.
            a0, b0 = max(lo, int((clip["start"] - 1.5) * 16000)), min(hi, int((clip["end"] + 1.5) * 16000))
            try:
                tw = [dict(w, s=round(w["s"] + a0 / 16000, 2), e=round(w["e"] + a0 / 16000, 2)) for w in transcribe.transcribe(audio[a0:b0])]
            except Exception:  # noqa: BLE001 - the clip is still made, with YouTube's words
                tw = []
            if len(tw) >= 3:
                exact[clip["id"]] = (a0 / 16000, b0 / 16000, tw)
                words_now = tw
        if clip["status"] != "error":
            render_one(job, clip, words_now)

    cpus = os.cpu_count() or 4
    renders = ThreadPoolExecutor(2 if cpus < 8 else min(6, cpus // 6))  # more clips made at once on a bigger machine
    futures = []
    step = BLOCK * 16000 if span > PROGRESSIVE_FROM else hi - lo
    blocks = [(x, min(hi, x + step)) for x in range(lo, hi, step)] or [(lo, hi)]
    _set(job, blocks_total=len(blocks))    # the page draws one mark per part, filled as each is written
    words, tokens, model = [], 0, None
    done_blocks = 0
    yt = None
    if src["type"] == "url" and config.YT_TRANSCRIPT and media.is_youtube(src["url"]):
        try:
            yt = media.youtube_words(src["url"])
        except Exception:  # noqa: BLE001 - no transcript to borrow: ours is written as usual
            yt = None
        if yt and not _covers(yt[0], lo / 16000, hi / 16000):
            yt = None
        job["transcript_from"] = "youtube" if yt else "own"
        job["lang"] = yt[1] if yt else ""          # the language spoken, when YouTube says (decides the captions)
    if resuming:
        try:
            words = json.loads((d / "words.json").read_text(encoding="utf-8"))
        except ValueError:
            words = []
        done_blocks = min(int(job.get("done_blocks", 0)), len(blocks)) if words else 0
        tokens, model = int((job.get("ai") or {}).get("tokens", 0)), (job.get("ai") or {}).get("model")
        if done_blocks < len(blocks):     # words past the last finished part are transcribed again
            cut = blocks[done_blocks][0] / 16000
            words = [w for w in words if w["s"] < cut]
        for c in job["clips"]:            # clips found before the restart that were not finished yet
            if c.get("status") not in ("done", "error"):
                c["status"] = "queued"
                futures.append((renders.submit(ctx.bind(make), c, list(words)), c))
        save(job)
    # The transcript of the next part is written while the AI is still reading this one (the AI is a wait on the
    # network, the transcript is work on this machine), so neither waits for the other.
    ahead = ThreadPoolExecutor(2, thread_name_prefix="ahead")
    heard, now_on = {}, [done_blocks]

    def hear(i):
        if i < len(blocks) and i >= done_blocks and i not in heard:
            a_, b_ = blocks[i]
            last = [0.0]

            def tp(p, i=i, a_=a_, b_=b_):
                if now_on[0] == i and p - last[0] > 0.05:      # only the part being shown moves the bar
                    last[0] = p
                    heard_now = (a_ + p * (b_ - a_)) / 16000   # the second of the video being listened to
                    _set(job, progress=max(job["progress"], 0.14 + 0.78 * ((a_ - lo) + p * (b_ - a_)) / max(1, hi - lo)),
                         heard_to=round(heard_now, 1))
            heard[i] = ahead.submit(ctx.bind(_hear_patiently), audio[a_:b_], tp)

    # The ad breaks and static screens of the whole video, found once. It reads the video end to end,
    # so it is done here rather than for each clip, and only when asked for.
    statics = quality.static_ranges(job.get("source_path") or "") if config.SKIP_STATIC else []
    try:
        sig = signals.youtube((job.get("source") or {}).get("url") or "")
    except Exception:
        sig = {}
    # Parts are judged a few at a time (`JUDGE_AHEAD`): the AI is a wait on the network, and one part at a time left
    # a 5 h 45 min stream at about 2.5 minutes a part. Their clips are still added in the order of the video, and a
    # part only counts as done (for a restart) once every part before it is done.
    judges = ThreadPoolExecutor(JUDGE_AHEAD, thread_name_prefix="judge")
    waiting = []          # (part, its start, its end, its shift, the judging) in the order of the video
    whose = usage.context()

    def _judge_block(*args, **kw):
        usage.set_context(*whose)
        return brain.find_clips(*args, **kw)

    def take(bi, a, b, shift, fut):
        nonlocal tokens, model, face
        if fut is None:
            job["done_blocks"] = bi + 1
            save(job)
            _set(job, blocks_done=max(bi + 1, int(job.get("blocks_done") or 0)))
            return
        found, ai = fut.result()
        tokens += ai.get("tokens", 0)
        model = ai.get("model") or model
        if ai.get("note"):
            notes.append(ai["note"])
        if found and statics:
            # A commercial or a "be right back" slate is not a clip. Any clip that sits mostly inside one
            # is dropped.
            keep = []
            for c in found:
                a_s, b_s = c["start"] + shift, c["end"] + shift
                inside = quality.static_overlap(a_s, b_s, statics)
                if inside > 0.5 * max(1.0, b_s - a_s):
                    notes.append(f"A clip from {round(a_s)}s was left out: it sat in an ad break or a static screen.")
                else:
                    keep.append(c)
            found = keep
        if found and o.get("moment_labels"):        # opt-in: what kind of moment each clip is
            _moment_labels(job, audio, a, b, found, notes)
        for c in found:
            c.update(id=f"clip{len(job['clips']) + 1:02d}", start=round(c["start"] + shift, 2),
                     end=round(c["end"] + shift, 2), style=o["style"], layout=o["layout"],
                     bg=o.get("bg", ""), captions=o.get("captions", True), censor=o.get("censor", False),
                     cleanup=o.get("cleanup", False), status="queued", version=0)
            # The sound chosen for the whole job dresses every clip of it, unless that clip was given its own.
            if o.get("sound") and not c.get("mood"):
                c["mood"] = o["sound"]
            # Only the gameplay layout uses a webcam, so it is only looked for then, and only once: a
            # stream with no webcam is not looked for again on every clip of it.
            if o["layout"] == "gameplay" and face is False:
                face = _facecam(job)
            if face:
                c["facecam"] = face
            job["clips"].append(c)
            futures.append((renders.submit(ctx.bind(make), c, list(words)), c))
        job["ai"] = {"model": model, "tokens": tokens, "note": "", "log": notes[-5:]}
        job["done_blocks"] = bi + 1       # a restart from here on carries on with the next part
        save(job)

    def take_ready(everything=False):
        while waiting and (everything or waiting[0][4] is None or waiting[0][4].done()):
            take(*waiting.pop(0))

    for bi, (a, b) in enumerate(blocks):
        if job.get("stop"):               # the person pressed Stop: no more parts are read
            break
        if bi < done_blocks:
            continue                      # transcribed and checked by the AI before the restart
        shift = a / 16000
        where = f" (minute {round((a - lo) / 16000 / 60)} of {round(span / 60)})" if len(blocks) > 1 else ""
        if yt:
            _set(job, stage="Reading the transcript" + where)
            bw = [dict(w, s=round(w["s"] - shift, 2), e=round(w["e"] - shift, 2)) for w in yt[0] if a / 16000 <= w["s"] < b / 16000]
        else:
            _set(job, stage="Writing the transcript" + where)
            now_on[0] = bi
            hear(bi)
            hear(bi + 1)
            bw = heard.pop(bi).result()
        _set(job, progress=max(job["progress"], 0.14 + 0.78 * (b - lo) / max(1, hi - lo)),
             heard_to=round((b - lo) / 16000 + lo / 16000, 1), blocks_done=bi + 1)
        words += [dict(w, s=round(w["s"] + shift, 2), e=round(w["e"] + shift, 2)) for w in bw]
        (d / "words.json").write_text(json.dumps(words), encoding="utf-8")
        if job.get("stop"):               # Stop was pressed while this part was being written: do not judge it
            break
        _set(job, stage="Finding the best moments" + where, word_count=len(words))
        # 0 means "as many good clips as there are": every block is judged and every strong find is kept, up to
        # ALL_CLIPS so one very long video cannot flood the page.
        left = (int(o["max_clips"]) or ALL_CLIPS) - len(job["clips"])
        if left <= 0 or len(bw) < 8:
            waiting.append((bi, a, b, shift, None))     # nothing to judge, but the parts are still finished in order
            take_ready()
            continue
        quota = max(1, math.ceil(left / (len(blocks) - bi)))
        s0 = int((a - lo) / 16000)
        fut = judges.submit(ctx.bind(_judge_block), bw, db[s0: s0 + int((b - a) / 16000) + 1], (b - a) / 16000, job["title"],
                                     job["uploader"], quota, int(o["min_len"]), int(o["max_len"]), notes.append, game=game,
                                     hook_words=_hook_words(job), min_score=o.get("min_score"),
                                     focus=((creators.get(job["creator"]) or {}).get("clip_focus") or "")
                                     if job.get("creator") else "",
                                     context_for=lambda s_, e_, _a=a: signals.brief(sig, _a / 16000 + s_, _a / 16000 + e_, shift=_a / 16000),
                                     memory=d / "story.json", whole=yt[0] if yt and span <= WHOLE_STORY_MAX else None, at=shift,
                                     source=lambda: job.get("source_path"), made=list(job["clips"]),
                                     creator=job.get("creator"))
        waiting.append((bi, a, b, shift, fut))
        while len(waiting) > JUDGE_AHEAD:               # never more than a few parts judged ahead of the oldest
            take(*waiting.pop(0))
        take_ready()
    take_ready(everything=True)
    if job.get("stop"):
        ahead.shutdown(wait=False, cancel_futures=True)     # the transcript of the next part is no longer needed
    if futures:
        _set(job, stage="Stopped by you: finishing the clips already found" if job.get("stop") else "Finishing the clips",
             progress=max(job["progress"], 0.92))
    _wait_for_clips(job, futures, began, renders._max_workers)
    if exact:           # keep our own words for the clips in the saved transcript, so editing a clip later uses them
        for a_s, b_s, tw in exact.values():
            words = [w for w in words if not a_s <= w["s"] < b_s] + tw
        words.sort(key=lambda w: w["s"])
        (d / "words.json").write_text(json.dumps(words), encoding="utf-8")
    renders.shutdown(wait=False)
    judges.shutdown(wait=False)
    ahead.shutdown(wait=False)
    fetch.shutdown(wait=False)
    del audio
    clips = job["clips"]
    job["ai"] = {"model": model, "tokens": tokens, "log": notes[-5:],
                 "note": "The AI was unavailable, so clips were picked by loudness only." if clips and not model else ""}
    stage = "Done" if clips else "Done, but nothing clip-worthy was found"
    if job.get("stop"):
        stage = f"Stopped by you with {len(clips)} clip{'s' if len(clips) != 1 else ''}"
    _set(job, status="done", stage=stage, progress=1.0, took=round(time.time() - t0))
    try:
        from . import notices
        name = job.get("title") or job["source"].get("name") or "your video"
        notices.add(job.get("user"), "clips", f"{len(clips)} clip{'s' if len(clips) != 1 else ''} ready" if clips else "Nothing clip-worthy found",
                    name, f"/app/creators/{job['creator']}" if job.get("creator") else "/app/videos")
    except Exception:  # noqa: BLE001
        pass
    creators.log(job["creator"], f"Video finished with {len(clips)} clips in {round(time.time() - t0)}s: {job['title']}")


def _worker(quick_only=False):
    while True:
        kind, a, cid = _q.get(quick_only)
        if kind == "fn":
            try:
                a()
            except Exception:  # noqa: BLE001
                traceback.print_exc()
            continue
        job = _jobs.get(a)
        if not job:
            if kind == "job":
                _q.done()
            continue
        token = ctx._uid.set(job["user"])  # everything this job does runs as its owner
        try:
            if kind == "job":
                _run_job(job)
            else:
                clip = next(c for c in job["clips"] if c["id"] == cid)
                words = []
                if clip.get("captions", True):
                    words = json.loads((Path(job["dir"]) / "words.json").read_text(encoding="utf-8"))
                render_one(job, clip, words)
        except Exception as e:  # noqa: BLE001
            (Path(job["dir"]) / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
            if kind == "job":
                for c in job["clips"]:
                    if c.get("status") in ("queued", "rendering"):
                        c.update(status="error", error=UNMADE)
                _set(job, status="error", error=safe.friendly(e), stage="Stopped")
                creators.log(job["creator"], f"Video failed: {safe.friendly(e)[:200]}")
        finally:
            ctx._uid.reset(token)
            if kind == "job":
                _q.done()


def _pick_up_after_restart():
    """Videos and single clips that were being made when the server stopped: queued again, oldest first."""
    waiting = sorted((j for j in all_jobs() if j.get("status") == "queued" and j.get("resume")), key=lambda j: j["created"])
    for j in waiting:
        _q.put(("job", j["id"], None), user=j["user"])
    for j in all_jobs():
        for cid in j.pop("remake", []):
            _q.put(("clip", j["id"], cid))
        if j.get("status") == "done":
            save(j)


def start():
    load.start()
    load_all()
    _pick_up_after_restart()
    for _ in range(max(1, config.JOB_WORKERS)):
        threading.Thread(target=_worker, daemon=True).start()
    threading.Thread(target=_worker, args=(True,), daemon=True).start()   # re-making a single clip never waits behind whole videos
    threading.Thread(target=_live_worker, daemon=True).start()
