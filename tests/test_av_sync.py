"""A clip's picture and sound start on the same instant, wherever the cut falls.

The bug this guards: ffmpeg's `-ss` before the input lands a .ts stream (every live clip) after the asked time, the
picture then waits for the next keyframe (two seconds on a YouTube stream) and the sound does not, so the finished
clip had the streamer's voice up to two seconds before his lips. A real stream piece is copied here in miniature:
an MPEG-TS file whose clock starts at 1.4 s, a keyframe every two seconds, a beep every second.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import render

FAILED = []
ASS = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
       "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
       "MarginR, MarginV, Encoding\nStyle: Default,Arial,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,"
       "100,100,0,0,1,2,0,2,10,10,10,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
       "MarginV, Effect, Text\n")


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def frame(path, t, vf="null", exact=True):
    seek = ["-i", str(path), "-ss", f"{t:.3f}"] if exact else ["-ss", f"{t:.3f}", "-i", str(path)]
    out = subprocess.run(["ffmpeg", "-v", "error"] + seek + ["-frames:v", "1", "-vf", vf + ",scale=54:96,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(out, dtype=np.uint8).reshape(96, 54).astype(float)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="pcsync"))
    src = tmp / "piece.ts"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=60:d=40",
                    "-f", "lavfi", "-i", "sine=f=880:beep_factor=8:d=40:sample_rate=48000",
                    "-c:v", "libx264", "-preset", "ultrafast", "-g", "120", "-keyint_min", "120", "-sc_threshold", "0",
                    "-c:a", "aac", "-f", "mpegts", str(src)], check=True)
    crop = "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    for start in (0.4, 13.3, 21.75, 25.0):
        out = tmp / "out"
        out.mkdir(exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="pcw"))
        name = f"c{int(start * 100)}"
        render._render_in(work, src, out, name, start, start + 6, "crop", 1080, ASS, src_w=640, src_h=360)
        made = out / f"{name}.mp4"
        check(f"a cut at {start}s has picture and sound the same length from the same start",
              render.av_gap(made) < 0.06, render.av_gap(made))
        diff = np.abs(frame(made, 0, "null", False) - frame(src, start, crop)).mean()
        later = np.abs(frame(made, 0, "null", False) - frame(src, start + 0.5, crop)).mean()
        check(f"a cut at {start}s opens on the source's frame at {start}s", diff < 4.0 and later > 2 * diff, (diff, later))

    check("the input is opened early enough for a keyframe", render._cut_window(30.0, 40.0) == (18.0, 12.0, 10.0))
    check("near the start nothing is skipped", render._cut_window(3.0, 8.0) == (0.0, 3.0, 5.0))
    check("both tracks are trimmed by the same fixed amount",
          render._trim("", 12, 6) == "trim=start=12.000:duration=6.000,setpts=PTS-12.000/TB,"
          and render._trim("a", 12, 6) == "atrim=start=12.000:duration=6.000,asetpts=PTS-12.000/TB,")

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
