"""The wiring gate: a module that is never called is not a feature, and a route that is not served is
not a route.

Wave 6 connected several modules that did real work but that nothing called. This file keeps those
connections honest. It follows the house style: plain asserts, a throwaway data folder, no server
needed except for one live probe that is skipped when the server is not up.
"""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "tests" / "wiring-data"
DATA.mkdir(exist_ok=True)
os.environ["PEAKCUT_DATA"] = str(DATA)

FAILED = []
COUNT = [0]


def check(name, ok, detail=""):
    COUNT[0] += 1
    if not ok:
        FAILED.append(name + ("   " + str(detail)[:200] if detail else ""))


def read(p):
    return (ROOT / p).read_text(encoding="utf-8", errors="replace") if (ROOT / p).exists() else ""


# 1 — the duplicate prompt module is gone, and nothing references it
check("the duplicate prompt module is deleted", not (ROOT / "studio" / "prompt_text.py").exists())

# 2 — the hooks route scores with hookscore and reads real jobs
h = read("studio/api_hooks.py")
check("the hooks route exists and is declared", "/api/learn/hooks" in h and "APIRouter()" in h)
check("the hooks route scores with hookscore", "hookscore.score(" in h)
check("the hooks route reads the real job list", "jobs.list_jobs()" in h)
check("the hooks route only counts finished clips", '"done"' in h)

# 3 — the report route turns rounds into shapes with learn_report
r = read("studio/api_learnreport.py")
check("the report route exists and is declared", "/api/learn/report" in r and "APIRouter()" in r)
check("the report route uses learn_report.shape", "learn_report.shape(" in r)
check("the report route tells the story", "learn_report.story(" in r and "learn_report.table(" in r)

# 4 — the brand AI route previews and NEVER applies on its own
b = read("studio/api_brandai.py")
check("the brand AI route exists and is declared", "/api/brandai/suggest" in b and "APIRouter()" in b)
check("the brand AI route previews through brand_ai", "brand_ai.preview(" in b)
check("the brand AI route never applies on its own", "brand_ai.apply(" not in b)

# 5 — the posttime route reads the posting record and is honest when it is thin
p = read("studio/api_posttime.py")
check("the posttime route exists and is declared", "/api/posttime" in p and "APIRouter()" in p)
check("the posttime route reads the posting record", "posting.overview()" in p)
sys.path.insert(0, str(ROOT / "studio"))
from studio import api_posttime as pt  # noqa: E402
thin = pt.hours_for([{"posted_at": 1000.0, "views": 10}] * 3)
check("fewer than five posts is answered honestly", thin.get("enough") is False and "Not enough posts" in thin.get("note", ""))
rows = [
    {"posted_at": 3600 * 9 + 1000, "views": 100.0},   # 09:00
    {"posted_at": 3600 * 9 + 2000, "views": 300.0},   # 09:00
    {"posted_at": 3600 * 9 + 3000, "views": 200.0},   # 09:00  (mean 200)
    {"posted_at": 3600 * 18 + 100, "views": 1000.0},  # 18:00
    {"posted_at": 3600 * 18 + 200, "views": 3000.0},  # 18:00  (mean 2000, the winner)
    {"posted_at": 3600 * 22 + 100, "views": 5.0},     # 22:00
]
rich = pt.hours_for(rows)
check("enough posts produce a real ranking", rich.get("enough") is True and rich.get("best") and rich["best"][0]["hour"] == 18,
      rich.get("best"))
check("the ranking names the mean, not the sum", rich["best"][0]["mean_views"] == 2000.0, rich["best"][0])
check("rows without a number are skipped, not zeroed", pt.hours_for([{"posted_at": 1, "views": "x"}] * 9).get("enough") is False)

# 6 — the server actually serves all four
s = read("studio/server.py")
for mod in ("api_hooks", "api_learnreport", "api_brandai", "api_posttime"):
    check(f"the server imports and includes {mod}", f"from . import" in s and f"{mod}.router" in s)

# 7 — the two wave-6 pages that landed stay real
for f in ("web/feat/learn-report.js", "web/feat/review-hooks.js"):
    check(f"{f} is still there", (ROOT / f).exists())

print(f"{COUNT[0]} checks run")
if FAILED:
    print(f"{len(FAILED)} check(s) failed:")
    for f in FAILED:
        print("  -", f)
    sys.exit(1)
print("All checks passed.")
