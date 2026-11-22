"""The improvement engine's three routes, answered without a network and without a real key.

The engine itself is tested in `tests/test_learn.py`. This file is about the doorway: that the routes
exist, that they refuse with a sentence rather than a 500, and that the answer is shaped the way the
page that draws it expects.

Every section clears the person's round log first, because one round blocks the next for six hours by
design and that is exactly the thing being tested.

Run: python tests/test_learn_api.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

_DATA = HERE / "learnapi-data"
_DATA.mkdir(exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(_DATA)
os.environ["PEAKCUT_PUBLIC_URL"] = "http://127.0.0.1:8765"
os.environ["PEAKCUT_ACCOUNTS"] = "0"
os.environ["PEAKCUT_AI"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from studio import accounts, ai, config, ctx, db, learn, server  # noqa: E402

db.init()

BASE = "http://127.0.0.1:8765"
CLIENT = TestClient(server.app, base_url=BASE, follow_redirects=False)

ok = 0
bad = []


def check(name: str, got, want=True) -> None:
    global ok
    if got == want:
        ok += 1
    else:
        bad.append(f"{name}   got {got!r}  wanted {want!r}")


class _Caller:
    """One route, called the way the single-user install calls it: inside a signed-in context.

    The routes read the person from `request.state.user`, which the session middleware fills from the
    cookie; a test has no cookie, so the context is set here instead of signing in."""

    def get(self, path, **kw):
        with ctx.as_user("u_local"):
            return CLIENT.get(path, **kw)

    def post(self, path, **kw):
        with ctx.as_user("u_local"):
            return CLIENT.post(path, **kw)

    def delete(self, path, **kw):
        with ctx.as_user("u_local"):
            return CLIENT.delete(path, **kw)


client = _Caller()


def clear_log() -> None:
    """Forget every round, so the next one is allowed. The six hour wait is tested at the end."""
    with ctx.as_user("u_local"):
        learn._file("u_local").unlink(missing_ok=True)


def ai_ready(flag: bool):
    """True or False for "the AI is set up", restored by the caller."""
    ai.ready = (lambda: flag) if flag else (lambda: False)


_REAL_READY = ai.ready
_REAL_TOKEN = accounts.youtube_token


def no_channel():
    accounts.youtube_token = lambda: ""


def restore() -> None:
    ai.ready = _REAL_READY
    accounts.youtube_token = _REAL_TOKEN


# ---------------------------------------------------------------- the routes exist
for path, method in (("/api/learn/state", "get"), ("/api/learn/run", "post"), ("/api/learn/undo", "post")):
    r = getattr(client, method)(path, **({"json": {}} if method == "post" else {}))
    check(f"{method.upper()} {path} is not a missing route", r.status_code != 404)

# ---------------------------------------------------------------- state, with no AI set up
clear_log()
ai_ready(False)
try:
    r = client.get("/api/learn/state")
    got = r.json()
finally:
    restore()

check("state answers 200 even with nothing set up", r.status_code, 200)
check("state carries every round as a list", isinstance(got.get("rounds"), list))
check("state says whether a round may start", "can_run" in got)
check("state says why not, in a sentence", bool(got.get("why_not")))
check("and the sentence names where to fix it", "Settings, AI" in got["why_not"])
check("state carries the settings a round may touch", "style" in got.get("settings", {}))
check("state carries the clip length too", "clip_len" in got.get("settings", {}))

# ---------------------------------------------------------------- run, refused with a sentence
clear_log()
ai_ready(False)
try:
    r = client.post("/api/learn/run", json={})
finally:
    restore()
check("run is refused when the AI is not set up, not a 500", r.status_code, 400)
check("and the refusal is a sentence", "Settings, AI" in r.json().get("detail", ""))

# ---------------------------------------------------------------- run, with no channel connected
clear_log()
ai_ready(True)
no_channel()
try:
    r = client.post("/api/learn/run", json={"days": 28})
    quiet = r.json()
finally:
    restore()

check("a round with no channel answers 200", r.status_code, 200)
check("it changed nothing", quiet.get("applied"), [])
check("it says what the numbers were", isinstance(quiet.get("facts"), list))
check("it never claims an improvement", quiet.get("effect"), "Nothing was changed, so there is no effect "
                                                            "to look for.")
check("it names the missing channel",
      "No YouTube channel is connected" in (quiet.get("facts") or [""])[0])
check("a round reports the changes it kept", quiet.get("changes"), [])
check("a round reports the ones it dropped", quiet.get("dropped"), [])
check("a round says which model answered, if any", quiet.get("model", "missing"), None)
check("a round records the settings from before it ran", "style" in quiet.get("before", {}))

# ---------------------------------------------------------------- a day count PeakCut does not offer
clear_log()
ai_ready(True)
no_channel()
try:
    r = client.post("/api/learn/run", json={"days": 13})
finally:
    restore()
check("a day count PeakCut does not offer still answers", r.status_code, 200)
check("and falls back to the 28 day window", r.json().get("days"), 28)

# ---------------------------------------------------------------- a body that is not a number
for body in ({"days": "not a number"}, {"days": None}, {"days": [1, 2]}, []):
    clear_log()
    ai_ready(True)
    no_channel()
    try:
        r = client.post("/api/learn/run", json=body)
    finally:
        restore()
    check(f"run with {body!r} answers, never a 500", r.status_code in (200, 400))

# ---------------------------------------------------------------- a second round straight after
clear_log()
with ctx.as_user("u_local"):
    path = learn._file("u_local")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rounds": [{"at": time.time(), "changes": [], "applied": []}],
                                "current": None}), encoding="utf-8")
ai_ready(True)
no_channel()
try:
    r = client.post("/api/learn/run", json={"days": 28})
finally:
    restore()
check("a round straight after another is a 400", r.status_code, 400)
check("and says when the next one may start", "next round can start in" in r.json().get("detail", ""))

# ---------------------------------------------------------------- undo, with nothing to undo
clear_log()
r = client.post("/api/learn/undo", json={})
check("undo with nothing to undo is a 400, not a 500", r.status_code, 400)
check("and says so", "nothing to undo" in r.json().get("detail", ""))

# ---------------------------------------------------------------- undo, of a round that kept no before
with ctx.as_user("u_local"):
    path = learn._file("u_local")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rounds": [{"at": 500.0, "changes": [{"setting": "style"}]}],
                                "current": None}), encoding="utf-8")
r = client.post("/api/learn/undo", json={})
check("undo of a round with no earlier state is a 400", r.status_code, 400)
check("and says the settings were not kept", "were not kept" in r.json().get("detail", ""))

# ---------------------------------------------------------------- undo, of a real round
clear_log()
with ctx.as_user("u_local"):
    from studio import brand

    doc = brand.defaults()
    doc["style"] = "bounce"
    brand.save("u_local", doc)
    path = learn._file("u_local")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rounds": [{"at": 900.0, "changes": [{"setting": "style",
                                                                     "value": "beast"}],
                                            "before": {"style": "bounce", "hook_words": "",
                                                       "captions_always": True}}], "current": None}),
                   encoding="utf-8")
r = client.post("/api/learn/undo", json={"at": 900.0})
check("undo of a real round answers 200", r.status_code, 200)
check("and reports the settings it put back", r.json().get("settings", {}).get("style"), "bounce")
with ctx.as_user("u_local"):
    check("and the style really went back on disk", brand.load("u_local")["style"], "bounce")

r = client.post("/api/learn/undo", json={"at": "not a time"})
check("undo with a time that is not a number is a 400", r.status_code, 400)

# ---------------------------------------------------------------- where the log lives
check("the engine keeps its log inside the person's own folder",
      str(config.user_dir("learn_test_user")) in str(learn._file("learn_test_user")))
check("and that file is named learn.json", learn._file("learn_test_user").name, "learn.json")

# ---------------------------------------------------------------- wave 3: the five new routes
# These are the routes the second half of the wave registered. They must exist, answer 200 with the
# shape the page draws, and refuse a bad body with a sentence rather than a 500. Nothing here needs a
# key or a network: with the AI switched off each route answers its empty shape.
clear_log()
ai_ready(False)
try:
    for path, method in (("/api/learn/signals", "get"), ("/api/learn/arms", "get"),
                         ("/api/learn/arms", "post"), ("/api/learn/arms", "delete"),
                         ("/api/learn/cost", "get")):
        r = getattr(client, method)(path, **({"json": {}} if method == "post" else {}))
        check(f"WAVE3 {method.upper()} {path} is not a missing route", r.status_code != 404)
        check(f"WAVE3 {method.upper()} {path} never answers 500 with the AI off", r.status_code < 500)

    r = client.get("/api/learn/signals")
    got = r.json()
    check("signals answers 200 with no data", r.status_code, 200)
    check("signals always carries the keys the page draws",
          [k for k in ("hook", "length", "drop", "points") if k in got],
          ["hook", "length", "drop", "points"])
    check("signals says the hook is a string, not a guess", isinstance(got.get("hook"), str))
    check("signals says drop is a shape even when it knows nothing",
          isinstance(got.get("drop"), dict) and "at" in got["drop"] and "kept" in got["drop"])
    check("signals reports points as a number", isinstance(got.get("points"), int))

    r = client.get("/api/learn/arms")
    check("arms answers 200 with no trial", r.status_code, 200)
    check("arms says there is no trial rather than inventing one", r.json().get("trial"), None)

    r = client.post("/api/learn/arms", json={"target": "not_a_setting"})
    check("arms refuses a setting PeakCut does not have", r.status_code, 400)
    check("and names the settings it can try", "style" in r.json().get("detail", ""))
    check("and the refusal is a sentence, not a stack trace", "Traceback" not in r.json().get("detail", ""))

    r = client.post("/api/learn/arms", json={"target": "style", "other": "style"})
    check("arms refuses the same setting twice", r.status_code, 400)
    check("and says why that cannot answer anything", "two different settings" in r.json().get("detail", ""))

    r = client.post("/api/learn/arms", json={"target": "style", "value": "calm",
                                             "other": "hook_words", "other_value": "short"})
    check("arms starts a real trial", r.status_code, 200)
    trial = r.json().get("trial") or {}
    check("and the trial remembers both settings", (trial.get("target"), trial.get("other")),
          ("style", "hook_words"))
    check("and the trial remembers both values", (trial.get("value"), trial.get("other_value")),
          ("calm", "short"))
    check("and the trial starts on arm a", trial.get("arm"), "a")

    r = client.get("/api/learn/arms")
    check("arms reads the trial back after it was saved", (r.json().get("trial") or {}).get("target"), "style")

    r = client.delete("/api/learn/arms")
    check("arms deletes the trial", r.status_code, 200)
    check("and the trial is gone", r.json().get("trial"), None)
    r = client.get("/api/learn/arms")
    check("and reading it again says there is none", r.json().get("trial"), None)

    r = client.get("/api/learn/cost")
    got = r.json()
    check("cost answers 200", r.status_code, 200)
    check("cost counts the calls as a number", isinstance(got.get("calls"), int))
    check("cost counts the tokens as a number", isinstance(got.get("tokens"), int))
    check("cost carries the sentence the page shows", bool(got.get("report")))
    check("and the sentence names the rounds left", "rounds left today" in got.get("report", ""))

    r = client.get("/api/learn/signals?days=90&seconds=12.5")
    check("signals accepts the days and length the page sends", r.status_code, 200)
    check("and still answers the keys the page draws",
          [k for k in ("hook", "length", "drop", "points") if k in r.json()],
          ["hook", "length", "drop", "points"])
finally:
    restore()
    clear_log()

print()
if bad:
    print(f"{len(bad)} check(s) failed")
    for line in bad:
        print("  " + line)
    sys.exit(1)
print(f"All checks passed. {ok} ok")
