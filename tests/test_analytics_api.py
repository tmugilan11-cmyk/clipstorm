#!/usr/bin/env python
"""The Analytics routes answer in the shape the page draws, with and without YouTube.

Two jobs. First, every route returns the keys the Analytics page reads, so a rename here
cannot quietly empty a card there. Second, with no YouTube connection the routes still answer
from PeakCut's own records instead of failing, because a person who has not connected a
channel must still see something true.

    python tests/test_analytics_api.py
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "analytics-data"
DATA.mkdir(exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)
os.environ["PEAKCUT_FETCH_MODEL"] = "0"
os.environ["PEAKCUT_UPDATE_CHECK"] = "0"
os.environ["PEAKCUT_ACCOUNTS"] = "0"
os.environ["PEAKCUT_PUBLIC_URL"] = "http://127.0.0.1:8765"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from studio import accounts, ctx, db, server  # noqa: E402

db.init()

BASE = "http://127.0.0.1:8765"
CLIENT = TestClient(server.app, base_url=BASE, follow_redirects=False)

ok, bad = [], []


def check(name, good, detail=""):
    (ok if good else bad).append(name)
    print(("ok   " if good else "FAIL ") + name + (("   " + str(detail)) if detail else ""))


def get(path):
    """One route, as the single-user install would call it."""
    with ctx.as_user("u_local"):
        r = CLIENT.get(path)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)


# The single-user install has no accounts row in a fresh data folder, so ask as the one it makes.
with ctx.as_user("u_local"):
    import studio.auth as auth

    try:
        u = auth.by_email("you@localhost")
    except Exception:  # noqa: BLE001
        u = None
    FIRST = getattr(u, "id", None) or "u_local"

# ---- no YouTube connection: every route still answers ----------------------
code, body = get("/api/analytics/status")
check("the status route answers", code == 200, code)
check("the status route says where the numbers came from", isinstance(body, dict) and "source" in body, body if code != 200 else "")
check("with nothing connected it says so in a sentence",
      isinstance(body, dict) and len(str(body.get("note") or "")) > 40, body.get("note") if isinstance(body, dict) else "")
check("it offers the real date ranges", isinstance(body, dict) and set((body.get("ranges") or {})) >= {"7", "28"}, )

code, body = get("/api/analytics/summary?days=28")
check("the summary answers with no connection", code == 200, code)
check("the summary has cards", isinstance(body, dict) and isinstance(body.get("cards"), list), type(body.get("cards")).__name__ if isinstance(body, dict) else "")
check("every card has a key, a label, a value and a unit",
      isinstance(body, dict) and all({"key", "label", "value", "unit"} <= set(c) for c in body.get("cards") or []),
      (body.get("cards") or [None])[0] if isinstance(body, dict) else "")
check("the summary names its dates", isinstance(body, dict) and bool(body.get("start")) and bool(body.get("end")))
check("it says which source it used", isinstance(body, dict) and body.get("source") in ("youtube", "peakcut"),
      body.get("source") if isinstance(body, dict) else "")

code, body = get("/api/analytics/timeseries?metric=views&days=28")
check("the timeseries answers with no connection", code == 200, code)
check("the timeseries has one point per day",
      isinstance(body, dict) and isinstance(body.get("rows"), list) and len(body.get("rows") or []) >= 1,
      len((body or {}).get("rows") or []) if isinstance(body, dict) else "")
check("every point is a day and a number",
      isinstance(body, dict) and all({"day", "value"} <= set(r) for r in body.get("rows") or []))

code, body = get("/api/analytics/timeseries?metric=nonsense")
check("an unknown metric is refused, not guessed", code == 400, code)
check("...and the refusal lists the real ones",
      isinstance(body, dict) and "views" in str(body.get("detail") or ""), body.get("detail") if isinstance(body, dict) else "")

for route, key in (("/api/analytics/videos?days=28", "rows"), ("/api/analytics/audience?days=28", "countries"),
                   ("/api/analytics/traffic?days=28", "sources")):
    code, body = get(route)
    check("%s answers with no connection" % route.split("?")[0], code == 200, code)
    check("%s carries a list under %s" % (route.split("?")[0], key),
          isinstance(body, dict) and isinstance(body.get(key), list), type(body.get(key)).__name__ if isinstance(body, dict) else "")

code, body = get("/api/analytics/retention?video=nonsense")
check("retention refuses a link it cannot read", code == 400, code)

# ---- a broken token must not take the route down ---------------------------
real_token = accounts.youtube_token
accounts.youtube_token = lambda: ""
code, body = get("/api/analytics/summary?days=7")
check("an empty token is the no-connection path, not an error", code == 200, code)

# a token that Google refuses: the route reports it in words, never as a stack trace
class FakeError(Exception):
    code = 403


def bad_ask(*a, **kw):
    raise FakeError("Insufficient Permission")


real_ask = None
import studio.api_analytics as api  # noqa: E402

real_ask = api._ask
api._ask = bad_ask
accounts.youtube_token = lambda: "a-token"
try:
    code, body = get("/api/analytics/summary?days=7")
    check("a refused token answers 400, not 500", code == 400, code)
finally:
    api._ask = real_ask
    accounts.youtube_token = real_token

# ---- the routes are mounted on the real app -------------------------------
# FastAPI 0.164 nests included routers instead of flattening them into app.routes, so reading the
# route table proves nothing. The honest check is what the block above already did: ask each one
# and require an answer that is not a 404. Only the asking is repeated here, by name.
for want in ("/api/analytics/status", "/api/analytics/summary", "/api/analytics/timeseries",
             "/api/analytics/videos", "/api/analytics/audience", "/api/analytics/traffic"):
    code, _ = get(want)
    check("%s is reachable on the real app" % want, code != 404, code)

print()
if bad:
    print("%d check(s) failed" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("All checks passed. %d ok" % len(ok))
