#!/usr/bin/env python
"""Learning from the clips' own results: the median logic, the sentences for the judge, the cache rules.

No network and no real posts: post records and numbers are faked. With zero posts and no YouTube
connection every answer is empty and nothing raises.

    PYTHONPATH=. python tests/test_own_results.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(tempfile.mkdtemp(prefix="ownres-"))
os.environ["PEAKCUT_DATA"] = str(DATA)
os.environ["PEAKCUT_FETCH_MODEL"] = "0"
os.environ["PEAKCUT_UPDATE_CHECK"] = "0"
os.environ["PEAKCUT_ACCOUNTS"] = "0"
os.environ["PEAKCUT_PUBLIC_URL"] = "http://127.0.0.1:8765"
sys.path.insert(0, str(ROOT))

from studio import accounts, ctx, own_results as o, ytstats  # noqa: E402

o.AUTO_REFRESH = False
ok, bad = [], []


def check(name, good, detail=""):
    (ok if good else bad).append(name)
    print(("ok   " if good else "FAIL ") + name + (("   " + str(detail)) if detail else ""))


U = "u_ownres"
DAY = 86400
NOW = 1_800_000_000.0


def post(i, views, age_days=10, **kw):
    """One fake measured row, posted `age_days` before NOW."""
    r = {"post": f"p{i}", "job": "j1", "clip": f"c{i}", "creator": "streamer", "platform": "youtube",
         "remote_id": f"vid{i:08d}", "posted_at": NOW - age_days * DAY, "title": f"Clip {i}", "hook": f"HOOK {i}",
         "kind": "troll", "length": 30.0, "judge_score": 80, "views": views, "likes": 5, "comments": 1}
    r.update(kw)
    return r


# ---- nothing at all: no posts, no YouTube ------------------------------------
check("no posts: collect is empty", o.collect(U, now=NOW) == [])
with ctx.as_user(U):
    check("no posts: taste_lines is empty", o.taste_lines() == [])
    check("no posts: the real post reader answers []", o._posted(U) == [])
check("no posts: the report is empty but whole", o.report(U)["rows"] == [] and o.report(U)["lines"] == [])
with ctx.as_user(U):
    st = accounts.youtube_status()
check("no connection: the status says so and nothing secret is in it",
      st["connected"] is False and "secret" not in json.dumps(st).lower(), st)
with ctx.as_user(U):
    chk = o.check_youtube(U)
check("no connection: the test button answers in words", chk["ok"] is False and len(chk["message"]) > 20, chk)

# ---- the median logic ----------------------------------------------------------
rows = [post(1, 100), post(2, 200), post(3, 300), post(4, 400), post(5, 5000), post(6, 10, age_days=0.1)]
a = o.analyse(rows, now=NOW)
by = {r["post"]: r for r in a}
check("the median is over grown-up clips only (100..5000: median 300)", by["p3"]["median"] == 300, by["p3"].get("median"))
check("vs_median is views over the median", by["p5"]["vs_median"] == round(5000 / 300, 2), by["p5"]["vs_median"])
check("a clip posted two hours ago is young and not judged", by["p6"].get("young") is True and "vs_median" not in by["p6"])
check("best first", a[0]["post"] == "p5" and [r["post"] for r in a if not r.get("young")][-1] == "p1")
two = [post(i, v, platform="youtube") for i, v in enumerate((100, 110, 120), 1)] + \
      [post(i + 10, v, platform="tiktok") for i, v in enumerate((9000, 10000, 11000), 1)]
b = {r["post"]: r for r in o.analyse(two, now=NOW)}
check("each site is compared with its own median", b["p2"]["vs_median"] == 1.0 and b["p12"]["vs_median"] == 1.0,
      (b["p2"]["vs_median"], b["p12"]["vs_median"]))
few = [post(1, 100, platform="youtube"), post(2, 500, platform="tiktok"), post(3, 900, platform="tiktok")]
c = {r["post"]: r for r in o.analyse(few, now=NOW)}
check("under three clips on a site: the all-clips median is used", c["p1"]["median"] == 500, c["p1"].get("median"))
check("a row with no view count is dropped from the analysis", len(o.analyse([post(1, None), post(2, 5)], now=NOW)) == 1)


# ---- the sentences for the judge ------------------------------------------------
def save(rows, at=NOW):
    o._write(U, {"at": at, "rows": rows, "error": "", "youtube": True})


real_time = time.time
time.time = lambda: NOW + 60          # taste_lines judges age by the real clock: put it where the fake posts are
try:
    good = post(1, 120000, title="CHAT LIED TO SPEED", kind="troll", length=34, judge_score=94, avg_view_pct=81.0)
    meh = [post(i, 1000 + i * 10) for i in range(2, 8)]
    flop = post(9, 40, title="Calm explanation", kind="talk", length=58, judge_score=88, avg_view_pct=22.0, kept_3s=0.41)
    save([good, flop] + meh)
    with ctx.as_user(U):
        lines = o.taste_lines(creator="streamer")
    check("a best performer gets a Did well sentence",
          any(l.startswith('Did well: "CHAT LIED TO SPEED" (troll, 34 s, judge gave 94)') for l in lines), lines[:2])
    check("it carries views and percent watched", any("120k views, 81% watched" in l for l in lines), lines[:1])
    check("a worst performer gets a Did badly sentence",
          any(l.startswith('Did badly: "Calm explanation" (talk, 58 s, judge gave 88)') and "41% still there at 3 s" in l
              for l in lines), lines)
    with ctx.as_user(U):
        check("the lines are plain strings, at most n", all(isinstance(l, str) for l in lines) and len(o.taste_lines(n=3)) <= 3)
        check("n=0 gives nothing", o.taste_lines(n=0) == [])

    # the judge comparison: high scores got low views
    back = [post(i, 5000 - i * 400, judge_score=50 + i * 5, kind="troll") for i in range(1, 9)]
    save(back)
    with ctx.as_user(U):
        jl = o.taste_lines()
    check("scores that predict backwards are called out", any("judge's scores" in l and "backwards" in l for l in jl), jl)
    fwd = [post(i, 500 * i, judge_score=50 + i * 5) for i in range(1, 9)]
    save(fwd)
    with ctx.as_user(U):
        jl = o.taste_lines()
    check("scores that predict are said to predict", any("predicting results so far" in l for l in jl), jl)
    calm = [post(i, 3000 + i, judge_score=70, kind="troll") for i in range(1, 5)] + \
           [post(i, 300, judge_score=90, kind="calm") for i in range(10, 14)]
    save(calm)
    with ctx.as_user(U):
        jl = o.taste_lines()
    check("a kind the judge likes but people skip is named", any("over-rates calm clips" in l for l in jl), jl)
    check("too few clips: no judge comparison", o.judge_lines(o.analyse([post(i, i * 100) for i in range(1, 5)], now=NOW)) == [])

    # creators: their own clips when there are enough, otherwise all
    mixed = [post(i, 1000 + i, creator="a") for i in range(1, 5)] + [post(i, 50000, creator="b") for i in range(5, 8)] + \
            [post(i, 10, creator="b") for i in range(8, 10)]
    save(mixed)
    with ctx.as_user(U):
        la = o.taste_lines(creator="a")
        lz = o.taste_lines(creator={"id": "nobody"})
    check("a creator with enough clips is judged on its own", all("50k" not in l for l in la), la)
    check("a creator with too few falls back to the whole channel", any("50k" in l for l in lz), lz)

    # too few measured clips: silence, not a guess
    save([post(1, 100), post(2, 100000)])
    with ctx.as_user(U):
        check("under three clips there is nothing to compare with", o.taste_lines() == [])

    # junk must never raise
    junk = [None, "x", 5, {}, {"views": "many"}, {"views": float("nan")}, {"views": True}, {"views": -3},
            {"views": 10, "posted_at": "yesterday", "title": None, "judge_score": "high", "marks": 7, "length": "long"},
            post(3, 100, title="<b>\"quote\"\n`tick`" + "x" * 500)]
    o._write(U, {"at": NOW, "rows": junk, "error": 7, "youtube": "yes"})
    with ctx.as_user(U):
        try:
            out = o.taste_lines()
            rep = o.report(U)
            fine = isinstance(out, list) and isinstance(rep, dict)
        except Exception as e:  # noqa: BLE001
            fine = False
            out = repr(e)
    check("junk in the cache never raises", fine, out if not fine else "")
    (DATA / "users" / U / "own_results.json").write_text("{ not json", encoding="utf-8")
    with ctx.as_user(U):
        check("a broken cache file reads as empty", o.taste_lines() == [] and o.report(U)["rows"] == [])
    save([post(i, 100 + i, title="<b>\"quote\"\n`tick`" + "x" * 500) for i in range(1, 6)]
         + [post(9, 90000, title="<b>\"q\"\n`t`" + "y" * 500)])
    with ctx.as_user(U):
        ls = o.taste_lines()
    check("text from a video is cleaned: no quotes, tags or newlines, and short",
          ls and all("\n" not in l and "<" not in l and "`" not in l and len(l) < 250 for l in ls), ls[:1])
finally:
    time.time = real_time

# ---- cache refresh rules -------------------------------------------------------
calls = {"posted": 0, "yt": 0}
real = (o._posted, o._numbers_youtube, o._numbers_zernio)


def fake_posted(uid):
    calls["posted"] += 1
    return [post(i, 100 * i) for i in range(1, 6)]


def fake_yt(rows, uid):
    calls["yt"] += 1
    return True


o._posted, o._numbers_youtube, o._numbers_zernio = fake_posted, fake_yt, lambda rows: None
try:
    cache = DATA / "users" / "u_cache01" / "own_results.json"
    got = o.collect("u_cache01", now=NOW)
    check("first collect does one pass and returns the measured rows", calls["posted"] == 1 and len(got) == 5, calls)
    check("...and saves them in the data folder", cache.is_file() and json.loads(cache.read_text())["at"] == NOW)
    o.collect("u_cache01", now=NOW + 3600)
    check("an hour later nothing is fetched again", calls["posted"] == 1, calls)
    o.collect("u_cache01", force=True, now=NOW + 100)
    check("a press of Refresh inside five minutes of the last pass is ignored", calls["posted"] == 1, calls)
    o.collect("u_cache01", force=True, now=NOW + 400)
    check("a press of Refresh later than that does fetch", calls["posted"] == 2, calls)
    o.collect("u_cache01", now=NOW + 400 + 6 * 3600 + 1)
    check("after six hours the next call fetches", calls["posted"] == 3, calls)

    def boom(uid):
        raise RuntimeError("disk on fire")

    o._posted = boom
    saved_before = json.loads(cache.read_text())
    got = o.collect("u_cache01", now=NOW + 40 * 3600)
    after = json.loads(cache.read_text())
    check("a failed pass keeps the old numbers", len(got) == 5 and len(after["rows"]) == len(saved_before["rows"]), len(got))
    check("...and says why beside them", "disk on fire" in after["error"], after["error"])
    check("...and does not claim to be fresh (it is tried again later)", after["at"] == saved_before["at"])
    o._posted = fake_posted
    o._busy["u_cache01"] = True
    n = calls["posted"]
    o.collect("u_cache01", force=True, now=NOW + 99 * 3600)
    check("a pass already running is not started twice", calls["posted"] == n)
    o._busy.clear()
    check("collect with a bad user id answers [] and does not raise", o.collect("??", now=NOW) == [])
finally:
    o._posted, o._numbers_youtube, o._numbers_zernio = real

# ---- the network fill-in with a faked Google -------------------------------------
fake_bulk_args = {}
real_token, real_bulk = accounts.youtube_token, ytstats.bulk
accounts.youtube_token = lambda: "tok"


def fake_bulk(token, ids, since="", retention_for=0):
    fake_bulk_args.update(token=token, ids=list(ids), since=since, n=retention_for)
    return {"videos": {ids[0]: {"views": 777, "likes": 9, "comments": 2, "averageViewPercentage": 64.2,
                                "averageViewDuration": 19.0, "kept_at_3s": 0.8}}, "error": ""}


ytstats.bulk = fake_bulk
try:
    rr = [post(1, 5, remote_id="aaaaaaaaaaa"), post(2, 6, remote_id="bbbbbbbbbbb", platform="tiktok")]
    yt = o._numbers_youtube(rr, U)
    check("YouTube numbers replace the tracked ones", yt is True and rr[0]["views"] == 777 and rr[0]["avg_view_pct"] == 64.2
          and rr[0]["kept_3s"] == 0.8 and rr[0]["source"] == "youtube", rr[0])
    check("only YouTube posts are asked about", fake_bulk_args["ids"] == ["aaaaaaaaaaa"], fake_bulk_args)
    check("a post on another site keeps its own numbers", rr[1]["views"] == 6 and "avg_view_pct" not in rr[1])
    accounts.youtube_token = lambda: ""
    rr = [post(1, 5, remote_id="aaaaaaaaaaa")]
    check("no token: YouTube is skipped quietly", o._numbers_youtube(rr, U) is False and rr[0]["views"] == 5)
finally:
    accounts.youtube_token, ytstats.bulk = real_token, real_bulk

# ytstats.bulk and kept_at with a faked Google
real_v, real_a = ytstats._videos, ytstats.analytics
ytstats._videos = lambda ids, key="", token="": [{"id": i, "views": 10, "likes": 1, "comments": 0, "seconds": 30,
                                                   "published": "2026-11-01T00:00:00Z", "title": ""} for i in ids]


def fake_an(token, start, end, metrics, dimensions="", filters="", sort="", max_results=0):
    if dimensions == "video":
        return [{"video": v, "views": 10, "averageViewDuration": 12.5, "averageViewPercentage": 41.7}
                for v in filters.replace("video==", "").split(",")]
    return [{"elapsedVideoTimeRatio": 0.05, "audienceWatchRatio": 0.9}, {"elapsedVideoTimeRatio": 0.1, "audienceWatchRatio": 0.7},
            {"elapsedVideoTimeRatio": 0.5, "audienceWatchRatio": 0.3}]


ytstats.analytics = fake_an
try:
    got = ytstats.bulk("tok", ["aaaaaaaaaaa", "bbbbbbbbbbb"], since="2026-10-30", retention_for=1)
    v1, v2 = got["videos"]["aaaaaaaaaaa"], got["videos"]["bbbbbbbbbbb"]
    check("bulk joins Data API counts with Analytics averages", v1["views"] == 10 and v1["averageViewPercentage"] == 41.7, v1)
    check("the 3-second hold is read at the nearest sample (3 s of 30 s = 10%)", v1["kept_at_3s"] == 0.7, v1)
    check("retention is read only for the newest asked-for videos", "kept_at_3s" not in v2)
    check("bulk with no token or no ids is empty and quiet", ytstats.bulk("", ["aaaaaaaaaaa"]) == {"videos": {}, "error": ""}
          and ytstats.bulk("tok", [])["videos"] == {})

    def refused(*a, **k):
        raise ytstats.YouTubeError("YouTube said 403: YouTube Analytics API has not been used in project 1 before or it is disabled.", 403)

    ytstats.analytics = refused
    got = ytstats.bulk("tok", ["aaaaaaaaaaa"], retention_for=1)
    check("a refused Analytics call keeps the Data API numbers and explains itself in words",
          got["videos"]["aaaaaaaaaaa"]["views"] == 10 and "YouTube Analytics API" in got["error"] and "switch" in got["error"], got)
finally:
    ytstats._videos, ytstats.analytics = real_v, real_a
check("explain: an expired sign-in tells the person to connect again",
      "Connect again" in ytstats.explain(RuntimeError("invalid_grant: Token has been expired or revoked")))

# ---- the connection: scopes and status ------------------------------------------------
check("scopes: an account that recorded nothing is not accused",
      accounts.youtube_scopes({}) == {"upload": None, "read": None, "analytics": None})
sc = accounts.youtube_scopes({"scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"})
check("scopes: an unticked analytics permission is seen", sc["analytics"] is False and sc["upload"] is True and sc["read"] is True, sc)
check("the connect link asks for analytics and read permission",
      "yt-analytics.readonly" in accounts.YT_SCOPES and "youtube.readonly" in accounts.YT_SCOPES and "youtube.upload" in accounts.YT_SCOPES)
check("the redirect address is the callback the server answers", accounts.redirect_for("youtube").endswith("/oauth/youtube/callback"))
with ctx.as_user(U):
    accounts._put({"id": "yt_UCfake", "platform": "youtube", "name": "Fake channel", "added": 1, "refresh_token": "r",
                   "access_token": "a", "expires": time.time() + 3000, "scope": "youtube.upload youtube.readonly"})
    st = accounts.youtube_status()
check("a connected account without analytics permission is flagged",
      st["connected"] and st["analytics_scope"] is False and st["token_ok"] is True, st)
check("the status carries no token and no secret", "access_token" not in st and "refresh_token" not in json.dumps(st))
with ctx.as_user(U):
    accounts.remove("yt_UCfake")


class Resp:
    status_code, text = 400, '{"error": "invalid_grant", "error_description": "Token has been expired or revoked."}'

    def json(self):
        return {}


import httpx  # noqa: E402

real_post = httpx.post
httpx.post = lambda *a, **k: Resp()
try:
    try:
        accounts._yt_token({"expires": 0, "refresh_token": "r", "access_token": "a", "id": "x"})
        msg = ""
    except RuntimeError as e:
        msg = str(e)
finally:
    httpx.post = real_post
check("a retired refresh token says to press Connect again", "Connect again" in msg and "seven days" in msg, msg)

# ---- the routes -------------------------------------------------------------------------
from fastapi.testclient import TestClient  # noqa: E402

from studio import db, server  # noqa: E402

db.init()
client = TestClient(server.app, base_url="http://127.0.0.1:8765", follow_redirects=False)


def ask(path, method="GET"):
    with ctx.as_user("u_local"):
        r = client.request(method, path)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)


code, body = ask("/api/own-results")
check("GET /api/own-results answers with nothing posted",
      code == 200 and body.get("rows") == [] and body.get("lines") == [], (code, str(body)[:120]))
code, body = ask("/api/own-results/youtube")
check("GET /api/own-results/youtube tells where the connection stands",
      code == 200 and {"app_ready", "redirect", "connected"} <= set(body), (code, str(body)[:120]))
check("...and shows the exact redirect address", body.get("redirect", "").endswith("/oauth/youtube/callback"))
code, body = ask("/api/own-results/youtube/test", "POST")
check("POST /api/own-results/youtube/test answers in words", code == 200 and body.get("ok") is False and body.get("message"), (code, body))
code, body = ask("/api/own-results/refresh", "POST")
check("POST /api/own-results/refresh answers at once", code == 200 and "rows" in body, (code, str(body)[:120]))
time.sleep(0.5)

print()
if bad:
    print("%d check(s) failed" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("All checks passed. %d ok" % len(ok))
