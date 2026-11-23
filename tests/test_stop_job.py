"""Stop on a video being made: a waiting one never starts, a running one stops looking for more moments and still
finishes the clips it already found, and nobody can stop someone else's video."""
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


def fake(jid, status, user=None, clips=()):
    d = Path(tempfile.mkdtemp(prefix="pcstop"))
    job = {"id": jid, "user": user or ctx.uid(), "dir": str(d), "status": status, "stage": "", "progress": 0.3,
           "clips": list(clips), "creator": None, "resume": True}
    jobs._jobs[jid] = job
    return job


def main():
    ctx._uid.set("u_stoptest")
    q = fake("stopq", "queued")
    jobs.stop("stopq")
    check("a waiting video is not started", q["status"] == "done" and q["stop"] and q["resume"] is False, q)
    check("and says it was stopped by you", "Stopped by you" in q["stage"], q["stage"])

    r = fake("stopr", "running", clips=[{"id": "clip01", "status": "queued"}])
    jobs.stop("stopr")
    check("a running video is told to stop, not killed", r["status"] == "running" and r["stop"] is True, r)
    check("its found clips are left to finish", r["clips"][0]["status"] == "queued")
    check("the page says it is stopping", r["stage"].startswith("Stopping"), r["stage"])
    check("a stopped video is not picked up again after a restart", r["resume"] is False)

    ran = []
    real = jobs.games.detect
    jobs.games.detect = lambda *a: ran.append(1) or ("", 0)
    try:
        jobs._run_job(fake("stopw", "queued") | {"stop": True})
    finally:
        jobs.games.detect = real
    check("a video stopped while waiting does no work when its turn comes", not ran)

    d = fake("stopd", "done")
    check("a finished video is left as it is", jobs.stop("stopd")["status"] == "done" and "stop" not in d)

    fake("stopx", "running", user="someone-else")
    try:
        jobs.stop("stopx")
        check("someone else's video cannot be stopped", False)
    except KeyError:
        check("someone else's video cannot be stopped", True)

    # the server went down while a stopped video was finishing: it comes back finished, not waiting forever
    import json
    sd = Path(tempfile.mkdtemp(prefix="pcstop"))
    (sd / "job.json").write_text(json.dumps({"id": "stopz", "status": "running", "stop": True, "clips": [
        {"id": "clip01", "status": "done"}, {"id": "clip02", "status": "queued"}]}), encoding="utf-8")
    jobs._load_file(sd / "job.json", "u_stoptest")
    z = jobs._jobs.get("stopz") or {}
    check("a stopped video comes back finished after a restart", z.get("status") == "done" and not z.get("resume"), z)
    check("its unmade clip says it can be re-made", z.get("clips", [{}, {}])[1].get("status") == "error", z.get("clips"))
    jobs._jobs.pop("stopz", None)

    src = Path(jobs.__file__).read_text(encoding="utf-8")
    check("the reading loop stops at the next part", src.count('if job.get("stop"):') >= 3)

    for jid in ("stopq", "stopr", "stopw", "stopd", "stopx"):
        jobs._jobs.pop(jid, None)
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
