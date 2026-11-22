"""Every feature file must still be a feature file.

The UI is built as small files in web/feat/, one per feature, wired in by
web/plugins.js. This test is the cheap net under that: it proves each file
parses as JavaScript, declares exactly one plug-in, never edits index.html,
and does not claim an id the page already uses.

Run it directly. It needs node on the PATH (the same node the page is checked
with) and nothing else.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEAT = ROOT / "web" / "feat"
INDEX = ROOT / "web" / "index.html"
PLUGINS = ROOT / "web" / "plugins.js"

checks = 0


def ok(what, yes, why=""):
    global checks
    checks += 1
    if not yes:
        print("FAIL", what, ("- " + why) if why else "")
        sys.exit(1)
    print("ok  ", what)


def node_check(path: Path) -> tuple[bool, str]:
    got = subprocess.run(
        ["node", "--check", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return got.returncode == 0, (got.stderr or got.stdout or "").strip()[-600:]


# The loader and the frozen page must both exist and parse.
ok("plugins.js is there", PLUGINS.is_file())
good, why = node_check(PLUGINS)
ok("plugins.js parses", good, why)

index = INDEX.read_text(encoding="utf-8")
ok("index.html loads the loader", "/assets/plugins.js" in index)
ok("index.html is otherwise untouched by features", index.count("/assets/feat/") == 0,
   "a feature referenced itself from index.html instead of being found by the loader")

# Every served feature file.
files = sorted(p for p in FEAT.glob("*.js") if not p.name.startswith("_"))
ok("there is at least one feature file", len(files) >= 1)

# Ids the frozen page already owns. A feature may not invent a second element
# with one of these ids, because getElementById would then return the wrong one.
page_ids = set(re.findall(r'\bid="([A-Za-z][\w\-]*)"', index))

seen_names = {}
for path in files:
    good, why = node_check(path)
    ok(f"{path.name} parses", good, why)

    src = path.read_text(encoding="utf-8")

    # Exactly one registration, named after the file. Both idioms are allowed:
    #   PeakCut.add("slug", ...)          and         const P = PeakCut; P.add("slug", ...)
    names = re.findall(
        r'\b(?:PeakCut|P|PC)\.add\(\s*["\']([a-z0-9\-]+)["\']',
        src,
    )
    ok(f"{path.name} declares one plug-in", len(names) == 1, f"found {names}")
    name = names[0] if names else ""
    ok(f"{path.name} is named after itself", name == path.stem, f"{name} != {path.stem}")
    ok(f"{path.name} is the only owner of {name}", name not in seen_names,
       f"also declared by {seen_names.get(name)}")
    seen_names[name] = path.name

    # It must not reach over the fence into the page's own markup. Mentioning
    # the frozen page in a comment is fine; touching it is not.
    code_only = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    code_only = "\n".join(ln.split("//")[0] for ln in code_only.splitlines())
    ok(f"{path.name} does not write into index.html", "index.html" not in code_only)

    # A feature that draws markup from anything the server said must escape it.
    # A fixed string is fine; an interpolated one needs esc() on every value
    # that came from outside, so demand that esc() is present at all.
    draws = re.findall(r"\.innerHTML\s*=\s*([^;]+)", src) + re.findall(r"insertAdjacentHTML\([^,]+,\s*([^)]+)", src)
    interpolated = [d for d in draws if "${" in d]
    if interpolated:
        ok(f"{path.name} escapes what it draws", re.search(r"\besc\(", src) is not None,
           "builds interpolated markup without esc()")
    elif draws:
        ok(f"{path.name} draws only fixed markup", True)
    else:
        ok(f"{path.name} draws no markup", True)

    # No stray network path: features talk to the app through PeakCut helpers or
    # the documented /api routes; a hard-coded origin would break on another port.
    ok(f"{path.name} uses no absolute origin", "http://127.0.0.1" not in src and "http://localhost" not in src)

    # Ids it introduces must not collide with the page's own.
    mine = set(re.findall(r'\bid="([A-Za-z][\w\-]*)"', src))
    clashes = sorted(mine & page_ids)
    ok(f"{path.name} invents no clashing id", not clashes, f"clashes with the page: {clashes}")

# The loader must accept the names it is fed.
ok("loader keeps the documented folder", "feat" in PLUGINS.read_text(encoding="utf-8"))

print(json.dumps({"files": len(files), "checks": checks}))
print("All checks passed.")
