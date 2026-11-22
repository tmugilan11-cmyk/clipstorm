"""The AI settings: an address a person types in decides where requests go.

Every service in the list has its own shape and its own address, but the address box is always editable, and
whatever is typed in is spoken to in the OpenAI chat format - that is what "an OpenAI-compatible service" means.
These checks follow that rule from the page to the thing that sends the request.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ok = []
bad = []


def check(name, good, why=""):
    (ok if good else bad).append(name)
    if not good:
        print("FAIL", name, ("  " + why) if why else "")


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(l for l in src.splitlines() if not l.strip().startswith("//"))


ai = strip_comments((ROOT / "studio" / "ai.py").read_text(encoding="utf-8"))
index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
index_js = strip_comments(index)

# ---- the rule lives in one place ------------------------------------------------
check("one wire() helper decides the shape of every request", "def wire(" in ai and ai.count("PROVIDERS[provider()][2]") == 0,
      "call()/see() still look the shape up from the table directly")
check("a typed address that is not the service's own is the OpenAI shape",
      'return "openai"' in ai.split("def wire(")[1].split("def ")[0],
      "wire() does not switch to the openai shape for a typed address")
check("a service's own address keeps its own shape",
      "typed != default" in ai or "typed == default" in ai, "wire() has no default comparison")

# ---- the page always shows the address box --------------------------------------
check("the address box is never hidden", "$(\"#ai_basewrap\").hidden = false" in index_js,
      "the page still hides the address box for non-custom services")
check("the address box says what it does for the chosen service", 'id="ai_basehint"' in index and "$(\"#ai_basehint\")" in index_js,
      "no plain-English line beside the address box")
check("switching service empties the address so two services never share one",
      '$("#ai_base").value = "";' in index_js, "the address is carried across services")

# ---- errors name the thing actually talked to ------------------------------------
check("errors name the typed address, not the company the row came from", "def where(" in ai
      # explain() may be told which service a failed call really went to (`first`); without that it asks where()
      and ("couldn't reach {where()}" in ai or ("who = first or where()" in ai and "couldn't reach {who}" in ai)),
      "explain() still names the service label")

# ---- the routes pass the address through -----------------------------------------
server = (ROOT / "studio" / "server.py").read_text(encoding="utf-8")
check("the save route takes the address the page sends", 'body.get("base_url")' in server)
check("the model-list route takes the address the page sends", 'body.get("base_url")' in server)

# ---- the whole module still imports ----------------------------------------------
from studio import ai as ai_mod  # noqa: E402

check("a gemini row pointed at its own address keeps the gemini shape", ai_mod.wire("gemini", "") == "gemini")
check("a gemini row pointed somewhere else speaks the openai shape",
      ai_mod.wire("gemini", "https://openrouter.ai/api/v1") == "openai")
check("logfare's own address keeps the openai shape it already had", ai_mod.wire("logfare", "https://logfare.ai/v1") == "openai")
check("a custom service speaks the openai shape", ai_mod.wire("custom", "http://127.0.0.1:1234/v1") == "openai")

# ---- the schema sentence, and what an empty answer means -------------------------
# A prompt that names its own object must not be told a different one, and the JSON word null must never be
# returned as though the model had answered. Both were real: a sound-placement prompt asking for {"cues": [...]}
# was told to answer {"items": ...} with a schema of `null`, so the model answered null and the caller read that
# as "the AI chose nothing", which is a real answer.
check("a prompt with no schema is not told to answer with an items object",
      "items" not in ai_mod._wrapped("Say the shape yourself.", None),
      "the items sentence is added even without a schema")
check("a prompt with no schema still asks for JSON only",
      "JSON only" in ai_mod._wrapped("Say the shape yourself.", None))
check("a prompt with a schema still gets the items sentence",
      "items" in ai_mod._wrapped("Find clips.", {"type": "object", "properties": {"n": {"type": "number"}}}))
try:
    ai_mod._parse("null")
    null_raised = False
except Exception:
    null_raised = True
check("the JSON word null is an error, not an empty answer", null_raised,
      "null is returned as a value, so a broken answer looks like a deliberate empty one")
check("an ordinary object still comes back", ai_mod._parse('{"cues": []}') == {"cues": []})
check("an items wrapper is still unwrapped", ai_mod._parse('{"items": {"cues": []}}') == {"cues": []})

print()
if bad:
    print("%d check(s) failed" % len(bad))
    for b in bad:
        print("  - " + b)
    sys.exit(1)
print("All checks passed. %d ok" % len(ok))
