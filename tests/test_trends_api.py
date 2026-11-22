#!/usr/bin/env python
"""The Trends routes answer in the shape the Trends page draws, with and without YouTube.

Two jobs. First, every route in `studio/api_trends.py` answers and none of them is missing, so a
page cannot draw an empty card because a path was renamed. Second, with no YouTube connection the
routes answer with an empty list and a sentence that says why. That matters more here than on most
pages: there is no local copy of what people search on YouTube, so the only honest answer without a
connection is "nothing, and here is why". A page that got a 500 there would have to guess, and a
guess is a made-up number.

The saved search terms are PeakCut's own list, so they must work with no connection at all. They are
kept in this test's own data folder, `tests/trends-data`, never in the folder the live server reads.

    python tests/test_trends_api.py

Run against a fresh folder, so the empty-list checks mean something.
"""
import json
import os
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "trends-data"
DATA.mkdir(exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)
os.environ["PEAKCUT_FETCH_MODEL"] = "0"
os.environ["PEAKCUT_UPDATE_CHECK"] = "0"
os.environ["PEAKCUT_ACCOUNTS"] = "0"
os.environ["PEAKCUT_PUBLIC_URL"] = "http://127.0.0.1:8765"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from studio import accounts, config, ctx, db, server  # noqa: E402

db.init()

BASE = "http://127.0.0.1:8765"
CLIENT = TestClient(server.app, base_url=BASE, follow_redirects=False)

ME = "u_local"                      # the single owner a PeakCut with accounts off signs itself in as
SAVED = config.user_dir(ME) / "trends.json"
ROUTES = ("/api/trends/status",
          "/api/trends/searches?days=28",
          "/api/trends/videos?days=28",
          "/api/trends/saved")


def call(method, path, **kw):
    """One route, as the single-user install would call it."""
    with ctx.as_user(ME):
        r = CLIENT.request(method, path, **kw)
    kind = r.headers.get("content-type", "")
    return r.status_code, (r.json() if kind.startswith("application/json") else r.text)


def get(path):
    """One GET, the shape the Analytics tests use."""
    return call("GET", path)


@contextmanager
def no_connection():
    """A PeakCut with no YouTube account connected, which is how this test folder starts."""
    real = accounts.youtube_token
    accounts.youtube_token = lambda: ""
    try:
        yield
    finally:
        accounts.youtube_token = real


def forget_saved():
    """Start from no saved terms, whatever an earlier run left in this folder."""
    SAVED.unlink(missing_ok=True)


def write_file(text):
    """Put this exact text in the saved-terms file, as a hand edit would."""
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    SAVED.write_text(text, encoding="utf-8")


def a_sentence(where, text):
    """A reason a person can read, not a stack trace and not a bare code."""
    said = str(text or "")
    assert len(said) > 40, "%s must say why in a sentence, got %r" % (where, said)
    assert "Traceback" not in said and "File \"" not in said, \
        "%s leaked an exception instead of a sentence: %r" % (where, said)
    return said


# ---- every route is mounted and answers ------------------------------------
def test_every_route_answers():
    """A renamed path answers 404, and the card that reads it would sit empty with no reason."""
    with no_connection():
        for path in ROUTES:
            code, body = get(path)
            assert code != 404, "%s is not mounted, answered 404: %s" % (path, body)
            assert code == 200, "%s answered %s: %s" % (path, code, body)


def test_no_connection_is_an_empty_list_and_a_note():
    """No YouTube means no search terms. The route says so instead of inventing rows."""
    forget_saved()
    with no_connection():
        code, body = get("/api/trends/status")
        assert code == 200, code
        assert body.get("connected") is False, "nothing is connected, so connected must be false: %r" % (body,)
        a_sentence("/api/trends/status", body.get("note"))

        before = datetime.now(timezone.utc).date()
        code, body = get("/api/trends/searches?days=28")
        after = datetime.now(timezone.utc).date()
        assert code == 200, code
        assert body.get("rows") == [], "no connection must mean no rows, got %r" % (body.get("rows"),)
        assert body.get("source") == "peakcut", \
            "rows did not come from YouTube, so the source is PeakCut's own: %r" % (body.get("source"),)
        assert body.get("days") == 28, body
        a_sentence("/api/trends/searches", body.get("note"))
        assert body.get("end") in (before.isoformat(), after.isoformat()), \
            "the range must end today, got %r" % (body.get("end"),)
        span = (date.fromisoformat(body["end"]) - date.fromisoformat(body["start"])).days
        assert span == 27, "28 days up to and including today is a 27 day span, got %d" % span

        code, body = get("/api/trends/searches?days=0")
        assert code == 200, code
        span = (date.fromisoformat(body["end"]) - date.fromisoformat(body["start"])).days
        assert span == 3649, "a lifetime range asks for the whole channel, got %d day(s)" % span

        code, body = get("/api/trends/videos?days=28")
        assert code == 200, code
        assert body.get("rows") == [], "no connection must mean no videos, got %r" % (body.get("rows"),)
        assert body.get("days") == 28, body
        assert body.get("start") and body.get("end"), body
        a_sentence("/api/trends/videos", body.get("note"))

        code, body = get("/api/trends/saved")
        assert code == 200, code
        assert body.get("terms") == [], "a fresh list is an empty list, got %r" % (body.get("terms"),)


# ---- saving a term is PeakCut's own list, no YouTube needed ----------------
def test_a_saved_term_comes_back():
    forget_saved()
    code, body = call("POST", "/api/trends/saved", json={"term": "  clip a stream  "})
    assert code == 200, "saving a good term answered %s: %s" % (code, body)
    assert body.get("terms") == ["clip a stream"], "the term must come back trimmed: %r" % (body,)
    assert SAVED.exists(), "the saved list must reach disk, or a restart would lose it"
    assert "clip a stream" in SAVED.read_text(encoding="utf-8"), \
        "the file holds the term as typed, trimmed: %r" % (SAVED.read_text(encoding="utf-8"),)

    code, body = get("/api/trends/saved")
    assert code == 200 and body.get("terms") == ["clip a stream"], body

    on_disk = json.loads(SAVED.read_text(encoding="utf-8"))
    assert on_disk.get("terms") == ["clip a stream"], "the file holds the list: %r" % (on_disk,)

    code, body = call("POST", "/api/trends/saved", json={"term": "second one"})
    assert code == 200, code
    assert body["terms"] == ["second one", "clip a stream"], "newest first: %r" % (body["terms"],)

    code, body = call("POST", "/api/trends/saved", json={"term": "CLIP a stream"})
    assert code == 200, code
    assert body["terms"] == ["CLIP a stream", "second one"], \
        "a repeat is one entry, matched without regard to case: %r" % (body["terms"],)


def test_a_blank_term_is_refused():
    forget_saved()
    refused = (("spaces", {"term": "   "}),
               ("missing", {}),
               ("null", {"term": None}),
               ("a tab and a newline", {"term": "\n\t "}),
               ("a number", {"term": 0}))
    for label, payload in refused:
        code, body = call("POST", "/api/trends/saved", json=payload)
        assert code == 400, "%s must be refused with 400, got %s: %s" % (label, code, body)
        said = str(body.get("detail") or "")
        assert len(said) > 20 and " " in said, "the refusal explains itself in words: %r" % (body,)
        assert "Traceback" not in said and "ValueError" not in said, body

    code, body = call("POST", "/api/trends/saved", json=["not", "an", "object"])
    assert code == 400, "a JSON array is not a saved term, got %s: %s" % (code, body)

    code, body = call("POST", "/api/trends/saved", content=b"not json at all",
                      headers={"content-type": "application/json"})
    assert code == 400, "a body that is not JSON is refused, got %s: %s" % (code, body)

    code, body = call("POST", "/api/trends/saved", json={"term": "x" * 121})
    assert code == 400, "a term past the cap is refused, not cut: got %s: %s" % (code, body)
    assert "120" in str(body.get("detail") or ""), "the refusal names the limit: %r" % (body,)

    code, body = get("/api/trends/saved")
    assert body.get("terms") == [], "none of those refusals stored anything: %r" % (body,)


def test_a_saved_term_can_be_deleted():
    forget_saved()
    for term in ("alpha", "beta"):
        code, body = call("POST", "/api/trends/saved", json={"term": term})
        assert code == 200, (code, body)

    code, body = call("DELETE", "/api/trends/saved?term=BETA")
    assert code == 200, "removing a saved term answered %s: %s" % (code, body)
    assert body.get("terms") == ["alpha"], "the term goes, the rest stays: %r" % (body,)

    code, body = call("DELETE", "/api/trends/saved?term=never%20saved%20this")
    assert code == 200, "removing a term that is not there is not an error: %s" % (body,)
    assert body.get("terms") == ["alpha"], "and it leaves the list alone: %r" % (body,)

    code, body = call("DELETE", "/api/trends/saved")
    assert code == 400, "a delete with no term named is refused, got %s: %s" % (code, body)
    assert "Traceback" not in str(body.get("detail") or ""), body

    code, body = get("/api/trends/saved")
    assert body.get("terms") == ["alpha"], "that refusal must not empty the list: %r" % (body,)
    forget_saved()


# ---- a hand-edited or broken file must not break the page ------------------
def test_a_junk_trends_file_still_answers():
    for junk, label in (("{not json at all", "half an object"),
                        ('{"terms": "not a list"}', "terms that is a string"),
                        ("null", "null"),
                        ("", "an empty file"),
                        ("\x00\x01\x02", "bytes that are not text")):
        write_file(junk)
        code, body = get("/api/trends/saved")
        assert code == 200, "%s must read as nothing saved, answered %s: %s" % (label, code, body)
        assert body.get("terms") == [], "%s reads as an empty list, got %r" % (label, body.get("terms"))

    write_file('["clip a stream", "", "clip a stream", "  second  "]')
    code, body = get("/api/trends/saved")
    assert code == 200, code
    assert body.get("terms") == ["clip a stream", "second"], \
        "a hand-written bare list is still read, blanks and repeats dropped: %r" % (body,)

    code, body = call("POST", "/api/trends/saved", json={"term": "third"})
    assert code == 200, "saving on top of a hand-written file answered %s: %s" % (code, body)
    assert body["terms"][0] == "third" and "clip a stream" in body["terms"], body
    forget_saved()


def test_a_range_past_the_cap_is_refused():
    """PeakCut refuses a range it cannot serve rather than quietly serving another one."""
    with no_connection():
        for path in ("/api/trends/searches?days=99999",
                     "/api/trends/searches?days=-1",
                     "/api/trends/searches?limit=999",
                     "/api/trends/videos?days=99999",
                     "/api/trends/videos?limit=0"):
            code, body = get(path)
            assert code in (400, 422), "%s must be refused, answered %s: %s" % (path, code, body)


def test_google_refusing_a_connected_account_is_not_a_500():
    """A connected channel whose read fails gets a sentence, not a stack trace and not a zero.

    The rows are empty either way, but the reason is different and the page shows the reason. A 500
    here would leave the page with nothing to say, and a row of zeros would be a number nobody sent.
    """
    import studio.api_trends as trends

    class Refused(Exception):
        code = 403

    def refuse(*a, **kw):
        raise Refused("Insufficient Permission")

    real_analytics = trends.ytstats.analytics
    real_token = accounts.youtube_token
    trends.ytstats.analytics = refuse
    accounts.youtube_token = lambda: "a-token"
    try:
        code, body = get("/api/trends/status")
        assert code == 200, "a refused token answers 200 with a reason, got %s: %s" % (code, body)
        assert body.get("connected") is True, "the account is connected even if the read failed: %r" % (body,)
        a_sentence("/api/trends/status", body.get("note"))

        code, body = get("/api/trends/searches?days=7")
        assert code == 200, "a refused search-term read answers 200, got %s: %s" % (code, body)
        assert body.get("rows") == [], "a failed read has no rows, got %r" % (body.get("rows"),)
        assert body.get("source") == "youtube", \
            "the read was attempted against YouTube, so the source says so: %r" % (body.get("source"),)
        a_sentence("/api/trends/searches", body.get("note"))
        assert body.get("note") != trends._NO_CONNECTION, \
            "an account is connected here, so the note must not claim otherwise"

        code, body = get("/api/trends/videos?days=7")
        assert code == 200, "a refused video read answers 200, got %s: %s" % (code, body)
        assert body.get("rows") == [], "a failed read has no rows, got %r" % (body.get("rows"),)
        a_sentence("/api/trends/videos", body.get("note"))
    finally:
        trends.ytstats.analytics = real_analytics
        accounts.youtube_token = real_token
        trends._CACHE.clear()


def main():
    tests = [(name, fn) for name, fn in list(globals().items())
             if name.startswith("test_") and callable(fn)]
    ok, bad = [], []
    for name, fn in tests:
        try:
            fn()
        except AssertionError as e:
            bad.append(name)
            print("FAIL " + name + "   " + str(e)[:400])
        except Exception as e:  # noqa: BLE001  - a crash here is a failure of this file
            bad.append(name)
            print("FAIL " + name + "   " + type(e).__name__ + ": " + str(e)[:400])
        else:
            ok.append(name)
            print("ok   " + name)

    print()
    if bad:
        print("%d check(s) failed" % len(bad))
        for b in bad:
            print("  - " + b)
        sys.exit(1)
    print("All checks passed. %d ok" % len(ok))


if __name__ == "__main__":
    main()
