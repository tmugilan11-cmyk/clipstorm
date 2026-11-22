#!/usr/bin/env python
"""The Insights page is one shell plus a folder of plug-ins, and every one fits.

`web/feat/analytics.js` draws the frame: the title row, the range picker and the tabs,
the Trends tab among them. Each `web/feat/analytics-*.js` fills one box in that frame.
This checks the whole set without a browser: each file parses, registers exactly one
plug-in named after itself, asks only the server routes that exist, and never reaches
for an absolute origin if the page moves.

    python tests/test_insights_pages.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAT = ROOT / "web" / "feat"
STUDIO = ROOT / "studio"
SHELL = FEAT / "analytics.js"

# The route decorators this app actually uses. Router files are mounted with no prefix,
# so a decorated path is the path the browser asks for. Every verb counts: `api_trends.py`
# answers GET, POST and DELETE on /api/trends/saved, and a scan that kept only the paths
# would record that as one route when the app really has three. `put` and `patch` count
# too — `api_review.py` decides a clip with PATCH and `server.py` receives an upload part
# with PUT, and neither was visible to a scan that knew only get, post and delete.
# Group 1 is the verb, group 2 is the path, so a verb can be reported instead of thrown away.
ROUTE = re.compile(r"@(?:router|app)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']")

# A request path as the file writes it. It stops at the closing quote, so a literal that
# carries its own query string ("/api/analytics/summary?days=7") is caught too, and the
# query is dropped before the route comparison, because a route is matched without one.
ROOTED = re.compile(r"([\"'`])(/api/[^\"'`\s]*)\1")

ok = []
bad = []


def check(name, good, detail=""):
    (ok if good else bad).append(name)
    print(("ok   " if good else "FAIL ") + name + (("   " + str(detail)) if detail else ""))


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def strip_comments(src):
    """Comments talk about routes too, and a comment is not a request."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


def node_check(path):
    got = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, timeout=60)
    return got.returncode == 0, (got.stderr or got.stdout or "").strip()[-600:]


def route_paths():
    """Every path a studio file says it answers, with the file that says it, and the
    verbs it answers there. One path can carry several: /api/trends/saved is a GET, a
    POST and a DELETE, so counting paths alone would hide two thirds of that route."""
    routes = {}
    verbs = {}
    for p in sorted(STUDIO.glob("*.py")):
        for m in ROUTE.finditer(read(p)):
            verb, path = m.group(1).upper(), m.group(2)
            routes.setdefault(path, p.name)
            verbs.setdefault(path, set()).add(verb)
    return routes, verbs


def route_matches(url, route):
    """A route with a {param} in it answers any one segment there."""
    if url == route:
        return True
    pattern = "^" + re.sub(r"\\\{[^}]*\\\}", "[^/]+", re.escape(route)) + "$"
    return re.match(pattern, url) is not None


# ---- what the server says it answers ---------------------------------------
routes, verbs = route_paths()
check("studio files say what routes they answer", len(routes) >= 20, "%d routes" % len(routes))

# A DELETE is a route in its own right, and it is the one verb that hides: /api/trends/saved
# is decorated GET, POST and DELETE, so dropping `delete` from the pattern still leaves the
# path in the list and the loss is silent. These three checks make it loud — if the pattern
# stops matching delete, they fail instead of quietly reporting a smaller route list.
deletes = sorted(path for path, seen_verbs in verbs.items() if "DELETE" in seen_verbs)
check("the scan sees DELETE routes", "DELETE" in {v for s in verbs.values() for v in s},
      ", ".join("%s %s" % ("DELETE", d) for d in deletes) or "no DELETE decorator was read")
check("the Trends DELETE route is counted", "/api/trends/saved" in deletes,
      "DELETE /api/trends/saved from %s" % routes.get("/api/trends/saved", "an unknown file"))
check("the Trends route is counted as three verbs",
      verbs.get("/api/trends/saved") == {"GET", "POST", "DELETE"},
      ", ".join(sorted(verbs.get("/api/trends/saved", set()))) or "the route was not read at all")

# ---- every plug-in file in the Insights folder parses ----------------------
files = sorted(FEAT.glob("analytics-*.js"))
check("the Insights folder has plug-in files", len(files) >= 1, "%d files" % len(files))

for p in files:
    good, why = node_check(p)
    check("%s parses" % p.name, good, why)

# ---- each one declares exactly one plug-in, under its own name -------------
seen = {}
for p in files:
    src = strip_comments(read(p))
    names = re.findall(r"\b(?:PeakCut|P|PC)\.add\(\s*[\"']([a-z0-9\-]+)[\"']", src)
    check("%s declares one plug-in" % p.name, len(names) == 1, "found %s" % (names or "none"))
    name = names[0] if names else ""
    check("%s is named after itself" % p.name, name == p.stem,
          "" if name == p.stem else "%r is not the file name %r" % (name, p.stem))
    check("%s is the only owner of its name" % p.name, name not in seen,
          "also declared by %s" % seen.get(name) if name in seen else "")
    if name:
        seen[name] = p.name

# ---- the shell still puts the Insights page in the menu --------------------
check("analytics.js is there", SHELL.is_file())
shell_src = strip_comments(read(SHELL)) if SHELL.is_file() else ""
m = re.search(r"\b(?:PeakCut|P|PC)\.page\(\s*[\"']analytics[\"']", shell_src)
check("the Insights page is registered", m is not None, "" if m else "no PeakCut.page(\"analytics\")")
if m:
    tail = shell_src[m.end(): m.end() + 1200]
    path = re.search(r"\bpath\s*:\s*[\"']([^\"']*)[\"']", tail)
    nav = re.search(r"\bnav\s*:\s*[\"']([^\"']*)[\"']", tail)
    check("the Insights page keeps the analytics address", bool(path) and path.group(1) == "analytics",
          path.group(1) if path else "no path")
    check("the Insights page has a menu label", bool(nav) and 1 <= len(nav.group(1).strip()) <= 18,
          nav.group(1) if nav else "no nav label")

# ---- the Trends tab is still one of the tabs ------------------------------
tabs = re.search(r"TABS\s*=\s*\[(.*?)\];", shell_src, re.S)
tab_rows = re.findall(r"\{[^{}]*k\s*:\s*[\"']([a-z0-9\-]+)[\"'][^{}]*\}", tabs.group(1)) if tabs else []
check("analytics.js declares its tabs", bool(tab_rows), ", ".join(tab_rows) if tab_rows else "no TABS array")
check("the Trends tab exists", "trends" in tab_rows, "tabs are: %s" % (", ".join(tab_rows) or "none"))
trends_row = re.search(r"\{[^{}]*k\s*:\s*[\"']trends[\"'][^{}]*\}", tabs.group(1)) if tabs else None
label = re.search(r"\bl\s*:\s*[\"']([^\"']+)[\"']", trends_row.group(0)) if trends_row else None
check("the Trends tab has a label", bool(label) and label.group(1).strip() != "",
      label.group(1) if label else "no label")

# ---- every request lands on a route that exists ----------------------------
for p in files:
    src = strip_comments(read(p))
    wanted = sorted({hit[1].split("?")[0].rstrip("/") for hit in ROOTED.findall(src)})
    if not wanted:
        check("%s asks the server for nothing" % p.name, True, "draws from what is already on the page")
        continue
    missing = [u for u in wanted if not any(route_matches(u, r) for r in routes)]
    check("%s fetches only routes this server has" % p.name, not missing,
          "missing: %s" % ", ".join(missing) if missing else ", ".join(wanted))

# ---- and none of them hard-codes this machine -----------------------------
# A plug-in served from elsewhere would still work, but an origin baked into the file
# stops working the moment PeakCut is opened from another port or host.
ORIGINS = ("http://127.0.0.1", "https://127.0.0.1", "http://localhost", "https://localhost")
origin_files = [p for p in files if any(o in read(p) for o in ORIGINS)]
check("no Insights file hard-codes an origin", not origin_files,
      ", ".join(p.name for p in origin_files) if origin_files else "all paths are relative")

print()
if bad:
    print("%d check(s) failed" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("All checks passed. %d ok" % len(ok))
