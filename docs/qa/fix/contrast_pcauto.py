# Measure the WCAG 2.2 contrast ratios for the .pcauto-warn panel pair
# before and after the fix. Formula: (L1 + 0.05) / (L2 + 0.05), L1 = lighter.
def lum(hexs):
    r, g, b = (int(hexs[i:i+2], 16) / 255 for i in (0, 2, 4))
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = ch(r), ch(g), ch(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(fg, bg):
    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)

SOFT = "2A1B10"   # --brand-soft, the .pcauto-warn background (index.html:17)
print("BEFORE  #160D05 (--brand-ink) on #2A1B10:", round(ratio("160D05", SOFT), 2), ":1")
print("AFTER   #FFB27A (--brand-deep) on #2A1B10:", round(ratio("FFB27A", SOFT), 2), ":1")
print("ALT     #F5F5F5 (--text)       on #2A1B10:", round(ratio("F5F5F5", SOFT), 2), ":1")
print("REF     #FFB27A on --bg #0A0A0A (palette note):", round(ratio("FFB27A", "0A0A0A"), 2), ":1")
