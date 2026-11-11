"""Step colours: palettes, text contrast, and blending from one step's colour to the next.

project "palette":
  "none"            - one colour everywhere (brand.ink); the classic look
  "vivid", "calm"   - built-in sets, one colour per step, cycling
  "brand"           - a set grown from brand.accent by turning its hue
  ["#D81B60", ...]  - your own colours
Each step gets a pair: `main` for full-colour cards and `dark` for the caption strip and panels. Both are
darkened until white text is readable on them (contrast 3:1 on main for large text, 4.5:1 on dark).
"""
import colorsys

PALETTES = {
    "vivid": ["#D81B60", "#00897B", "#3949AB", "#F4511E", "#8E24AA", "#1E88E5", "#2E7D32", "#C0392B"],
    "calm": ["#3E5C76", "#2F6F6F", "#5B5F97", "#7A5C3E", "#6B4E71", "#4A6670", "#52796F", "#775253"],
}
BLEND = 0.5      # seconds over which a new step's colour replaces the last one


def hexrgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _lum(c):
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v / 255) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable(c, text, ratio):
    """Darken c until `text` on it reaches the contrast ratio."""
    c = tuple(c)
    for _ in range(60):
        if contrast(c, text) >= ratio:
            break
        c = tuple(int(v * 0.94) for v in c)
    return c


def mix(a, b, k):
    return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


def themed(P):
    return P.get("palette", "none") not in ("none", None, "")


def pairs(P):
    """[(main, dark)] for every step."""
    n = len(P["steps"])
    text = hexrgb(P["brand"]["text"])
    pal = P.get("palette", "none")
    if not themed(P):
        ink = hexrgb(P["brand"]["ink"])
        return [(ink, ink)] * n
    if pal == "brand":
        h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in hexrgb(P["brand"]["accent"])))
        base = [tuple(int(x * 255) for x in colorsys.hsv_to_rgb((h + 0.5 + k * 0.085) % 1, min(0.7, max(0.45, s)), 0.6))
                for k in range(8)]          # start opposite the accent so the tap highlight still stands out
    else:
        base = [hexrgb(c) for c in (PALETTES[pal] if isinstance(pal, str) else pal)]
    out = []
    for i in range(n):
        main = readable(base[i % len(base)], text, 3.0)
        out.append((main, readable(mix(main, (0, 0, 0), 0.42), text, 4.5)))
    return out


def colours_at(P, plan, f, cache):
    """(main, dark) at output frame f, blending in over the first BLEND seconds of each step."""
    if "pairs" not in cache:
        cache["pairs"] = pairs(P)
        cache["starts"] = [int(round(s["start"] * P["fps"])) for s in plan["steps"]]
    si = plan["frames"][f][1]
    cur = cache["pairs"][si]
    k = (f - cache["starts"][si]) / (BLEND * P["fps"])
    if si == 0 or k >= 1:
        return cur
    prev = cache["pairs"][si - 1]
    k = max(0.0, k)
    k = k * k * (3 - 2 * k)
    return mix(prev[0], cur[0], k), mix(prev[1], cur[1], k)
