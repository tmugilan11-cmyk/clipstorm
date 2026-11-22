"""Post captions are saved text; Japanese/Chinese never become video effects.

Exercises real FastAPI routes and both publishing paths with network calls replaced.
"""
import copy
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "tests" / "ig-post-data"
DATA.mkdir(parents=True, exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from studio import api_igcaption, brand, captions, ctx, igcaption, jobs, posting, render, zernio

UID = "caption_owner"
OTHER = "other_owner"
WORDS = [{"w": "hello", "s": 0.0, "e": 0.4}, {"w": "world", "s": 0.4, "e": 0.8}]
CLIP = {"id": "clip01", "status": "done", "review": "approved", "file": "clip.mp4",
        "style": "bounce", "title": "The comeback", "description": "He won the last round.",
        "hashtags": ["gaming"], "hook": "Watch this", "start": 0, "end": 2, "fixed_words": WORDS}
job = {"id": "caption-test", "user": UID, "creator": None, "dir": str(DATA), "clips": [copy.deepcopy(CLIP)]}
jobs._jobs[job["id"]] = job
app = FastAPI()
app.include_router(api_igcaption.router)

@app.middleware("http")
async def who(request, call_next):
    uid = request.headers.get("x-test-user", UID)
    request.state.user = SimpleNamespace(id=uid, disabled=False)
    with ctx.as_user(uid):
        return await call_next(request)

client = TestClient(app)
URL = "/api/jobs/caption-test/clips/clip01/igcaption"
failed = []

def check(name, fn):
    try:
        fn()
        print("ok   " + name)
    except Exception as e:
        failed.append(name)
        print("FAIL " + name + "   " + str(e))


def no_video_effects():
    banned = {"jp-gothic", "jp-box", "jp-hand", "jp-mincho", "jp-emphasis", "cn-douyin", "cn-karaoke"}
    assert not banned.intersection(captions.style_names()), "Japanese/Chinese post looks are still video effects"
    assert brand.normalise({"style": "cn-douyin"})["style"] not in banned
    assert "Dialogue:" in render.build_ass(WORDS, 0, 2, "Watch this", "bounce", [], 300, 1380)


def route_save():
    before = copy.deepcopy(job["clips"][0])
    response = client.put(URL, json={"enabled": True, "caption": "逆転の瞬間。\n\n#ゲーム", "lang": "ja", "format": "short"})
    assert response.status_code == 200, response.text
    got = client.get(URL).json()
    assert got["caption"] == "逆転の瞬間。\n\n#ゲーム" and got["enabled"] is True, got
    assert job["clips"][0]["style"] == before["style"]
    assert job["clips"][0]["fixed_words"] == before["fixed_words"]
    assert (DATA / "job.json").is_file(), "caption was not persisted"
    posted = igcaption.for_post(job["clips"][0], {"post_footer": "footer"})
    assert posted == got["caption"], "upload text differs from saved preview"


def route_validation():
    before = copy.deepcopy(job["clips"][0])
    for body in ({"caption": "x" * 2201}, {"caption": []}, {"lang": "bad"}, {"enabled": "yes"}):
        r = client.put(URL, json=body)
        assert r.status_code == 400, r.text
    assert client.get(URL, headers={"x-test-user": OTHER}).status_code == 404
    assert client.put(URL, json={"caption": "other"}, headers={"x-test-user": OTHER}).status_code == 404
    assert job["clips"][0] == before, "a rejected update changed the clip"


def defaults_and_empty():
    assert client.put(URL, json={"enabled": True, "caption": ""}).status_code == 200
    assert igcaption.for_post(job["clips"][0], {}) == "", "empty override got replaced"
    assert client.put(URL, json={"enabled": False}).status_code == 200
    default = igcaption.for_post(job["clips"][0], {})
    assert default == "The comeback\n\nHe won the last round.\n\n#gaming", repr(default)


def generation_is_preview():
    before = copy.deepcopy(job["clips"][0])
    with patch("studio.ai.ready", return_value=True), patch("studio.ai.models", return_value=["fake"]), \
         patch("studio.ai.call", return_value=({"caption": "最后一轮的逆转。\n#游戏"}, 10, 10)) as ask:
        r = client.post(URL + "/generate", json={"lang": "zh", "format": "short"})
        assert r.status_code == 200, r.text
        assert "逆转" in r.json()["caption"]
        assert ask.call_count == 1
    assert job["clips"][0] == before, "a generation silently changed the saved caption"
    with patch("studio.ai.ready", return_value=True), patch("studio.ai.models", return_value=["fake"]), \
         patch("studio.ai.call", side_effect=RuntimeError("offline")):
        assert client.post(URL + "/generate", json={"lang": "ja"}).status_code == 502
    assert job["clips"][0] == before


def publishes_exact_saved_text():
    text = "最后一轮！\n\n#游戏"
    clip = job["clips"][0]
    clip.update(ig_caption_enabled=True, ig_caption=text)
    for relay, platform in ((False, "instagram"), (True, "instagram"), (True, "youtube")):
        acc = {"id": "zernio:one" if relay else "one", "platform": platform, "name": "Test", "zernio": relay}
        sent = []
        p = {"job": job["id"], "clip": "clip01", "account": acc["id"], "creator": None, "tries": 0}
        def native(a, path, caption, jid):
            sent.append(caption)
            return "native", "https://example.test/post"
        def through(media, caption, targets, **kw):
            sent.append(caption)
            return {"id": "relay", "url": "https://example.test/post"}
        with ctx.as_user(UID), patch.object(posting.accounts, "get", return_value=acc), \
             patch.object(posting.creators, "get", return_value={"post_footer": "footer", "privacy": "private"}), \
             patch.object(posting.creators, "log"), patch.object(posting, "_save"), patch.object(posting, "_mirror"), \
             patch.object(posting.accounts, "instagram_upload", side_effect=native), \
             patch.object(zernio, "upload", return_value="https://example.test/video"), \
             patch.object(zernio, "post", side_effect=through):
            posting._post(p)
        assert p["status"] == "posted", p
        assert len(sent) == 1
        if platform == "instagram":
            assert sent[0] == text, repr(sent[0])
        else:
            assert text not in sent[0] and "He won the last round." in sent[0], sent


if __name__ == "__main__":
    check("post-only styles never appear in video controls", no_video_effects)
    check("Japanese post text survives save and reload without changing video", route_save)
    check("bad input and another owner cannot change a caption", route_validation)
    check("empty caption and standard post text are explicit choices", defaults_and_empty)
    check("AI generation is a draft and a failure preserves the saved text", generation_is_preview)
    check("native and Zernio uploads send exactly the saved Instagram caption", publishes_exact_saved_text)
    if failed:
        raise SystemExit(1)
    print("All checks passed.")
