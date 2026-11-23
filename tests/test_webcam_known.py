"""A clip switched to "Facecam on top" uses the webcam place the video's other clips already found.

"IT WAS KSI THE WHOLE TIME" (2026-11-23) was re-made with Facecam on top and came out without the streamer: the
video's own box was the stream's opening corner, and a fresh search of that dark, still scene found nothing, while
31 other clips of the same video had the camera at one place whose border measured 55.7 in that clip.
No video is read: the border measure is a stand-in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import facecam, jobs

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def main():
    real = (facecam._full_frame, facecam.border_strength, facecam.detect)
    searched = []
    strength = {(0, 0, 389, 189): 0.2, (0, 515, 574, 393): 55.7, (0, 502, 574, 469): 46.9}
    facecam._full_frame = lambda src: "frame"
    facecam.border_strength = lambda frame, box: strength.get(tuple(box), 0.0)
    facecam.detect = lambda src: searched.append(1) or None
    try:
        job = {"facecam": [0, 0, 389, 189],
               "clips": [{"facecam": [0, 515, 574, 393]}] * 3 + [{"facecam": [0, 502, 574, 469]}, {"layout": "crop"}]}
        check("the box the other clips found is used", jobs._webcam_in(job, "clip.mp4") == [0, 515, 574, 393])
        check("without searching the picture again", not searched)

        strength.clear()
        check("a box whose border is not in this clip is not used", jobs._webcam_in(job, "clip.mp4") is None)
        check("then the picture is searched", searched)

        searched.clear()
        strength[(0, 0, 389, 189)] = 30.0
        check("the video's own box still counts when it is there", jobs._webcam_in(job, "clip.mp4") == [0, 0, 389, 189])
    finally:
        facecam._full_frame, facecam.border_strength, facecam.detect = real
    src = Path(__file__).resolve().parent.parent / "web" / "index.html"
    check("the editor says when a clip was made without the streamer panel", "esc(c.layout_note)" in src.read_text(encoding="utf-8"))
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
