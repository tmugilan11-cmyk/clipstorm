"""One network hiccup does not end a long video, and a video that failed part-way carries on from where it stopped.

On the first whole-stream run (5 h 45 min) one SSL handshake timeout from the speech service at part 28 of 35 ended
the whole video and left 21 found clips unmade."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import ctx, jobs

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


def main():
    ctx._uid.set("u_carrytest")
    check("a handshake timeout is a hiccup", jobs._passing(RuntimeError("Logfare could not transcribe this audio: "
                                                                          "_ssl.c:1126: The handshake operation timed out")))
    check("a 503 is a hiccup", jobs._passing(RuntimeError("HTTP 503 Service Unavailable")))
    check("a wrong key is not", not jobs._passing(RuntimeError("401 Unauthorized: invalid API key")))

    real_t, real_w = jobs.transcribe.transcribe, jobs.HEAR_WAITS
    jobs.HEAR_WAITS = (0, 0, 0)
    calls = []

    def flaky(audio, on_progress=None):
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("The handshake operation timed out")
        return [{"w": "chat", "s": 0.0, "e": 0.3}]
    try:
        jobs.transcribe.transcribe = flaky
        got = jobs._hear_patiently(None)
        check("a part that times out twice is heard on the third try", got and len(calls) == 3, (got, len(calls)))

        calls.clear()
        jobs.transcribe.transcribe = lambda a, p=None: calls.append(1) or (_ for _ in ()).throw(RuntimeError("timed out"))
        try:
            jobs._hear_patiently(None)
            check("a service that never comes back is still reported", False)
        except RuntimeError:
            check("a service that never comes back is still reported", len(calls) == 4, len(calls))

        calls.clear()
        jobs.transcribe.transcribe = lambda a, p=None: calls.append(1) or (_ for _ in ()).throw(RuntimeError("401 bad key"))
        try:
            jobs._hear_patiently(None)
        except RuntimeError:
            pass
        check("a wrong key is not tried again", len(calls) == 1, len(calls))
    finally:
        jobs.transcribe.transcribe, jobs.HEAR_WAITS = real_t, real_w

    # carrying on
    d = Path(tempfile.mkdtemp(prefix="pccarry"))
    (d / "words.json").write_text("[]", encoding="utf-8")
    job = {"id": "carry1", "user": "u_carrytest", "dir": str(d), "status": "error", "kind": "video", "error": "x",
           "creator": None, "clips": [{"id": "clip01", "status": "done"},
                                      {"id": "clip02", "status": "error", "error": jobs.UNMADE},
                                      {"id": "clip03", "status": "error", "error": "Render failed"}]}
    jobs._jobs["carry1"] = job
    put = []
    real_put = jobs._q.put
    jobs._q.put = lambda item, user=None: put.append(item)
    try:
        jobs.carry_on("carry1")
    finally:
        jobs._q.put = real_put
    check("a failed video is queued again to carry on", job["status"] == "queued" and job["resume"] is True and put, job)
    check("its finished clips are kept", job["clips"][0]["status"] == "done")
    check("the clips it found but never made are made now", job["clips"][1]["status"] == "queued")
    check("a clip that failed for its own reason is left for a re-make", job["clips"][2]["status"] == "error")
    try:
        jobs.carry_on("carry1")
        check("a video that is not failed cannot carry on", False)
    except ValueError:
        check("a video that is not failed cannot carry on", True)

    d2 = Path(tempfile.mkdtemp(prefix="pccarry"))
    jobs._jobs["carry2"] = {"id": "carry2", "user": "u_carrytest", "dir": str(d2), "status": "error", "kind": "video", "clips": []}
    try:
        jobs.carry_on("carry2")
        check("a video with nothing heard yet cannot carry on", False)
    except ValueError:
        check("a video with nothing heard yet cannot carry on", True)
    jobs._jobs["carry3"] = {"id": "carry3", "user": "someone-else", "dir": str(d), "status": "error", "kind": "video", "clips": []}
    try:
        jobs.carry_on("carry3")
        check("someone else's video cannot be carried on", False)
    except KeyError:
        check("someone else's video cannot be carried on", True)
    src = Path(jobs.__file__).read_text(encoding="utf-8")
    check("every part of a video is heard patiently", "ahead.submit(ctx.bind(_hear_patiently)" in src)
    for k in ("carry1", "carry2", "carry3"):
        jobs._jobs.pop(k, None)
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
