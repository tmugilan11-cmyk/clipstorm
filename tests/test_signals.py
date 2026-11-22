import os
os.environ["PEAKCUT_JUDGE_WEB"] = "0"
from studio import signals

heat = [(0, 10, 0.2), (10, 20, 0.2), (20, 30, 0.9), (30, 40, 0.8), (40, 50, 0.2), (50, 60, 0.2)]
sig = {"heat": heat, "comments": [(25, 50, "lol 0:25 best part"), (200, 9, "far")], "chapters": [], "views": 1, "likes": 1}
sig["comments"] = [(25, 50, "lol 0:25 best part"), (200, 9, "far")]
out = signals.brief(sig, 15, 60, shift=10)
assert out.startswith("WHAT VIEWERS OF THIS VIDEO DID"), out
assert "[10-30] replayed" in out, out          # buckets merged, times shifted by 10
assert "[15] (50 likes) lol 0:25 best part" in out, out
assert "far" not in out
assert "replayed" not in signals.brief(sig, 40, 60)
assert signals.brief(sig, 100, 150) == ""
assert signals.brief({}, 0, 10) == ""
e = signals.youtube("https://example.com/x")
assert e == {"heat": [], "comments": [], "chapters": [], "views": None, "likes": None}
print("signals ok")
