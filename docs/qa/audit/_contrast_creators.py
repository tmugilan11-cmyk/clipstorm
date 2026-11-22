def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

def lum(hexs):
    hexs = hexs.lstrip("#")
    r, g, b = (int(hexs[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def ratio(a, b):
    x, y = lum(a), lum(b)
    hi, lo = max(x, y), min(x, y)
    return round(((hi + 0.05) / (lo + 0.05)) * 100) / 100

pairs = [
    ("text on bg",        "#F5F5F5", "#0A0A0A"),
    ("dim on bg",         "#A3A3A3", "#0A0A0A"),
    ("faint(resolved) on bg", "#A0948C", "#0A0A0A"),
    ("faint(:root) on bg",    "#7C7C7C", "#0A0A0A"),
    ("dim on muted",      "#A3A3A3", "#111111"),
    ("faint(resolved) on muted", "#A0948C", "#111111"),
    ("faint(:root) on muted",    "#7C7C7C", "#111111"),
    ("text on muted",     "#F5F5F5", "#111111"),
    ("brand-deep on brand-soft", "#FFB27A", "#2A1B10"),
    ("white on live (Recording pill)", "#FFFFFF", "#EF4444"),
    ("brand-ink on live (proposed fix)", "#160D05", "#EF4444"),
    ("dim on card",       "#A3A3A3", "#111111"),
]
for name, fg, bg in pairs:
    print(f"{name:38s} {fg} on {bg}  {ratio(fg, bg)}")
