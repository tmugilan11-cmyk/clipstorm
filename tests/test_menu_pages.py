#!/usr/bin/env python
"""Every page a feature file puts in the menu has what a menu row needs.

A page is registered with PeakCut.page("name", {...}). This checks each one without a
browser: the file parses, names itself, says where it is, has a label and an icon that
exists in the page's own icon map, and does not take an address another page already has.

    python tests/test_menu_pages.py
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAT = ROOT / "web" / "feat"
INDEX = ROOT / "web" / "index.html"

# The headings a page may sit under in the left menu. Small on purpose: a row in a
# heading the menu never declared sorts to the bottom, or opens a heading of its own,
# which is how a feature stops looking like part of the product. The first six come
# from the spine in web/feat/menu.js. "Set up" is what the four moved pages use
# today, so it is allowed until the spine learns that name.
ALLOWED_GROUPS = (
    "Make", "Understand", "Look and sound", "Connect", "Account", "Help", "Set up",
)

ok = []
bad = []


def check(name, good, detail=""):
    (ok if good else bad).append(name)
    print(("ok   " if good else "FAIL ") + name + (("   " + str(detail)) if detail else ""))


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


# ---- what the page itself offers -------------------------------------------
index_src = read(INDEX)
icons = set(re.findall(r'^\s*"([a-z0-9_]+)"\s*:', index_src, re.M))


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", src)


# A feature file may draw an icon the page never had: `P.icon("name", path)` adds one to
# the page's map at run time, and a plug-in may hand the loader a whole `{ icons: SET }`
# object. So the set of names a menu row may use is the page's own map plus every name a
# feature file publishes. Without this, a row that draws perfectly in the browser reads as
# broken here, which would teach people to ignore this test.
for _p in sorted(FEAT.glob("*.js")):
    _src = strip_comments(read(_p))
    icons.update(re.findall(r"\b(?:PeakCut|P|PC)\.icon\(\s*[\"']([a-z0-9_\-]+)[\"']", _src))
    for _set in re.finditer(r"\b(?:icons|SET)\s*:\s*([A-Za-z_$][\w$]*)", _src):
        block = re.search(
            r"\b(?:const|let|var)\s+" + re.escape(_set.group(1)) + r"\s*=\s*\{", _src)
        if not block:
            continue
        depth, i = 0, block.end() - 1
        while i < len(_src):
            if _src[i] == "{":
                depth += 1
            elif _src[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = _src[block.end(): i]
        icons.update(re.findall(r"^\s*[\"']?([a-z0-9_\-]+)[\"']?\s*:", body, re.M))


def pages_in(path):
    """Every PeakCut.page(...) registration in one file, as dicts of the simple keys."""
    src = strip_comments(read(path))
    found = []
    for m in re.finditer(r"\b(?:PeakCut|P|PC)\.page\(\s*[\"']([a-z0-9\-]+)[\"']", src):
        name = m.group(1)
        tail = src[m.end(): m.end() + 4000]
        row = {"name": name}
        for key in ("nav", "icon", "path", "group", "tip"):
            k = re.search(r"\b" + key + r"\s*:\s*[\"']([^\"']*)[\"']", tail)
            if k:
                row[key] = k.group(1)
        n = re.search(r"\border\s*:\s*(-?\d+)", tail)
        if n:
            row["order"] = int(n.group(1))
        found.append(row)
    return found


# ---- every file in the folder parses ---------------------------------------
files = sorted(p for p in FEAT.glob("*.js") if not p.name.startswith("_"))
check("there is at least one feature file", len(files) > 0, "%d files" % len(files))

for p in files:
    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
    check("%s parses" % p.name, r.returncode == 0, (r.stderr or "").strip().splitlines()[:1])

# ---- every page has what a menu row needs ----------------------------------
all_pages = []
for p in files:
    for row in pages_in(p):
        row["file"] = p.name
        all_pages.append(row)

check("at least one page is registered", True,
      "%d pages" % len(all_pages) if all_pages else "none yet, which is allowed: a build that adds no page adds no page")

for row in all_pages:
    n = row["name"]
    check("%s says what to call it" % n, bool(row.get("nav")))
    check("%s says where it lives" % n, bool(row.get("path")))
    check("%s has a one-line tip" % n, bool(row.get("tip")))
    check("%s has a group" % n, bool(row.get("group")))
    icon = row.get("icon") or ""
    check("%s has an icon the page knows" % n, icon in icons if icon else False, icon or "no icon")

# ---- two pages may not share an address or a name --------------------------
paths = [r.get("path") for r in all_pages if r.get("path")]
check("no two pages share an address", len(paths) == len(set(paths)),
      sorted(p for p in set(paths) if paths.count(p) > 1) or "")
names = [r["name"] for r in all_pages]
check("no two pages share a name", len(names) == len(set(names)),
      sorted(n for n in set(names) if names.count(n) > 1) or "")

# ---- a page may not live where a built-in page lives -----------------------
builtin = set(re.findall(r"\b(overview|library|settings|usage|review|creator|admin)\b", index_src[:200000]))
CLASH = {"overview", "library", "settings", "usage", "review", "admin", ""}
for r in all_pages:
    p = r.get("path") or ""
    check("%s does not take a built-in address" % r["name"], p not in CLASH, p)

# ---- a page sits under a heading the menu knows ---------------------------
# An unknown heading does not error: it quietly sorts to the bottom, or starts a
# heading that holds one row. Both look like a bug to the person reading the menu,
# so name the offending group and print the whole allowed set beside it.
for r in all_pages:
    g = r.get("group") or ""
    check("%s sits under a known heading" % r["name"], g in ALLOWED_GROUPS,
          g if g in ALLOWED_GROUPS else "%r is not one of: %s" % (g, ", ".join(ALLOWED_GROUPS)))

# ---- a page address may not shadow another feature file -------------------
# /app/heard would read as the heard feature, while being some other page. A file
# named after the page it draws stays allowed: analytics.js owning the analytics
# page is the normal shape, not a clash.
stems = {p.stem for p in FEAT.glob("*.js") if not p.name.startswith("_")}
for r in all_pages:
    p = (r.get("path") or "").strip("/")
    mine = r.get("file") == p + ".js"
    check("%s does not shadow a feature file" % r["name"], p not in stems or mine,
          p if (p not in stems or mine) else "%s is already web/feat/%s.js" % (p, p))

# ---- the pages moved out of Settings still exist -------------------------
# Each one is a real feature the main menu now owns. A missing one means it slid
# back into Settings, which is the complaint this rebuild answered.
MOVED = ("brand", "transcribe", "tools", "apps")
by_name = {r["name"]: r for r in all_pages}
for name in MOVED:
    r = by_name.get(name)
    check("%s is a page" % name, r is not None, "" if r else "no file registers it")
    if not r:
        continue
    tip = (r.get("tip") or "").strip()
    check("%s has a tip long enough to say something" % name, len(tip) >= 20,
          "" if len(tip) >= 20 else "%d chars, needs 20: %r" % (len(tip), tip))

# ---- a menu row has room for its label, and only one row may own it -------
for r in all_pages:
    nav = (r.get("nav") or "").strip()
    check("%s has a label a menu row fits" % r["name"], 1 <= len(nav) <= 18,
          "" if 1 <= len(nav) <= 18 else "%d chars, needs 1 to 18: %r" % (len(nav), nav))
labels = [(r.get("nav") or "").strip().lower() for r in all_pages]
for r in all_pages:
    nav = (r.get("nav") or "").strip().lower()
    check("%s has a label of its own" % r["name"], labels.count(nav) == 1,
          "" if labels.count(nav) == 1 else "%r is on %d pages" % (nav, labels.count(nav)))

# ---- the view is a function or a string, and it draws something ------------
for p in files:
    src = strip_comments(read(p))
    if "PeakCut.page(" not in src and not re.search(r"\b(?:P|PC)\.page\(", src):
        continue
    check("%s draws its page" % p.name, bool(re.search(r"\bview\s*[:(]", src)))

# ---- the seven rows wave 4 promised are really in the menu ----------------
# Named by what the person sees in the menu, not only by registration name: the
# brief called the Usage row "usage", while the file registers a page named
# "ai-usage" under the label "Usage". Either slug is accepted for that row, and
# every other row is matched on its label, so a rename cannot quietly delete a row.
WAVE4 = (
    ("Creators", ("creators",)),
    ("Live", ("live",)),
    ("Schedule", ("schedule",)),
    ("Help", ("help",)),
    ("Clip formats", ("formats",)),
    ("Sounds", ("sounds",)),
    ("Usage", ("usage", "ai-usage")),
)
by_name = {r["name"]: r for r in all_pages}
by_label = {(r.get("nav") or "").strip().lower(): r for r in all_pages}
for label, slugs in WAVE4:
    row = next((by_name[s] for s in slugs if s in by_name), None) or by_label.get(label.lower())
    check("the %s row is in the menu" % label, row is not None,
          "" if row else "no feature file registers a page named %s or labelled %r"
          % (" or ".join(slugs), label))
    if not row:
        continue
    check("%s row points at a feature file that exists" % label, (FEAT / row["file"]).exists(),
          row["file"])
    have = strip_comments(read(FEAT / row["file"]))
    # The file must register a plug-in; test_feat_files.py already holds it to one add()
    # named after the file. The page name may differ from the file stem (usage.js draws
    # the page named "ai-usage"), so the two are not required to match here.
    check("%s row's file registers a plug-in" % label,
          bool(re.search(r"\b(?:PeakCut|P|PC)\.add\(\s*[\"'][a-z0-9\-]+[\"']", have)),
          "no PeakCut.add(...) in %s" % row["file"])

# ---- every address a page asks for is a route the server answers ----------
# The page cannot fail loudly on a route that does not exist: it gets a 404 and the
# person sees an empty panel. So read each /api/... string out of the feature files
# and require one route in studio/ whose shape matches. "${...}" counts as one
# segment of any name, "?query" is dropped, and a base path a page concatenates
# onto (P.api("/api/jobs/" + jid)) may be the front of a longer real route.
STUDIO = ROOT / "studio"
server_routes = set()
for p in sorted(STUDIO.rglob("*.py")):
    for m in re.finditer(
        r"@(?:app|router|api)\.(?:get|post|put|patch|delete|api_route)\(\s*[\"']([^\"']+)[\"']",
        read(p),
    ):
        server_routes.add(m.group(1))
check("the server has routes to compare against", bool(server_routes), "%d routes" % len(server_routes))


def route_segments(path):
    return [s for s in path.split("/") if s]


def same_step(a, b):
    return a == b or a == "*" or b == "*" or a.startswith("{") or b.startswith("{")


def route_exists(path):
    """The first studio route that could answer this path, or None."""
    want = route_segments(path)
    for route in sorted(server_routes):
        have = route_segments(route)
        if len(have) == len(want) and all(same_step(a, b) for a, b in zip(want, have)):
            return route
        if len(have) > len(want) and all(same_step(a, b) for a, b in zip(want, have)):
            return route
    return None


asked = {}
for p in files:
    src = strip_comments(read(p))
    for m in re.finditer(r"[\"'`](/api/[^\"'`]*)[\"'`]", src):
        raw = m.group(1).split("?")[0].split("#")[0]
        raw = re.sub(r"\$\{[^}]*\}", "*", raw)
        asked.setdefault(raw, set()).add(p.name)
check("some page asks the server for something", bool(asked), "%d addresses" % len(asked))
for path in sorted(asked):
    where = ", ".join(sorted(asked[path]))
    check("route %s exists" % path, route_exists(path) is not None,
          "" if route_exists(path) else "asked by %s, no route in studio/ matches" % where)

# ---- a page escapes the values it puts into markup ------------------------
# A page that fills a template literal with a field from the server has to pass that
# field through esc(). Two checks, both kept narrow enough to be true of the repo as it
# stands, because a check that cries wolf teaches everyone to ignore the whole file:
#   1. a file that registers a menu page, and builds markup, must call esc( somewhere;
#   2. an interpolation that is a bare server-shaped field (.name, .error, .url ...) must
#      not sit inside markup unwrapped. A call such as cell(t.v, t.u, t.tip) is let
#      through, because the escaping, when it is needed, happens in that function.
# Plain locals that already hold escaped markup, and numbers, are not flagged.
TEMPLATE = re.compile(r"`[^`]*`", re.S)
SERVER_FIELD = re.compile(
    r"\.(?:name|title|label|error|message|note|email|handle|text|why|say|tip|url|href|src"
    r"|reason|detail|channel|user|platform|track|kind|status)\b"
)
page_files = sorted({r["file"] for r in all_pages})
for name in page_files:
    p = FEAT / name
    src = strip_comments(read(p))
    markup = [m.group(0) for m in TEMPLATE.finditer(src) if "<" in m.group(0)]
    if not markup:
        continue
    check("%s escapes what it puts in markup" % name, "esc(" in src,
          "" if "esc(" in src else "%d markup templates and no esc( call" % len(markup))
    loose = []
    for tpl in markup:
        for e in re.finditer(r"\$\{([^{}]*)\}", tpl):
            expr = e.group(1).strip()
            if "(" in expr or "esc(" in expr or "num(" in expr:
                continue
            if SERVER_FIELD.search(expr):
                loose.append(expr[:60])
    check("%s escapes the server fields it names" % name, not loose,
          "" if not loose else "unescaped: " + "; ".join(sorted(set(loose))[:4]))

# ---- addresses that moved -------------------------------------------------
# A bookmark saved before a page got its own menu row must still open that page. The table lives in
# index.html so that both the router and the page guard read the same list; this proves every entry
# still points at a page that exists, so a rename cannot leave a dead bookmark behind.
html = read(ROOT / "web" / "index.html")
moved = re.search(r"const MADE_CLEAN = \{(.*?)\};", html, re.S)
check("the moved addresses are written down where the router can read them", bool(moved),
      "" if moved else "no MADE_CLEAN table in web/index.html")
if moved:
    pairs = re.findall(r'"(/app/[a-z\-/]+)"\s*:\s*"([a-z\-]+)"', moved.group(1))
    check("every moved address names a page", len(pairs) >= 6,
          "" if len(pairs) >= 6 else "only %d entries" % len(pairs))
    # A page is drawn either by its own web/feat/<name>.js or by one file that registers several
    # (menu-pages.js holds brand, tools and apps), so look for the page name anywhere in web/feat.
    every = "\n".join(read(f) for f in sorted(FEAT.glob("*.js")) if not f.name.startswith("_"))
    for old, new in pairs:
        drawn = (FEAT / (new + ".js")).is_file() or ('"%s"' % new) in every
        check("%s lands on %s, which some file draws" % (old, new), drawn,
              "" if drawn else "nothing in web/feat registers %s" % new)
    check("the page guard treats a moved address as a real address", "MADE_CLEAN[clean]" in html,
          "" if "MADE_CLEAN[clean]" in html else "pathKnown does not consult the table")


print()
if bad:
    print("%d check(s) failed" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("All checks passed. %d ok" % len(ok))
