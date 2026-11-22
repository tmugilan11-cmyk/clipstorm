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
check("types that join several moments say they are unavailable and why", all(rows[k]["state"] == "unavailable" and rows[k]["reason"] for k in ("callback", "compilation", "escalation", "thenvsnow", "chat")))
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
print("All checks passed." if not bad else f"{len(bad)} FAILED")
raise SystemExit(1 if bad else 0)
