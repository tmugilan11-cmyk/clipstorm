"""0 clips means "as many good clips as it can find", for a finished video and for a live hour.

The person asked for a way to get every good clip instead of a fixed number. 0 is that way: a video is judged in
every block and keeps every strong find up to jobs.ALL_CLIPS; a live recording with 0 clips an hour has no hourly
limit, only live.MAX_LIVE_CLIPS for the whole recording.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import creators, jobs, live

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def main():
    check("0 clips is accepted for a video, not raised to 1", jobs.LIMITS["max_clips"][0] == 0)
    check("a video can ask for up to 100", jobs.LIMITS["max_clips"][1] == 100)
    check("'all' stops at the same cap as one live recording", jobs.ALL_CLIPS == 100 and live.MAX_LIVE_CLIPS >= 100)
    check("a creator can save 0 clips per video", creators.NUMERIC["max_clips"][0] == 0)
    check("a creator can save 0 live clips an hour", creators.NUMERIC["live_per_hour"][0] == 0)
    src = Path(jobs.__file__).read_text(encoding="utf-8")
    check("the video pipeline reads 0 as ALL_CLIPS", '(int(o["max_clips"]) or ALL_CLIPS)' in src)
    lsrc = Path(live.__file__).read_text(encoding="utf-8")
    check("a live hour of 0 has no hourly limit", 'if st["live_per_hour"] and len(recent) >= st["live_per_hour"]' in lsrc)
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
