"""A clip sent through Zernio carries its video and is published now, and "posted" means Zernio published it.

The first clips sent through Zernio (2026-11-23) reached it as posts with no video and no "publish now", which
Zernio saves as an empty draft: nothing appeared on Instagram or YouTube while the page said "posted".
No network: every request is caught before it leaves."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import zernio

FAILED = []


def check(name, ok, why=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({why})"))
    if not ok:
        FAILED.append(name)


class Resp:
    def __init__(self, code, body):
        self.status_code, self._body, self.text, self.headers = code, body, "", {}

    def json(self):
        return self._body


def answer(status, platform_status, url="", err=""):
    row = {"platform": "youtube", "status": platform_status}
    if url:
        row["platformPostUrl"] = url
    if err:
        row["errorMessage"] = err
    return {"post": {"_id": "p1", "status": status, "mediaItems": [{"type": "video"}], "platforms": [row]}}


def main():
    sent = []
    real = (zernio.httpx.request, zernio.key, zernio.accounts)
    zernio.key = lambda: "k"
    zernio.accounts = lambda k=None: [{"id": "zernio:yt1", "platform": "youtube"}, {"id": "zernio:ig1", "platform": "instagram"}]
    reply = [Resp(201, answer("published", "published", "https://youtube.com/shorts/abc"))]
    zernio.httpx.request = lambda method, url, headers=None, timeout=None, **kw: sent.append(
        {"url": url, "timeout": timeout, **kw}) or reply[0]
    try:
        got = zernio.post("https://media.zernio.com/clip.mp4", "caption", ["zernio:yt1"], title="Speed Loses It")
        body = sent[-1]["json"]
        check("the video is attached to the post", body.get("mediaItems") == [{"type": "video", "url": "https://media.zernio.com/clip.mp4"}], body)
        check("it is published now, not kept as a draft", body.get("publishNow") is True and "isDraft" not in body, body)
        check("YouTube gets the clip's title", body["platforms"][0].get("platformSpecificData", {}).get("title") == "Speed Loses It", body)
        check("publishing now is given time to finish", sent[-1]["timeout"] >= 300, sent[-1]["timeout"])
        check("the link on the platform is kept", got["url"] == "https://youtube.com/shorts/abc", got)

        zernio.post("https://media.zernio.com/clip.mp4", "c", ["zernio:ig1"], title="t")
        check("Instagram is not sent a YouTube title", "platformSpecificData" not in sent[-1]["json"]["platforms"][0], sent[-1]["json"])

        zernio.post("https://media.zernio.com/clip.mp4", "c", ["zernio:yt1"], when="2026-12-01T10:00:00Z")
        check("a post for later is scheduled, not published now", "publishNow" not in sent[-1]["json"]
              and sent[-1]["json"].get("scheduledFor"), sent[-1]["json"])

        for status, plat, err, name in (("draft", "pending", "", "a draft"),
                                        ("failed", "failed", "Video is too long for a Reel", "a failure")):
            reply[0] = Resp(201, answer(status, plat, err=err))
            try:
                zernio.post("https://media.zernio.com/clip.mp4", "c", ["zernio:yt1"])
                check(f"{name} is never called posted", False)
            except zernio.ZernioError as e:
                check(f"{name} is never called posted", True)
                if err:
                    check("and the platform's reason is shown", err in str(e), str(e))

        reply[0] = Resp(207, answer("partial", "processing"))
        try:
            zernio.post("https://media.zernio.com/clip.mp4", "c", ["zernio:yt1"])
            check("a partly published post with no link is not called posted", False)
        except zernio.ZernioError:
            check("a partly published post with no link is not called posted", True)

        reply[0] = Resp(201, answer("publishing", "processing"))
        got = zernio.post("https://media.zernio.com/clip.mp4", "c", ["zernio:yt1"])
        check("a post still being published is accepted (its link is fetched later)", got["status"] == "publishing", got)

        try:
            zernio.post("", "c", ["zernio:yt1"])
            check("a post with no uploaded video is refused", False)
        except zernio.ZernioError:
            check("a post with no uploaded video is refused", True)

        reply[0] = Resp(200, answer("published", "published", "https://instagram.com/reel/x"))
        check("a post's status reads the platform link", zernio.status("p1")["url"] == "https://instagram.com/reel/x")
    finally:
        zernio.httpx.request, zernio.key, zernio.accounts = real
    src = (Path(zernio.__file__).parent / "posting.py").read_text(encoding="utf-8")
    check("the post queue passes the clip's title", 'zernio.post(media, text, [acc["id"]], timezone_name="UTC", title=title)' in src)
    check("a post with no link yet is looked up again", "zernio.status(p[\"zernio_post\"])" in src)
    print()
    if FAILED:
        print(f"{len(FAILED)} failed: " + ", ".join(FAILED))
        raise SystemExit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
