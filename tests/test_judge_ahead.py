"""The parts of a long video are judged a few at a time, and their clips still come out in the order of the video.

A whole video runs through jobs._run_job here: a 40-minute file made by ffmpeg (four 10-minute parts), a stand-in
transcript and a stand-in judge that takes a moment per part. No network, no AI, no rendering."""
import sys
import tempfile
import threading
import time
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import brain, ctx, jobs, transcribe

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def main():
    ctx._uid.set("u_aheadtest")
    tmp = Path(tempfile.mkdtemp(prefix="pcahead"))
    src = tmp / "long.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=64x36:r=1:d=2400",
                    "-f", "lavfi", "-i", "sine=f=300:d=2400:sample_rate=16000", "-c:v", "libx264", "-preset",
                    "ultrafast", "-c:a", "aac", "-shortest", str(src)], check=True)
    d = tmp / "job"
    d.mkdir()
    job = {"id": "ahead1", "user": "u_aheadtest", "dir": str(d), "status": "queued", "stage": "", "progress": 0.0,
           "clips": [], "creator": None, "kind": "video", "title": "t", "uploader": "u", "duration": 0, "ai": {},
           "source": {"type": "file", "path": str(src), "name": "long.mp4"},
           "options": {**jobs.DEFAULTS, "max_clips": 0, "range_start": None, "range_end": None, "min_score": 0}}
    jobs._jobs["ahead1"] = job

    live, most, order = [0], [0], []
    lock = threading.Lock()

    def fake_judge(words, db, duration, *a, at=0.0, **k):
        with lock:
            live[0] += 1
            most[0] = max(most[0], live[0])
        time.sleep(1.5 if at < 1 else 0.3)        # the first part is the slowest, so later ones finish first
        with lock:
            live[0] -= 1
            order.append(at)
        return [{"start": 10.0, "end": 40.0, "score": 90, "hook": f"PART AT {int(at)}", "title": "x"}], {"tokens": 1}

    real = (brain.find_clips, transcribe.transcribe, jobs.render_one, jobs.config.SKIP_STATIC, transcribe.cloud)
    brain.find_clips = fake_judge
    transcribe.transcribe = lambda audio, p=None, quiet_ok=False: [
        {"w": f"word{i}", "s": float(i), "e": float(i) + 0.5} for i in range(0, 600, 5)]
    transcribe.cloud = lambda: True
    jobs.render_one = lambda job, clip, words: clip.update(status="done")
    jobs.config.SKIP_STATIC = False
    try:
        jobs._run_job(job)
    finally:
        brain.find_clips, transcribe.transcribe, jobs.render_one, jobs.config.SKIP_STATIC, transcribe.cloud = real
        jobs._jobs.pop("ahead1", None)

    check("the video finishes", job["status"] == "done", (job["status"], job.get("stage")))
    check("several parts were judged at the same time", most[0] >= 2, most[0])
    check("never more than JUDGE_AHEAD (+1 being added) at once", most[0] <= jobs.JUDGE_AHEAD + 1, most[0])
    check("a later part really did finish before the first", order and order[0] > 0, order)
    starts = [c["start"] for c in job["clips"]]
    check("the clips are still in the order of the video", starts == sorted(starts) and len(starts) == 4, starts)
    check("their numbers follow that order", [c["id"] for c in job["clips"]] == ["clip01", "clip02", "clip03", "clip04"],
          [c["id"] for c in job["clips"]])
    check("every part counts as done", job.get("done_blocks") == 4, job.get("done_blocks"))
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
