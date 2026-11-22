"""Checks that the posting path obeys review decisions: a rejected clip never goes out,
and with review-first on, an undecided clip waits for a person.

Runs against the real studio/posting.py with everything networky faked in memory.

    python tests/test_review_gate.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "gate-data"              # a plain folder: tempfile.mkdtemp is unwritable on some hosts
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)

sys.path.insert(0, str(ROOT))

from studio import creators, posting             # noqa: E402

failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok    {name}")
    else:
        print(f"  FAIL  {name}: got {got!r}, wanted {want!r}")
        failures.append(name)


def fake_job():
    return {"id": "j1", "creator": "c1", "clips": [
        {"id": "cA", "status": "done", "score": 90, "review": "approved"},
        {"id": "cR", "status": "done", "score": 90, "review": "rejected"},
        {"id": "cN", "status": "done", "score": 90, "review": None},
    ]}


FAKE_CREATOR = {"id": "c1", "autopost": True, "accounts": ["acct1"], "post_min_score": 50}


def main() -> int:
    called = []
    real_enqueue, real_creators_get = posting.enqueue, creators.get
    posting.enqueue = lambda job, clip, aids, now=False: called.append(clip["id"]) or []
    posting.creators.get = lambda cid: dict(FAKE_CREATOR)     # the module refers to it as creators.get

    try:
        # review-first on: only the approved clip is auto-queued
        posting.on_clip_ready(fake_job(), {"id": "cA", "status": "done", "score": 90, "review": "approved"})
        check("approved clip is queued", called, ["cA"])

        called.clear()
        posting.on_clip_ready(fake_job(), {"id": "cR", "status": "done", "score": 90, "review": "rejected"})
        check("rejected clip is never queued", called, [])

        called.clear()
        posting.on_clip_ready(fake_job(), {"id": "cN", "status": "done", "score": 90, "review": None})
        check("undecided clip waits for a person", called, [])

        # review-first off: the undecided clip goes out again, the rejected one still never does
        posting.REVIEW_FIRST = False
        called.clear()
        posting.on_clip_ready(fake_job(), {"id": "cN", "status": "done", "score": 90, "review": None})
        check("undecided posts with review-first off", called, ["cN"])
        called.clear()
        posting.on_clip_ready(fake_job(), {"id": "cR", "status": "done", "score": 90, "review": "rejected"})
        check("rejected still never posts with review-first off", called, [])
        posting.REVIEW_FIRST = True

        # a low-score clip never auto-posts, whatever its review says
        called.clear()
        posting.on_clip_ready(fake_job(), {"id": "cA", "status": "done", "score": 10, "review": "approved"})
        check("low score still waits", called, [])

        # the counter: two done clips have no decision yet
        job = fake_job()
        check("review_pending counts undecided", posting.review_pending(job), 1)
        job["clips"][2]["review"] = "rejected"
        check("review_pending drops to zero", posting.review_pending(job), 0)

        # the last-mile guard: a queued post for a clip rejected afterwards refuses to post
        job = fake_job()
        job["dir"] = str(DATA)                       # the mirror step saves the job back to disk
        p = {"id": "p1", "user": "u", "job": "j1", "clip": "cR", "creator": "c1", "account": "acct1",
             "account_name": "Test", "platform": "youtube", "status": "scheduled", "due_at": 0,
             "created": 0, "title": "t", "score": 1, "tries": 0, "url": "", "remote_id": "", "error": None, "views": None}
        real_jobs_get = posting.jobs.get
        posting.jobs.get = lambda jid: job
        posting.accounts.get = lambda aid: {"id": "acct1", "name": "Test", "platform": "youtube"}
        try:
            with posting.ctx.as_user("test_user_01"):    # alerts.notify looks up the signed-in user
                posting._post(p)
        finally:
            posting.jobs.get = real_jobs_get
        check("last-mile guard fails the post", p["status"], "failed")
        check("the error says why", "rejected in review" in (p["error"] or ""), True)
    finally:
        posting.enqueue = real_enqueue
        posting.creators.get = real_creators_get

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
