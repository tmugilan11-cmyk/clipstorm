# Measures WCAG 2.2 contrast ratios for the day.js card inks, before and after the fix.
# Run: python docs/qa/fix/measure_day.py

def lum(hexv):
    v = hexv.lstrip("#")
    parts = [int(v[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    x, y = lum(a), lum(b)
    hi, lo = max(x, y), min(x, y)
    return round((hi + 0.05) / (lo + 0.05), 2)


INKS = {"--text #F5F5F5": "#F5F5F5", "--dim #A3A3A3": "#A3A3A3", "--bad #F87171": "#F87171"}

print("BEFORE (cream gradient stops - the bug):")
for ground in ("#FFF9F4", "#FFF7F0"):
    for name, ink in INKS.items():
        print(f"  {name} on {ground}: {ratio(ink, ground)}:1")

print("AFTER candidates (palette dark warm tones):")
for ground, label in (("#2A1B10", "var(--brand-soft)"), ("#160D05", "var(--brand-ink)")):
    for name, ink in INKS.items():
        print(f"  {name} on {ground} ({label}): {ratio(ink, ground)}:1")
