"""Contrast measurements for the web/feat/pill.js fix wave.

WCAG 2.2 relative luminance and (L1+0.05)/(L2+0.05). Text is 13px here, so the
floor is 4.5; the dot and the pill boundary are non-text, judged at 3.0.
"""

def lum(hexstr):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def ratio(fg, bg):
    lf, lb = lum(fg), lum(bg)
    if lf < lb:
        lf, lb = lb, lf
    return (lf + 0.05) / (lb + 0.05)

# ---- the real cascade grounds (polish-colour.js wins base/rec background) ----
BRAND_SOFT = "#2A1B10"   # --brand-soft, base pill ground
BAD_SOFT   = "#2B1416"   # --bad-soft, recording pill ground
MUTED      = "#111111"   # --muted, wait pill ground
PAGE       = "#0A0A0A"   # topbar --bg

pairs = [
    # (label, fg, bg, floor)
    ("CURRENT run base  #8A3C08 on brand-soft", "#8A3C08", BRAND_SOFT, 4.5),
    ("CURRENT run hover #7A3406 on #FFEEDF",    "#7A3406", "#FFEEDF", 4.5),
    ("CURRENT rec base  #9E121B on bad-soft",   "#9E121B", BAD_SOFT, 4.5),
    ("CURRENT rec hover #9E121B on #FFE9EA",    "#9E121B", "#FFE9EA", 4.5),
    ("CURRENT wait base --dim on --muted",      "#A3A3A3", MUTED, 4.5),
    ("CURRENT wait hover --dim on #F1ECE7",     "#A3A3A3", "#F1ECE7", 4.5),
    ("CURRENT .pcrun-2 rec base --dim on bad-soft",   "#A3A3A3", BAD_SOFT, 4.5),
    ("CURRENT .pcrun-2 rec hover --dim on #FFE9EA",   "#A3A3A3", "#FFE9EA", 4.5),
    ("CURRENT dot sep ::before rec base --faint on bad-soft", "#7C7C7C", BAD_SOFT, 3.0),
    ("CURRENT dot sep ::before rec hover --faint on #FFE9EA", "#7C7C7C", "#FFE9EA", 3.0),
    ("CURRENT wait boundary border --line-2 on topbar", "#2A2A2A", PAGE, 3.0),
    ("CANDIDATE run base ink #FFD9BC on brand-soft", "#FFD9BC", BRAND_SOFT, 4.5),
    ("CANDIDATE run base ink --brand-deep #FFB27A on brand-soft", "#FFB27A", BRAND_SOFT, 4.5),
    ("CANDIDATE rec base ink #FFB4B7 on bad-soft", "#FFB4B7", BAD_SOFT, 4.5),
    ("CANDIDATE rec base ink #FFD3D5 on bad-soft", "#FFD3D5", BAD_SOFT, 4.5),
    ("CANDIDATE rec hover dark ink #9E121B on #FFE9EA (kept)", "#9E121B", "#FFE9EA", 4.5),
    ("CANDIDATE wait hover dark ink #3A2C25 on #F1ECE7", "#3A2C25", "#F1ECE7", 4.5),
    ("CANDIDATE wait hover dark ink --brand-ink #160D05 on #F1ECE7", "#160D05", "#F1ECE7", 4.5),
    ("CANDIDATE wait hover dark ink #7A3406 on #F1ECE7", "#7A3406", "#F1ECE7", 4.5),
    ("CANDIDATE .pcrun-2 rec base #C79AA1 on bad-soft", "#C79AA1", BAD_SOFT, 4.5),
    ("CANDIDATE .pcrun-2 rec base #D9B0B4 on bad-soft", "#D9B0B4", BAD_SOFT, 4.5),
    ("CANDIDATE .pcrun-2 rec hover #A03040 on #FFE9EA", "#A03040", "#FFE9EA", 4.5),
    ("CANDIDATE .pcrun-2 rec hover #9E121B on #FFE9EA", "#9E121B", "#FFE9EA", 4.5),
    ("CANDIDATE wait base bg --line #1E1E1E vs topbar", "#1E1E1E", PAGE, 3.0),
    ("CANDIDATE wait base bg --line-2 #2A2A2A vs topbar", "#2A2A2A", PAGE, 3.0),
    ("CANDIDATE wait text --dim on --line #1E1E1E", "#A3A3A3", "#1E1E1E", 4.5),
    ("CANDIDATE flash dark #3A2415 vs card text --text", "#F5F5F5", "#3A2415", 4.5),
    ("CANDIDATE flash dark --brand-soft vs card text --text", "#F5F5F5", BRAND_SOFT, 4.5),
    ("CURRENT flash light #FFF4EA vs card text --text", "#F5F5F5", "#FFF4EA", 4.5),
    ("CURRENT flash light #FFE6D2 vs card text --text", "#F5F5F5", "#FFE6D2", 4.5),
]

worst = 0
for label, fg, bg, floor in pairs:
    r = ratio(fg, bg)
    mark = "PASS" if r >= floor else "FAIL"
    print(f"{label:64s} {r:6.2f}:1  (need {floor})  {mark}")
