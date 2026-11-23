"""Joins several moments of one video into one Short: a countdown, a Strike 1-2-3 run, a Then vs Now, or a Callback.

`studio/formats.py` plans the shape (which parts, which numbered cards, which badges) and `studio/format_finish.py`
draws the cards. This file does the real work around them:

  1. `choose`    picks the moments: the ones a person ticked, or the best-scoring clips of the video.
  2. `fit`       makes them fit the creator's longest clip length, and works out the plan.
  3. `make`      renders every moment as its own clip (so each one has its own layout, webcam and captions, and goes
                 through exactly the same cut as any other clip), then joins them with a short numbered card and a
                 flash between, and writes one file.

THE ONE RULE THAT MATTERS: picture and sound must stay in step. Nothing here cuts a source with `ffmpeg -ss` of its
own. Every moment goes through `render.render_clip`, which opens the input early and trims both tracks at one
timestamp, and the join then trims each finished part to the length it really has (the shorter of its picture and
its sound) before the parts are put end to end. The finished file is measured with `render.av_gap` and refused if
picture and sound have drifted apart.

Nothing here talks to the network except fetching a moment out of a video that is no longer on this computer (the
same fetch `jobs._piece_again` makes), and nothing here asks an AI anything: captions are the words already heard.
It never changes a clip or a job; it only writes the montage files it is told to."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from . import config, format_finish, formats, media, render, roman, safe

PAD = 8.0                      # seconds either side of a moment that is fetched again, like jobs.PAD
GAP_LIMIT = 0.06               # a finished montage whose picture and sound differ by more than this is refused
DEFAULT_HEADINGS = {           # what the first card says when the person wrote no heading
    "compilation": "TOP {n} MOMENTS",
    "escalation": "IT KEEPS GETTING WORSE",
    "thenvsnow": "WHAT HE SAID VS WHAT HAPPENED",
}
DEFAULT_WORD = {"escalation": "STRIKE"}


class MontageError(ValueError):
    """A montage that cannot be made, in words a person can act on."""


# ---------------------------------------------------------------- small readers
def _num(value, default=None):
    return formats._num(value, default)


def _usable(clip) -> bool:
    a, b = _num(clip.get("start")), _num(clip.get("end"))
    return isinstance(clip, dict) and a is not None and b is not None and b > a and bool(clip.get("id"))


def _short(text, limit=formats.MAX_LABEL) -> str:
    """A moment's hook, as a card label: upper case, plain, cut at a whole word."""
    t = formats.clean_text(text).strip()
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0]
    return (cut or t[:limit]).strip()


def _overlap(a: dict, b: dict) -> float:
    inter = min(a["end"], b["end"]) - max(a["start"], b["start"])
    return max(0.0, inter) / max(0.1, min(a["end"] - a["start"], b["end"] - b["start"]))


# ---------------------------------------------------------------- 1. which moments
def _moment(clip: dict) -> dict:
    return {"id": str(clip["id"]), "start": float(clip["start"]), "end": float(clip["end"]),
            "score": float(_num(clip.get("score"), 0.0)), "hook": str(clip.get("hook") or ""), "clip": clip}


def choose(job: dict, fmt: str, ids=None, count=None) -> list:
    """The moments of a montage, in the order they will play.

    `ids` are the clips a person ticked; without them the best-scoring clips of the video are taken, never two that
    overlap. A countdown plays worst to best (best last); the other shapes play in the order things happened."""
    if fmt not in formats.MONTAGE_RULES:
        raise MontageError(f"{fmt!r} is not a montage type. Types: {', '.join(formats.JOINS)}.")
    low, high = formats.MONTAGE_RULES[fmt]
    label = formats.FORMATS[fmt]["label"]
    clips = [c for c in (job.get("clips") or []) if isinstance(c, dict) and _usable(c)]
    want = f"{low}" if low == high else f"{low} to {high}"
    if ids:
        by_id = {str(c["id"]): c for c in clips}
        picked, seen = [], set()
        for cid in ids:
            cid = str(cid)
            if cid in seen:
                continue
            seen.add(cid)
            if cid not in by_id:
                raise MontageError(f"This video has no clip called {cid}.")
            picked.append(_moment(by_id[cid]))
        if not low <= len(picked) <= high:
            raise MontageError(f"A {label} takes {want} moments, and {len(picked)} were chosen.")
    else:
        n = int(count) if count else low
        n = max(low, min(high, n))
        ranked = sorted((_moment(c) for c in clips if c.get("status") != "error"),
                        key=lambda m: (-m["score"], m["start"]))
        picked = []
        for m in ranked:
            if all(_overlap(m, p) < 0.3 for p in picked):
                picked.append(m)
            if len(picked) == n:
                break
        if len(picked) < low:
            raise MontageError(f"This video has only {len(picked)} separate clip{'s' if len(picked) != 1 else ''}, "
                               f"and a {label} needs at least {low}.")
    if fmt == "compilation":
        picked.sort(key=lambda m: (m["score"], m["start"]))          # best last
    else:
        picked.sort(key=lambda m: m["start"])                       # the order it happened in
    return picked


# ---------------------------------------------------------------- where each moment's picture comes from
def _source_kind(job: dict, clip: dict) -> str:
    """"file" when the picture is on this computer, "download" when it has to be fetched again, or a MontageError
    that says why neither works. Cheap: it looks at the disk and the job, it fetches nothing."""
    p = clip.get("src")
    if p and Path(p).is_file():
        return "file"
    sp = job.get("source_path")
    if sp and Path(sp).is_file():
        return "file"
    src = job.get("source") or {}
    if src.get("type") == "live" and job.get("status") == "live":
        raise MontageError("This moment's piece of the stream is not saved any more, and the stream is still going. "
                           "Make the montage once the stream has ended.")
    replay = src.get("type") == "live"
    if (src.get("type") != "url" and not replay) or not src.get("url"):
        raise MontageError("The original video is no longer here, so this montage can't be made. Add the video again.")
    return "download"


def _resolve(job: dict, m: dict, work: Path, k: int) -> tuple:
    """(the video file, the video-time of that file's second zero) for one moment."""
    clip = m["clip"]
    kind = _source_kind(job, clip)
    if kind == "file":
        p = clip.get("src")
        if p and Path(p).is_file():
            return Path(p), float(clip.get("src_offset") or 0.0)
        return Path(job["source_path"]), 0.0
    # Fetched again: the same cut jobs._piece_again makes (exact, so no matching is needed), into the montage's own
    # work folder, so the clip's own folder is never touched.
    want = max(0.0, m["start"] - PAD)
    until = m["end"] + PAD
    if job.get("duration"):
        until = min(float(job["duration"]), until)
    try:
        piece = media.download_section((job.get("source") or {})["url"], work / "dl", f"m{k}", want, until,
                                       int((job.get("options") or {}).get("quality") or 1080), exact=True)
    except Exception as e:  # noqa: BLE001
        raise MontageError(f"Could not fetch this part of the video: {safe.friendly(e, 250)}") from e
    return Path(piece), round(want, 2)


def _job_words(job: dict) -> list:
    got = job.get("words")
    if not got and job.get("dir"):
        f = Path(job["dir"]) / "words.json"
        try:
            got = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else []
        except (OSError, ValueError):
            got = []
    return [w for w in (got or []) if isinstance(w, dict) and w.get("w") and _num(w.get("s")) is not None]


def _words_for(job_words: list, clip: dict, start: float, end: float, off: float) -> list:
    """The words heard in this moment, in the file's own time. The clip's own tidied words come first (they are what
    its finished clip was captioned from), then the video's transcript. No AI is asked."""
    own = [w for w in (clip.get("fixed_words") or []) if isinstance(w, dict) and w.get("w") and _num(w.get("s")) is not None]
    pool = own if any(start - 1 <= float(w["s"]) <= end + 1 for w in own) else job_words
    near = [w for w in pool if start - 1 <= float(w["s"]) <= end + 1]
    near = roman.words(near)
    return [dict(w, s=float(w["s"]) - off, e=float(_num(w.get("e"), float(w["s"]) + 0.3)) - off) for w in near]


# ---------------------------------------------------------------- 2. the plan, fitted to the length
def _pick_for(fmt: str, moments: list, hook: str, layout: str, word: str, labels) -> dict:
    parts = [{"start": round(m["start"], 2), "end": round(m["end"], 2), "label": _short(m["hook"])} for m in moments]
    pick = {"format": fmt, "start": min(p["start"] for p in parts), "end": max(p["end"] for p in parts),
            "layout": layout, "hook": hook, "parts": parts,
            "jump_card": True}                # a callback says LATER on a card between the two moments
    if fmt == "escalation":
        pick["word"] = word or DEFAULT_WORD["escalation"]
    if fmt == "thenvsnow" and labels:
        pick["labels"] = list(labels)
    return pick


def _card_seconds(plan: dict) -> float:
    return sum(float(c.get("dur") or 0.0) for c in plan.get("cards") or [])


def fit(job: dict, fmt: str, moments: list, hook: str = "", layout: str = "", word: str = "", labels=None,
        max_len=None) -> dict:
    """Shortens the moments until the whole montage fits the creator's longest clip length, and plans it.

    Every moment loses its start (a moment's payoff is late), never below `formats.MIN_PART` seconds. When even that
    is too long for the shape's fewest moments, the person is told to raise the length instead of getting a clip
    that is cut to nothing. Returns {"moments", "pick", "plan", "layout", "hook", "budget"}."""
    opts = job.get("options") or {}
    budget = float(max_len or opts.get("max_len") or 60)
    budget = max(formats.MIN_TOTAL, min(budget, formats.MAX_TOTAL))
    layout = layout if layout in render.LAYOUTS else (opts.get("layout") if opts.get("layout") in render.LAYOUTS else "blur")
    low = formats.MONTAGE_RULES[fmt][0]
    moments = [dict(m) for m in moments]
    hook = formats._clean(hook)[:60]
    for _turn in range(20):
        n = len(moments)
        heading = hook or DEFAULT_HEADINGS.get(fmt, "").format(n=n) or (
            _short(max(moments, key=lambda m: m["score"])["hook"], 40) if fmt == "callback" else "")
        pick = _pick_for(fmt, moments, heading, layout, word, labels)
        plan = formats.plan(pick, None)
        if not plan["ok"]:
            raise MontageError(plan["error"] or "This montage could not be planned.")
        room = budget - _card_seconds(plan)
        lengths = [m["end"] - m["start"] for m in moments]
        if sum(lengths) <= room + 0.01:
            break
        if n * formats.MIN_PART > room:
            if n > low:                                    # drop the weakest moment and try again
                moments.remove(min(moments, key=lambda m: m["score"]))
                continue
            raise MontageError(f"{n} moments do not fit in {budget:.0f} seconds. Raise the longest clip length to at "
                               f"least {n * formats.MIN_PART + _card_seconds(plan):.0f} seconds, or choose fewer.")
        # Share the time out in proportion, never giving a moment less than the minimum, and give back what a
        # short moment did not need to the longer ones.
        shares = _shares(lengths, room)
        for m, take in zip(moments, shares):
            m["start"] = round(m["end"] - take, 2)
        # the plan is made again on the next turn, with the new lengths, and must come out within `room` now
    else:
        raise MontageError("These moments could not be fitted into the longest clip length. Raise it, or choose fewer.")
    return {"moments": moments, "pick": pick, "plan": plan, "layout": layout, "hook": heading, "budget": budget}


def _shares(lengths: list, room: float) -> list:
    """How long each moment may be when `room` seconds are shared out: nobody below MIN_PART, nobody above what they
    have, the rest split in proportion. Totals `room` (to the centisecond) whenever everything cannot fit."""
    low = formats.MIN_PART
    out = [min(x, max(low, x * room / sum(lengths))) for x in lengths]
    for _ in range(6):                                      # a few rounds settle every rounding and floor
        extra = sum(out) - room
        if extra <= 0.005:
            break
        free = [i for i, x in enumerate(out) if x > low + 0.01]
        if not free:
            break
        cut = extra / len(free)
        for i in free:
            out[i] = max(low, out[i] - cut)
    # floored to the centisecond, so the rounded plan can never come out longer than the room it was given
    return [max(low, math.floor(x * 100) / 100) if x < lengths[i] else x for i, x in enumerate(out)]


# ---------------------------------------------------------------- 3. render and join
def _durations(path: Path) -> tuple:
    """(picture seconds, sound seconds) of a finished file, 0 for a missing track."""
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json",
                            str(path)], capture_output=True, text=True, timeout=60, creationflags=media.NO_WINDOW)
        s = {x["codec_type"]: float(x.get("duration") or 0) for x in json.loads(p.stdout or "{}").get("streams", [])}
        return s.get("video", 0.0), s.get("audio", 0.0)
    except Exception:  # noqa: BLE001
        return 0.0, 0.0


def _face(job: dict, clip: dict, src: Path):
    """The webcam's box for a clip that needs one (stack and gameplay layouts), or None."""
    for known in (clip.get("facecam"), job.get("facecam")):
        if known and len(known) == 4 and int(known[2]) > 8:
            return [int(v) for v in known]
    try:
        from . import jobs
        return jobs._webcam_in(dict(job), src)      # a copy, so finding it never writes onto the job
    except Exception:  # noqa: BLE001 - no webcam is a layout, never a failed montage
        return None


def _render_part(job, m, span, k, work, brand, layout, style, job_words, notes) -> Path:
    clip = m["clip"]
    src, off = _resolve(job, m, work, k)
    meta = media.probe(src)
    start, end = float(span["start"]), float(span["end"])
    lo = float(clip.get("src_offset") or 0.0) if clip.get("src") and Path(clip["src"]).is_file() else off
    hi = off + meta["duration"]
    start, end = max(start, lo), min(end, hi)
    if end - start < 1.0:
        raise MontageError(f"Moment {k + 1} ({m['id']}) is outside the video that is saved.")
    face = _face(job, clip, src) if span["layout"] in ("stack", "gameplay") else None
    if span["layout"] in ("stack", "gameplay") and not face:
        notes.append(f"No webcam was found for moment {k + 1}, so it fills the screen.")
    local = dict(clip, start=start - off, end=end - off, layout=span["layout"], style=style, facecam=face,
                 hook=roman.to_roman(span.get("hook") or ""), captions=True)
    words = _words_for(job_words, clip, start, end, off)
    made = render.render_clip(src, work / "p", f"p{k}", local, words, meta["width"], meta["height"],
                              brand=brand)
    # how many caption lines this part got: the proof that every part has words on it
    try:
        ass = (work / "p" / f"p{k}.ass").read_text(encoding="utf-8")
        said = sum(1 for ln in ass.splitlines() if ln.startswith("Dialogue:") and ",Hook," not in ln)
    except OSError:
        said = 0
    return work / "p" / made["file"], said, bool(words)


def _join(work: Path, parts: list, plan: dict, name: str, lengths: list) -> dict:
    """Puts the finished parts end to end with the cards, one flash per join, and writes <name>.mp4 in `work`."""
    fps = config.OUT_FPS
    cmd, graph, timeline, labels, t = ["ffmpeg", "-y", "-v", "error"], [], [], [], 0.0
    idx = 0
    for k, span in enumerate(plan["spans"]):
        card = next((c for c in span.get("chips") or [] if c["kind"] == "card"), None)
        if card:
            d = float(card["dur"])
            cmd += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", f"color=c=black:s={formats.W}x{formats.H}:r={fps}",
                    "-f", "lavfi", "-t", f"{d:.3f}", "-i", "anoisesrc=r=48000:c=pink:a=0.22"]
            graph.append(f"[{idx}:v]fps={fps},trim=duration={d:.3f},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{len(labels)}];"
                         f"[{idx + 1}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                         f"highpass=f=300,lowpass=f=7000,afade=t=in:st=0:d={d * 0.4:.3f},"
                         f"afade=t=out:st={d * 0.4:.3f}:d={d * 0.6:.3f},atrim=duration={d:.3f},asetpts=PTS-STARTPTS[a{len(labels)}]")
            labels.append(len(labels))
            timeline.append({"kind": "card", "t0": t, "t1": t + d, "lines": card["lines"]})
            t += d
            idx += 2
        d = float(lengths[k])
        cmd += ["-i", str(parts[k].relative_to(work)).replace("\\", "/")]
        graph.append(f"[{idx}:v]fps={fps},scale={formats.W}:{formats.H},setsar=1,format=yuv420p,"
                     f"trim=duration={d:.3f},setpts=PTS-STARTPTS[v{len(labels)}];"
                     f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"atrim=duration={d:.3f},asetpts=PTS-STARTPTS[a{len(labels)}]")
        labels.append(len(labels))
        chips = [dict(c) for c in span.get("chips") or [] if c["kind"] in ("tag", "badge")]
        if span.get("hook"):
            # the heading sits where a badge would: the badge moves up, above it, like jobs.render_one does
            for c in chips:
                c.update(y=124, size=min(int(c.get("size") or 80), 60))
        timeline.append({"kind": "part", "t0": t, "t1": t + d, "chips": chips})
        t += d
        idx += 1
    (work / "montage.ass").write_text(format_finish.build_join_ass(timeline), encoding="utf-8")
    joined = "".join(f"[v{i}][a{i}]" for i in labels)
    graph.append(f"{joined}concat=n={len(labels)}:v=1:a=1[cv][a];[cv]ass=montage.ass:fontsdir=f[v]")
    cmd += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]", "-t", f"{t:.3f}",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-profile:v", "high", "-level", "4.2",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
            f"{name}.mp4"]
    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=media.NO_WINDOW, timeout=render.RENDER_SECONDS)
    if p.returncode != 0 or not (work / f"{name}.mp4").is_file():
        raise MontageError("The montage could not be joined: " + (p.stderr or "")[-300:].strip())
    first_part = next(seg for seg in timeline if seg["kind"] == "part")
    media.run(["ffmpeg", "-y", "-v", "error", "-i", f"{name}.mp4", "-ss", f"{first_part['t0'] + 1.0:.2f}",
               "-frames:v", "1", "-q:v", "3", f"{name}.jpg"], cwd=str(work))
    return {"length": t, "timeline": timeline}


def prepare(job: dict, fmt: str, ids=None, count=None, hook: str = "", layout: str = "", word: str = "", labels=None,
            max_len=None) -> dict:
    """Everything that can be decided without rendering: which moments, whether their pictures are there, how long
    each one will be, and the plan. This is what a page asks for to say "yes, that will work" (or why not) at once."""
    moments = choose(job, fmt, ids, count)
    for m in moments:
        _source_kind(job, m["clip"])                    # a missing source is said now, before any rendering
    return fit(job, fmt, moments, hook, layout, word, labels, max_len)


def make(job: dict, fmt: str, out_dir, name: str, ids=None, count=None, hook: str = "", layout: str = "",
         style: str = "", word: str = "", labels=None, max_len=None, brand=None, report=None) -> dict:
    """Makes one montage and writes <name>.mp4 and <name>.jpg into `out_dir`. Raises MontageError with a sentence.

    `job` is only read: its clips are never changed. `report(text)` is told what is happening, if given."""
    say = report or (lambda _t: None)
    fitted = prepare(job, fmt, ids, count, hook, layout, word, labels, max_len)
    plan, moments, layout = fitted["plan"], fitted["moments"], fitted["layout"]
    style = style or max(moments, key=lambda m: m["score"])["clip"].get("style") or (job.get("options") or {}).get("style") or "bounce"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    work = render._workdir()
    notes, captions, heard = [], [], []
    try:
        (work / "f").mkdir()
        for f in config.FONTS_DIR.glob("*.ttf"):
            shutil.copyfile(f, work / "f" / f.name)
        job_words = _job_words(job)
        parts, lengths = [], []
        for k, (m, span) in enumerate(zip(moments, plan["spans"])):
            say(f"Making moment {k + 1} of {len(moments)}")
            path, said, any_words = _render_part(job, m, span, k, work, brand, layout, style, job_words, notes)
            v, a = _durations(path)
            real = min(x for x in (v, a) if x > 0) if (v > 0 or a > 0) else 0.0
            if real < 1.0:
                raise MontageError(f"Moment {k + 1} came out empty.")
            parts.append(path)
            lengths.append(real)
            captions.append(said)
            heard.append(any_words)
        say("Joining the moments")
        joined = _join(work, parts, plan, name, lengths)
        gap = render.av_gap(work / f"{name}.mp4")
        if gap >= GAP_LIMIT:
            raise MontageError(f"The montage's sound is out of step with its picture by {gap:.2f} s, so it was not kept.")
        shutil.move(str(work / f"{name}.mp4"), str(out_dir / f"{name}.mp4"))
        if (work / f"{name}.jpg").is_file():
            shutil.move(str(work / f"{name}.jpg"), str(out_dir / f"{name}.jpg"))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if not any(heard):
        notes.append("No words were heard in these moments, so the parts have no captions.")
    return {"file": f"{name}.mp4", "cover": f"{name}.jpg", "format": fmt, "layout": layout,
            "length": round(joined["length"], 2), "gap": round(gap, 3), "parts": [m["id"] for m in moments],
            "part_lengths": [round(x, 2) for x in lengths], "captions": captions,
            "cards": [c["text"] for c in plan["cards"]], "hook": fitted["hook"], "timeline": joined["timeline"],
            "notes": notes}
