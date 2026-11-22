# Measure the WCAG contrast ratios for the pairs the fix wave touches.
# (L1+0.05)/(L2+0.05) with sRGB relative luminance, same formula as docs/qa/CONTRACT.md:49.

def lum(hexval: str) -> float:
    h = hexval.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(fg: str, bg: str) -> float:
    a, b = lum(fg), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


pairs = [
    ("CURRENT BUG  brand-ink #160D05 on muted track #111111", "#160D05", "#111111"),
    ("CURRENT BUG  brand-ink #160D05 on page bg #0A0A0A", "#160D05", "#0A0A0A"),
    ("PROPOSED     new-series #22D3EE on muted track #111111", "#22D3EE", "#111111"),
    ("PROPOSED     new-series #22D3EE on page bg #0A0A0A", "#22D3EE", "#0A0A0A"),
    ("PROPOSED     note link brand-deep #FFB27A on aa-note muted #111111", "#FFB27A", "#111111"),
    ("PROPOSED     swipe hint faint #A0948C on panel #111111", "#A0948C", "#111111"),
    ("PROPOSED     swipe hint faint #A0948C on page bg #0A0A0A", "#A0948C", "#0A0A0A"),
    ("PROPOSED     rerr link inherits bad #F87171 on bad-soft #2B1416", "#F87171", "#2B1416"),
    ("SIBLING      returning bar brand #FF8B33 on muted track #111111", "#FF8B33", "#111111"),
]

for name, fg, bg in pairs:
    print("%-62s %.2f:1" % (name, ratio(fg, bg)))
