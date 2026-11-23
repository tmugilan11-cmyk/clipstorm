"""Montages: several moments of one video joined into one Short, with picture and sound still in step.

Everything here is made by ffmpeg on the spot (no network, no AI, nothing from the owner's data folder). The test
video changes colour every five seconds (green, blue, red, green...), has a short beep at the start of every second, and a keyframe only
every four seconds, so every moment starts BETWEEN keyframes, which is exactly what used to put the voice ahead of the
lips. The same picture is made twice, once as .mp4 and once as an MPEG-TS piece whose own clock starts at 1.4 s (a
live recording), so both kinds of source are checked.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = tempfile.mkdtemp(prefix="pcmont")
os.environ["PEAKCUT_DATA"] = DATA                      # a throwaway data folder: nothing real is touched
os.environ.setdefault("PEAKCUT_JUDGE_WEB", "0")

from studio import formats, montage, render                      # noqa: E402

render.install_fonts()

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


COLOUR = ("r='255*lt(mod(floor(T/5),3),1)'", "g='255*eq(mod(floor(T/5),3),1)'", "b='255*eq(mod(floor(T/5),3),2)'")
# floor(T/5) mod 3: 0 = RED, 1 = GREEN, 2 = BLUE   (0-5 s red, 5-10 green, 10-15 blue, 15-20 red ...)


def make_source(path: Path, ts: bool):
    """A 40 s test video: colour by time, a beep every second, a keyframe only every 4 s."""
    vf = "format=gbrp,geq=" + ":".join(COLOUR) + ",format=yuv420p"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=s=640x360:r=30:d=40",
           "-f", "lavfi", "-i", "aevalsrc='0.8*sin(2*PI*880*t)*lt(mod(t,1),0.1)':s=48000:d=40",
           "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "ultrafast", "-g", "120", "-keyint_min", "120", "-sc_threshold", "0",
           "-c:a", "aac"]
    cmd += (["-output_ts_offset", "1.4", "-f", "mpegts"] if ts else ["-movflags", "+faststart"])
    subprocess.run(cmd + [str(path)], check=True)


def colour_at(path, t) -> str:
    """"R", "G" or "B": the colour in the middle of the picture at second t of `path`."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ss", f"{t:.3f}", "-frames:v", "1",
                          "-vf", "crop=20:20:530:950,scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    if len(raw) < 3:
        return "?"
    r, g, b = raw[0], raw[1], raw[2]
    if max(r, g, b) < 120:
        return "K"                                      # dark: a card
    return "RGB"[(r, g, b).index(max(r, g, b))]


def frame_stats(path, t):
    """(average brightness 0-255, number of bright pixels) of the frame at t, on a 108x192 copy."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ss", f"{t:.3f}", "-frames:v", "1",
                          "-vf", "scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return (sum(raw) / max(1, len(raw)), sum(1 for v in raw if v > 200))


def probe(path):
    import json
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,duration",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    s = {x["codec_type"]: x for x in json.loads(out)["streams"]}
    return s


WORDS = [{"w": w, "s": 1.0 + i * 0.5, "e": 1.3 + i * 0.5} for i, w in enumerate(
    "this is the first thing he said then nothing happened and later it did happen again really loud now".split() * 3)]


def words_at(offset):
    """Words everywhere in the 40 s, in video time (the file starts at `offset`)."""
    return [dict(w, s=w["s"] + offset, e=w["e"] + offset) for w in WORDS]


def job_for(src: Path, ts: bool, offset: float, clips_spec):
    clips = []
    for cid, a, b, score in clips_spec:
        c = {"id": cid, "start": a + offset, "end": b + offset, "score": score, "hook": f"HOOK {cid.upper()}",
             "style": "bounce", "layout": "crop", "status": "done"}
        if ts:
            c.update(src=str(src), src_offset=offset, src_end=offset + 40)
        clips.append(c)
    job = {"id": "j1", "user": "u1", "dir": str(Path(DATA) / "job"), "width": 640, "height": 360, "duration": 40 + offset,
           "options": {"max_len": 60, "quality": 1080, "layout": "blur", "style": "bounce"},
           "source": {"type": "live" if ts else "upload"}, "status": "done", "clips": clips,
           "words": words_at(offset)}
    if not ts:
        job["source_path"] = str(src)
    return job


SPEC = [("a", 5.3, 10.3, 50), ("b", 10.7, 14.9, 90), ("c", 15.7, 19.9, 70)]      # green, blue, red


def colour_change_and_beep(path, t0, t1):
    """Inside one finished part: when the picture goes from green to blue, and when the beep nearest to it starts."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}",
                          "-vf", "fps=30,crop=20:20:530:950,scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    change = None
    for i in range(0, len(raw) - 2, 3):
        if raw[i + 2] > raw[i + 1] + 60:                     # blue has taken over from green
            change = i // 3 / 30.0
            break
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}",
                          "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    import array
    a = array.array("h")
    a.frombytes(pcm[: len(pcm) // 2 * 2])
    onsets, quiet = [], True
    for i in range(0, len(a) - 80, 80):                     # 10 ms windows
        loud = max(abs(x) for x in a[i:i + 80]) > 3000
        if loud and quiet:
            onsets.append(i / 8000.0)
        quiet = not loud
    near = min(onsets, key=lambda o: abs(o - change)) if onsets and change is not None else None
    return change, near


def sample_parts(path, timeline):
    return "".join(colour_at(path, (s["t0"] + s["t1"]) / 2) for s in timeline if s["kind"] == "part")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="pcm"))
    mp4, ts = tmp / "video.mp4", tmp / "piece.ts"
    make_source(mp4, False)
    make_source(ts, True)

    # ---------------------------------------------------------------- the catalogue tells the truth
    rows = {r["id"]: r for r in formats.public()}
    check("the four joining types are now offered as montages",
          all(rows[k]["state"] == "montage" and rows[k]["available"] and rows[k]["max_parts"] >= 2 for k in formats.JOINS))
    check("chat says honestly that the lines are typed", rows["chat"]["state"] == "needs_lines" and "type the lines" in rows["chat"]["reason"])

    # ---------------------------------------------------------------- choosing
    job = job_for(mp4, False, 0.0, SPEC)
    best = montage.choose(job, "compilation")
    check("the best three are taken, a countdown plays worst to best", [m["id"] for m in best] == ["a", "c", "b"], [m["id"] for m in best])
    check("the other shapes play in the order things happened", [m["id"] for m in montage.choose(job, "escalation")] == ["a", "b", "c"])
    check("two best moments for a callback are the two highest scores, in time order",
          [m["id"] for m in montage.choose(job, "callback")] == ["b", "c"])
    try:
        montage.choose(job, "compilation", ids=["a", "b"])
        check("a countdown of two ticked moments is refused", False)
    except montage.MontageError as e:
        check("a countdown of two ticked moments is refused with a sentence", "3 to 5" in str(e), e)
    try:
        montage.choose(job, "compilation", ids=["a", "b", "zzz"])
        check("an unknown clip is refused", False)
    except montage.MontageError as e:
        check("an unknown clip is refused with its name", "zzz" in str(e), e)
    twin = job_for(mp4, False, 0.0, SPEC + [("d", 5.5, 9.9, 99)])
    got = [m["id"] for m in montage.choose(twin, "compilation")]
    check("overlapping clips are not both used", not ("a" in got and "d" in got), got)

    # ---------------------------------------------------------------- a missing source
    gone = job_for(mp4, False, 0.0, SPEC)
    gone.pop("source_path")
    try:
        montage.make(gone, "compilation", tmp / "x", "x")
        check("a missing source is refused", False)
    except montage.MontageError as e:
        check("a missing source is refused with a clear sentence", "no longer here" in str(e), e)
    live_gone = job_for(mp4, False, 0.0, SPEC)
    live_gone.pop("source_path")
    live_gone.update(source={"type": "live", "url": "https://example.invalid/x"}, status="live")
    try:
        montage.make(live_gone, "compilation", tmp / "x", "x")
        check("a live stream whose pieces are gone is refused", False)
    except montage.MontageError as e:
        check("a live stream whose pieces are gone says to wait until it ends", "once the stream has ended" in str(e), e)

    # ---------------------------------------------------------------- a countdown from an .mp4
    out = tmp / "out"
    said = []
    r = montage.make(job, "compilation", out, "count", ids=["a", "b", "c"], report=said.append)
    f = out / r["file"]
    check("a countdown is written", f.is_file() and (out / r["cover"]).is_file())
    check("parts play worst to best (green, red, blue)", sample_parts(f, r["timeline"]) == "GRB", sample_parts(f, r["timeline"]))
    check("the cards count down #3 #2 #1", r["cards"] == ["#3", "#2", "#1"], r["cards"])
    s = probe(f)
    dur = float(s["video"]["duration"])
    check("the picture is a full 1080x1920 frame", (s["video"]["width"], s["video"]["height"]) == (1080, 1920))
    want = sum(r["part_lengths"]) + 0.9 + 0.6 + 0.6
    check("total length is the parts plus the cards", abs(dur - want) < 0.15 and abs(r["length"] - want) < 0.05, (dur, want))
    check("total length is within the creator's longest clip", dur <= 60)
    check("with room to spare the parts keep their own lengths", all(abs(x - y) < 0.2 for x, y in zip(r["part_lengths"], [5.0, 4.2, 4.2])), r["part_lengths"])
    card = r["timeline"][0]
    avg, bright = frame_stats(f, card["t0"] + 0.45)
    ref = r["timeline"][1]
    avg_part, _ = frame_stats(f, (ref["t0"] + ref["t1"]) / 2)
    check("the first card is dark with bright number and heading text", card["kind"] == "card" and avg < 30 and bright > 150, (avg, bright))
    check("the card is a real card, not the picture", avg_part > 2 * avg + 10, (avg, avg_part))
    check("every part has captions on it", all(n > 0 for n in r["captions"]), r["captions"])
    check("picture and sound start together (mp4 source, cuts between keyframes)", render.av_gap(f) < 0.06, render.av_gap(f))
    check("progress was reported", any("Joining" in t for t in said), said)

    # ---------------------------------------------------------------- a strike run from a live .ts piece
    tsjob = job_for(ts, True, 100.0, SPEC)
    r2 = montage.make(tsjob, "escalation", out, "strikes", ids=["a", "b", "c"], hook="HE KEEPS DOING IT")
    f2 = out / r2["file"]
    check("a strike run plays in the order things happened (green, blue, red)", sample_parts(f2, r2["timeline"]) == "GBR",
          sample_parts(f2, r2["timeline"]))
    check("the strike cards are numbered 1 2 3", r2["cards"] == ["STRIKE 1", "STRIKE 2", "STRIKE 3"], r2["cards"])
    check("every strike part has captions", all(n > 0 for n in r2["captions"]), r2["captions"])
    check("picture and sound start together (mp4 from a .ts piece with its own clock)", render.av_gap(f2) < 0.06, render.av_gap(f2))
    check("the first card carries the heading", r2["hook"] == "HE KEEPS DOING IT")

    # ---------------------------------------------------------------- the strongest sync proof: the beep lands on the picture
    # A moment that crosses the green-to-blue change at source second 10.0 has its beep at second 10.0 too. In the
    # finished montage the beep must start on the frame where the colour changes (two frames of slack).
    for label, src_job, kind, off in (("mp4", job_for(mp4, False, 0.0, []), "compilation", 0.0),
                                      (".ts", job_for(ts, True, 100.0, []), "escalation", 100.0)):
        cross = [("x", 8.3 + 0, 12.5, 50), ("y", 20.3, 24.5, 60), ("z", 28.3, 32.5, 70)]       # y and z cross nothing
        sj = job_for(mp4 if label == "mp4" else ts, label != "mp4", off, cross)
        rr = montage.make(sj, kind, out, "sync" + label.strip("."), ids=["x", "y", "z"])
        first = next(seg for seg in rr["timeline"] if seg["kind"] == "part" and rr["parts"][0] == "x") if kind == "escalation" else             [seg for seg in rr["timeline"] if seg["kind"] == "part"][rr["parts"].index("x")]
        change, beep = colour_change_and_beep(out / rr["file"], first["t0"], first["t1"])
        check(f"the beep starts on the frame where the picture changes ({label}, a cut between keyframes)",
              change is not None and beep is not None and abs(change - beep) < 0.07, (change, beep))

    # ---------------------------------------------------------------- then vs now and callback
    r3 = montage.make(job, "thenvsnow", out, "thennow", ids=["a", "c"])
    check("then vs now says THEN and NOW", r3["cards"] == ["THEN", "NOW"], r3["cards"])
    check("then vs now is in step", render.av_gap(out / r3["file"]) < 0.06)
    r4 = montage.make(tsjob, "callback", out, "callback", ids=["a", "c"], hook="HE CALLED IT")
    check("a callback joins its two moments with a LATER card", r4["cards"] == ["LATER"], r4["cards"])
    check("a callback is in step too (.ts source)", render.av_gap(out / r4["file"]) < 0.06, render.av_gap(out / r4["file"]))
    check("a callback plays the setup first", sample_parts(out / r4["file"], r4["timeline"]) == "GR", sample_parts(out / r4["file"], r4["timeline"]))

    # ---------------------------------------------------------------- fitting the longest length
    r5 = montage.make(job, "compilation", out, "short", ids=["a", "b", "c"], max_len=12)
    check("a short longest length shortens every moment, still in step",
          float(probe(out / r5["file"])["video"]["duration"]) <= 12.05 and min(r5["part_lengths"]) >= 2.0
          and render.av_gap(out / r5["file"]) < 0.06, (r5["length"], r5["part_lengths"]))
    try:
        montage.make(job, "compilation", out, "tiny", ids=["a", "b", "c"], max_len=5)
        check("a length that cannot hold three moments is refused", False)
    except montage.MontageError as e:
        check("a length that cannot hold three moments says what to raise", "Raise" in str(e), e)

    # ---------------------------------------------------------------- the source files are never changed
    check("the test's source video was only read", mp4.stat().st_size > 0 and not list(tmp.glob("*.src*")))

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
