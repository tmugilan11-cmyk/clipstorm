"""Clip types: the plan never crashes, the catalogue tells the truth, and a drawn type really changes the clip."""
import subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio import format_finish, formats

bad = []
def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok: bad.append(name)

parts = [{"start": 2, "end": 6}, {"start": 8, "end": 12}, {"start": 14, "end": 18}]
for k in ("compilation", "escalation"):
    p = formats.plan({"format": k, "start": 0, "end": 20, "parts": parts}, [])
    check(f"{k} with parts plans without error", p["ok"] and len(p["spans"]) == 3)
rows = {r["id"]: r for r in formats.public()}
check("all eight types are listed with a sentence and a best-for line", len(rows) == 8 and all(r["line"] and r["best_for"] for r in rows.values()))
check("moment is ready", rows["moment"]["state"] == "ready")
check("types that join several moments are montages, with how many moments they take", all(rows[k]["state"] == "montage" and rows[k]["available"] and 2 <= rows[k]["min_parts"] <= rows[k]["max_parts"] <= 5 for k in formats.JOINS))
check("chat says honestly that its lines are typed, not copied from the stream", rows["chat"]["state"] == "needs_lines" and "type the lines" in rows["chat"]["reason"] and "does not keep what chat wrote" in rows["chat"]["reason"])
check("reveal says it needs a webcam (or that it is not connected)", rows["reveal"]["state"] in ("needs_webcam", "unavailable"))

tmp = Path(tempfile.mkdtemp())
src = tmp / "a.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x225588:s=1080x1920:r=30:d=4", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=mono", "-t", "4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(src)], check=True)
before = src.read_bytes()
words = [{"w": "x", "s": 0.2 * i, "e": 0.2 * i + 0.1} for i in range(20)]
plan = formats.plan({"format": "waitforit", "start": 0, "end": 4, "payoff": 3.0}, words)
r = format_finish.finish(plan, src, False)
check("wait for it is drawn onto the clip", r["applied"] and src.read_bytes() != before)
before = src.read_bytes()
r = format_finish.finish(formats.plan({"format": "reveal", "start": 0, "end": 4}, words), src, False)
check("reveal without a webcam leaves the clip alone and says why", not r["applied"] and r["skipped"] and src.read_bytes() == before)

# Chat: the typed lines pop up over the clip and change the file; without lines nothing is drawn and it says why.
src2 = tmp / "c.mp4"
src2.write_bytes(src.read_bytes())
cplan = formats.plan({"format": "chat", "start": 0, "end": 4, "payoff": 1.5, "chat": ["KEKW", "NO WAY", "CHAD"]}, words)
check("chat plans one bubble per typed line", cplan["ok"] and len(cplan["chat"]) == 3)
before = src2.read_bytes()
r = format_finish.finish(cplan, src2, False)
check("chat bubbles are drawn onto the clip", r["applied"] == ["chat"] and src2.read_bytes() != before)
before = src2.read_bytes()
r = format_finish.finish(formats.plan({"format": "chat", "start": 0, "end": 4}, words), src2, False)
check("chat with no lines leaves the clip alone and says why", not r["applied"] and "no chat messages" in r["skipped"] and src2.read_bytes() == before)

# The editor's re-make route keeps the typed lines (short, at most five) and turns a joining type into a plain clip.
from studio import jobs
jobs._jobs["tj"] = {"id": "tj", "user": "u", "dir": str(tmp), "creator": "c", "clips": [{"id": "c1", "start": 1.0, "end": 9.0, "status": "done", "style": "bounce", "layout": "blur"}]}
jobs.save = lambda job: None
jobs._q.put = lambda *a, **k: None
jobs.request_render("tj", "c1", {"format": "chat", "chat": ["  KEKW  ", "", "a" * 90, "x", "y", "z", "w"]})
c1 = jobs._jobs["tj"]["clips"][0]
check("request_render keeps at most five trimmed chat lines", c1["format"] == "chat" and len(c1["chat"]) == 5 and c1["chat"][0] == "KEKW" and len(c1["chat"][1]) == 40)
jobs.request_render("tj", "c1", {"format": "compilation"})
check("one clip cannot be set to a joining type", c1["format"] is None)
try:
    jobs.request_render("tj", "c1", {"chat": "not a list"})
    check("chat lines that are not a list are refused", False)
except ValueError:
    check("chat lines that are not a list are refused", True)
print("All checks passed." if not bad else f"{len(bad)} FAILED")
raise SystemExit(1 if bad else 0)
