"""A recording of a stream that is already running begins at the stream's first minute.

Checked here without a network and without ffmpeg: the stream's fragments are fetched in order from the
first one, a fragment that fails is asked for again, every piece's sound puts it on the recording's clock,
a stream being caught up on is listened to in long stretches and still looked at second by second, and a
piece of stream is not thrown away before it has been listened to.
"""
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import live, transcribe

FAILED = []
SR = live.SR


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def session(folder, **settings):
    """A real Session on an empty folder, with nothing started."""
    d = Path(tempfile.mkdtemp(dir=folder))
    job = {"id": "t", "dir": str(d), "user": "u", "creator": "c", "clips": [], "ai": {}, "title": "", "uploader": "",
           "source": {"url": "https://www.youtube.com/watch?v=x", "name": "x"}, "options": {"captions": True}}
    s = live.Session(job, dict({"from_start": True, "buffer_min": 20}, **settings))
    s._note = lambda text: None
    return s


def sound(seconds, level=0):
    """`seconds` of 16 kHz sound as the bytes ffmpeg would hand back."""
    return (np.full(int(seconds * SR), level, dtype=np.int16)).tobytes()


def window(seq, tgt=5.0, count=720):
    live._playlist_window = lambda url: (seq, tgt, count)


def run(fn, seconds=20):
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    t.join(seconds)
    return not t.is_alive()


def main():
    root = Path(tempfile.mkdtemp(dir=os.getcwd() + "/.pctest") if os.path.isdir(".pctest") else tempfile.mkdtemp())
    real_sleep = time.sleep
    try:
        # ------------------------------------------------ the fragments, from the first one, in order
        s = session(root)
        asked, written = [], []
        live._head_seq = lambda base: 11                      # the stream has fragments 0..11: four pieces of three
        live._fetch = lambda url, timeout=20: (asked.append(url), url.encode())[1]

        def mux(vb, ab, nominal):
            written.append((vb, ab, nominal))
            if len(written) == 4:
                s.stop_flag.set()
            return True
        s._mux = mux
        frags = [{"base": "http://v/x", "td": 2.0}, {"base": "http://a/x", "td": 2.0}]
        check("the fetch finishes", run(lambda: s._fragments(frags)))
        check("four pieces are written from twelve fragments", len(written) == 4, len(written))
        first = written[0][0].decode() if written else ""
        check("the first piece is the stream's first three fragments, in order",
              first.count("sq=0") == 1 and first.index("sq=0") < first.index("sq=1") < first.index("sq=2"), first)
        check("the picture and the sound of a piece are the same fragments",
              bool(written) and written[0][1].decode().replace("//a/", "//v/") == first)
        check("a piece is as long as its fragments", bool(written) and written[0][2] == 6.0)
        check("the recording knows which fragment comes next", s.frag_next == 12, s.frag_next)
        check("the recording knows where the stream has got to", s.head == 11, s.head)

        # ------------------------------------------------ a restart carries on, it does not begin again
        s = session(root)
        s.frag0 = s.frag_next = 300
        got = []
        live._head_seq = lambda base: 305
        s._mux = lambda vb, ab, nominal: (got.append(vb.decode()), s.stop_flag.set(), True)[2]
        run(lambda: s._fragments(frags))
        check("a recording picked up again starts at the fragment it had reached",
              bool(got) and "sq=300" in got[0] and "sq=0&" not in got[0] and not got[0].endswith("sq=0"), got[:1])

        # ------------------------------------------------ a fragment that fails is asked for again
        s = session(root)
        time.sleep = lambda x: None                            # the pauses between tries are not what is tested
        tries = {"n": 0}

        def flaky(url, timeout=20):
            if "sq=4" in url and "//v/" in url:
                tries["n"] += 1
                if tries["n"] <= 3:
                    raise OSError("connection reset")
            return url.encode()
        live._fetch = flaky
        live._head_seq = lambda base: 5
        done = []
        s._mux = lambda vb, ab, nominal: (done.append(vb.decode()), len(done) == 2 and s.stop_flag.set(), True)[2]
        check("the fetch finishes after a failure", run(lambda: s._fragments(frags)))
        time.sleep = real_sleep
        check("the piece with the failed fragment is still written, whole and in its place",
              len(done) == 2 and all(f"sq={i}" in done[1] for i in (3, 4, 5)), done)
        check("nothing was skipped", s.frag_next == 6, s.frag_next)

        # ------------------------------------------------ the download does not run away from the listening
        s = session(root)
        s.seg_clock, s.t_done = live.AHEAD_MAX + 60.0, 0.0
        live._head_seq = lambda base: 600
        live._fetch = lambda url, timeout=20: url.encode()
        took = []
        s._mux = lambda vb, ab, nominal: (took.append(1), True)[1]
        threading.Timer(1.5, s.stop_flag.set).start()
        run(lambda: s._fragments(frags))
        check("far ahead of the listening, nothing more is fetched", took == [], len(took))

        # ------------------------------------------------ every piece's sound puts it on the clock
        s = session(root)
        lengths = iter([5.99, 6.01, 0.0, 6.0])
        s._piece_audio = lambda piece: sound(next(lengths), 900)
        for i in range(4):
            s._commit(s.buf / f"seg_{i:06d}.ts", 6.0)
        check("the clock is the sound of the pieces, added up", abs(s.seg_clock - 24.0) < 0.01, s.seg_clock)
        check("the sound waiting to be heard is exactly as long as the clock",
              len(s.pending) // 2 == s.samples and abs(s.samples / SR - s.seg_clock) < 1e-6)
        check("a piece with no sound keeps its place as silence",
              abs((s.segments[2][2] - s.segments[2][1]) - 6.0) < 1e-6, s.segments[2])
        check("pieces follow one another with no gap",
              all(abs(s.segments[i][2] - s.segments[i + 1][1]) < 1e-9 for i in range(3)))
        check("loudness is kept once a second", len(s.db) == 24, len(s.db))
        rows = live._list_rows(s.buf / "index.csv")
        check("the pieces and their places are written down for a restart",
              len(rows) == 4 and rows[3][0] == "seg_000003.ts" and abs(rows[3][2] - 24.0) < 0.01, rows)
        (s.buf / "half.csv").write_text("seg_000000.ts,0.0,6.0\nseg_000001.ts,6.0,1", encoding="utf-8")
        check("a line still being written is not read as a finished piece",
              live._list_rows(s.buf / "half.csv") == [("seg_000000.ts", 0.0, 6.0)])

        # ------------------------------------------------ how far behind live
        s = session(root)
        s.mode, s.head, s.frag_td, s.t_done = "start", 5399, 2.0, 600.0     # three hours of stream, ten minutes heard
        check("behind live is measured against where the streamer is now", s._behind() == 10200.0, s._behind())
        s.frag0 = 300                                                        # picked up after a restart at minute ten
        check("and allows for where this recording began", s._behind() == 9600.0, s._behind())
        s.job.update(status="live", stage="Recording")
        live.jobs.save = lambda job: None
        s._show_catchup()
        check("the card says how far behind it is, in hours and minutes",
              s.job["stage"] == "Catching up: 2 h 40 min behind live", s.job["stage"])
        s.t_done = 10200.0 - 20
        s._show_catchup()
        check("and says Recording again once it has caught up", s.job["stage"] == "Recording", s.job["stage"])

        # ------------------------------------------------ catching up is listened to in long stretches
        s = session(root)
        heard = []
        transcribe.cloud = lambda: True
        transcribe.transcribe = lambda audio, on_progress=None, quiet_ok=False: (
            heard.append((len(audio) / SR, quiet_ok)), [{"w": "word", "s": 1.0, "e": 1.2}])[1]
        s.pending += sound(300, 500)
        s.samples = 300 * SR
        check("a backlog is listened to", s._transcribe_step() is True)
        check("three long stretches at once", len(heard) == 3 and all(20 <= h[0] <= 29.1 for h in heard), heard)
        check("a quiet stretch is an answer, not a failure", all(h[1] for h in heard), heard)
        check("the transcript moves on by what was heard", abs(s.t_done - sum(h[0] for h in heard)) < 0.01, s.t_done)
        check("the words are put on the recording's clock, in order",
              len(s.words) == 3 and s.words[0]["s"] == 1.0 and 20 < s.words[1]["s"] < s.words[2]["s"],
              [w["s"] for w in s.words])
        heard.clear()
        s2 = session(root)
        s2.pending += sound(8, 500)
        s2.samples = 8 * SR
        s2._transcribe_step()
        check("live speech is still heard a few seconds at a time", len(heard) == 1 and heard[0][0] <= 6.6, heard)
        s3 = session(root)
        s3.pending += sound(300, 500)
        s3.ai_busy, s3.t_done, s3.judged_to = time.time(), live.CATCHUP_AI + 100.0, 0.0
        check("the listening waits for the AI rather than run far past it", s3._transcribe_step() is False)

        # ------------------------------------------------ a jump is found wherever it is, not only at the newest second
        s = session(root)
        s.db = [-40.0] * 600
        s.db[300:306] = [-10.0] * 6            # a shout five minutes in, long before the newest second
        s.t_done = 590.0
        s._watch_spikes()
        check("a jump in the middle of a backlog is found", bool(s.spike) and 295 <= s.spike["t"] <= 306, s.spike)

        # ------------------------------------------------ where a plain ffmpeg connection begins (no backlog to walk)
        s = session(root)
        window(1000)
        check("a new recording begins at the first piece the stream still offers",
              s._start_index("http://x/live.m3u8") == 0)
        check("the piece it began at is remembered", s.seq0 == 1000)
        s.samples = SR * 600
        window(1060)
        check("pieces the live edge moved on by are not recorded twice",
              s._start_index("http://x/live.m3u8") == 60, s._start_index("http://x/live.m3u8"))
        window(1200)
        check("a beginning that has scrolled out of the window is not repeated",
              s._start_index("http://x/live.m3u8") is None)
        window(1000)
        check("a plain stream address is left to ffmpeg", s._start_index("http://x/video.mp4") is None)
        off = session(root, from_start=False)
        check("turning the switch off records from now", off._start_index("http://x/live.m3u8") is None)

        # ------------------------------------------------ a piece is kept until it has been listened to
        s = session(root)
        s._piece_audio = lambda piece: sound(60)
        for i in range(60):
            f = s.buf / f"seg_{i:06d}.ts"
            f.write_bytes(b"x" * 8)
            s._commit(f, 60.0)
        s.pending.clear()
        check("every piece is picked up", len(s.segments) == 60, len(s.segments))
        s.t_done = 300.0                       # the old rule would have dropped the first 55 pieces here
        s._scan_segments()
        check("pieces the transcript has not reached yet stay on disk",
              len(s.segments) == 60 and (s.buf / "seg_000000.ts").exists(), len(s.segments))
        s.t_done = 1800.0
        s._scan_segments()
        left = [p.name for p, _, _ in s.segments]
        check("a piece the transcript has passed may go",
              "seg_000000.ts" not in left and not (s.buf / "seg_000000.ts").exists())
        check("what the transcript has not reached is still there", "seg_000055.ts" in left, left[-3:])

        # ------------------------------------------------ a piece the AI has not read yet is kept for it
        s = session(root, buffer_min=5)
        s._piece_audio = lambda piece: sound(60)
        for i in range(40):
            f = s.buf / f"seg_{i:06d}.ts"
            f.write_bytes(b"x" * 8)
            s._commit(f, 60.0)
        s.pending.clear()
        s.t_done, s.judged_to = 2400.0, 1500.0       # heard to minute 40, the AI has read to minute 25
        s._scan_segments()
        left = [p.name for p, _, _ in s.segments]
        check("pieces the AI has not read yet outlive a short buffer", "seg_000023.ts" in left, left[:3])
        check("pieces it has read may go", "seg_000010.ts" not in left, left[:3])
        # ------------------------------------------------ a clip waiting to be made keeps its pieces
        w = session(root, buffer_min=5)
        w._piece_audio = lambda piece: sound(60)
        for i in range(40):
            f = w.buf / f"seg_{i:06d}.ts"
            f.write_bytes(b"x" * 8)
            w._commit(f, 60.0)
        w.pending.clear()
        w.t_done = w.judged_to = 2400.0               # heard and read to minute 40
        w.job["clips"].append({"id": "clip001", "start": 610.0, "end": 640.0, "status": "queued"})
        w._scan_segments()
        left = [p.name for p, _, _ in w.segments]
        check("the pieces of a clip still waiting to be made are kept", "seg_000010.ts" in left and "seg_000009.ts" in left, left[:3])
        check("older pieces nobody is waiting for still go", "seg_000005.ts" not in left, left[:3])
        w.job["clips"][0].update(status="done", src="x")
        w._scan_segments()
        check("once the clip is made its pieces may go", "seg_000010.ts" not in [p.name for p, _, _ in w.segments])

        # ------------------------------------------------ the webcam is looked for in every clip, not once
        c = session(root)
        looked = []
        c._find_facecam = lambda src: (looked.append(src), {"intro": None, "game1": [0, 386, 430, 295],
                                                            "odd": [1640, 728, 280, 352]}.get(src))[1]
        there = {"game2": True, "intro2": False, "odd": False}
        live.facecam.still_there = lambda src, box: there.get(src, False)
        check("a first clip with no webcam in it finds none", c._webcam_for("intro") is None)
        check("the next clip is looked at afresh and finds it", c._webcam_for("game1") == [0, 386, 430, 295])
        check("a later clip only has it confirmed, not searched again",
              c._webcam_for("game2") == [0, 386, 430, 295] and looked == ["intro", "game1"], looked)
        check("a scene without the webcam gets no webcam", c._webcam_for("intro2") is None)
        check("a one-off find elsewhere does not replace the usual place",
              c._webcam_for("odd") == [1640, 728, 280, 352] and c.facecam_box == [0, 386, 430, 295], c.facecam_box)

        s.judged_to = 0.0                             # an AI that never answers must not keep everything for ever
        s._scan_segments()
        check("an AI that never answers cannot fill the disk", "seg_000015.ts" not in [p.name for p, _, _ in s.segments])
    finally:
        time.sleep = real_sleep
        shutil.rmtree(root, ignore_errors=True)

    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
