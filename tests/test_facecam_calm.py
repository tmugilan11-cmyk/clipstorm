"""A webcam with no border is still found: it is an island of calm against one side of a moving picture.

`facecam._drift` works on two small arrays (how much each pixel moves, how light it is), so everything here
is made up in memory: no video, no ffmpeg, no network. The numbers are the ones measured on a real stream:
the game moves at about 22, the room behind a streamer at about 3.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import facecam as fc

FAILED = []
W, H = fc.W, fc.H


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def picture(*boxes, game=22.0, calm=3.0):
    """A moving game with still boxes drawn on it: each box is (x0, y0, x1, y1) on the small grid."""
    rng = np.random.default_rng(7)
    still = game + rng.normal(0, 2.0, size=(H, W)).astype(np.float32)
    for x0, y0, x1, y1 in boxes:
        still[y0:y1, x0:x1] = calm + rng.normal(0, 0.5, size=(y1 - y0, x1 - x0))
    return still, np.full((H, W), 100.0, dtype=np.float32)


def first(still, light):
    got = fc._drift(still, light)
    return (int(got[0]["x"]), int(got[0]["y"]), int(got[0]["x1"]), int(got[0]["y1"])) if got else None


def near(got, want, by=2):
    return got is not None and all(abs(g - w) <= by for g, w in zip(got, want))


def main():
    cw, ch = 72, 50      # the webcam measured on the real stream: 22% of the width, 27% of the height

    for name, box in (("top-left", (0, 0, cw, ch)), ("top-right", (W - cw, 0, W, ch)),
                      ("bottom-left", (0, H - ch, cw, H)), ("bottom-right", (W - cw, H - ch, W, H))):
        got = first(*picture(box))
        check(f"a webcam in the {name} corner is found", near(got, box), got)

    for name, box in (("left", (0, 65, cw, 65 + ch)), ("right", (W - cw, 40, W, 40 + ch)),
                      ("top", (120, 0, 120 + cw, ch)), ("bottom", (60, H - ch, 60 + cw, H))):
        got = first(*picture(box))
        check(f"a webcam along the {name} side is found", near(got, box), got)

    # the streamer moves in the middle of their own picture: the room either side of them is still
    still, light = picture((0, 65, cw, 115))
    still[75:115, 28:44] = 24.0
    got = first(still, light)
    check("a person moving inside the webcam does not cut the box short", near(got, (0, 65, cw, 115)), got)

    # a counter drawn under the webcam is still too, but it is narrower and it is not the webcam
    got = first(*picture((0, 65, cw, 115), (0, 116, 30, 122)))
    check("something small drawn under the webcam is left out", near(got, (0, 65, cw, 115)), got)

    # a camera filling the whole frame: the room is still everywhere, there is no game round anything
    rng = np.random.default_rng(3)
    room = np.full((H, W), 3.0, dtype=np.float32)
    room[30:180, 100:230] = 20.0 + rng.normal(0, 2.0, size=(150, 130))       # the person
    check("a camera that fills the frame is not a webcam on a game",
          fc._drift(room, np.full((H, W), 100.0, dtype=np.float32)) == [])

    check("a game with no webcam gives nothing", fc._drift(*picture()) == [])
    check("a still sliver too small to be a webcam gives nothing", fc._drift(*picture((0, 80, 20, 95))) == [])
    check("a still banner right across the top is not a webcam", fc._drift(*picture((0, 0, W, 30))) == [])

    # a black hole is not a picture
    still, light = picture((0, 65, cw, 115))
    light[65:115, 0:cw] = 5.0
    check("a still black box is not taken for a webcam", fc._drift(still, light) == [])

    # a stretch of a profile, and the dip a person makes in it
    check("a short dip does not end a stretch", fc._runs(np.array([1, 1, 0, 1, 1.0]), 0.5, 1) == [(0, 5)])
    check("a long dip does", fc._runs(np.array([1, 1, 0, 0, 0, 1.0]), 0.5, 1) == [(0, 2), (5, 6)])
    check("nothing above the floor is no stretch", fc._runs(np.zeros(5), 0.5, 1) == [])

    # an empty box must not be measured at all (it used to warn about the mean of nothing)
    still, light = picture()
    check("a box outside the picture is simply not a webcam",
          fc._plausible(400, 10, 460, 60, still, light, 22.0) is None)

    # where the person is inside a webcam picture: the part that moves, the room being still
    box = np.full((40, 100), 1.0)
    box[:, 60:80] = 12.0
    c = fc._center_of(box)
    check("a person on the right of the box is found there", c is not None and abs(c - 0.70) < 0.03, c)
    box = np.full((40, 100), 1.0)
    box[:, 5:15] = 12.0
    check("a person at the far edge is clamped to 0.2", fc._center_of(box) == 0.2, fc._center_of(box))
    check("a perfectly still box says nothing", fc._center_of(np.full((40, 100), 0.5)) is None)
    check("movement everywhere says nothing", fc._center_of(np.random.RandomState(1).uniform(8, 12, (40, 100))) is None)

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
