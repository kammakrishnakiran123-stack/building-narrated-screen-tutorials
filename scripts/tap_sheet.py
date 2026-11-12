"""Contact sheets of every tap in the project: its box drawn on the exact frame the video will freeze on.

usage: python3 tap_sheet.py PROJECT.json
Writes work/taps_NN.png. Each tile is labelled "step / label / t". A correct tile shows the screen just
BEFORE the tap takes effect, with the red box around the whole control. Fix "t" or "rect" and rerun.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import ImageDraw
import common


def main():
    P = common.load(sys.argv[1])
    tw, tiles = 360, []
    groups = {}
    for si, st in enumerate(P["steps"]):
        if st.get("taps"):
            v = common.view(P, si)
            groups.setdefault(v["key"], (v, []))[1].extend((st["id"], t) for t in st["taps"])
    for v, taps in groups.values():
        x, y, w, h = v["crop"]
        th, k = round(h * tw / w), tw / w
        shots = common.frames_at(P, [t["t"] for _, t in taps], scale=(tw, th), v=v)
        for sid, t in taps:
            im = shots[t["t"]].copy()
            d = ImageDraw.Draw(im)
            (x1, y1, x2, y2), circ = common.rect_of(t["rect"])
            box = [(x1 - x) * k, (y1 - y) * k, (x2 - x) * k, (y2 - y) * k]
            (d.ellipse if circ else d.rectangle)(box, outline=(255, 0, 0), width=3)
            d.rectangle([0, th - 20, tw, th], fill=(0, 0, 0))
            d.text((4, th - 17), f"{sid} / {t['label']} / {t['t']}", fill=(255, 255, 0))
            tiles.append(im)
    print(f"{len(tiles)} taps:", *common.sheet(tiles, os.path.join(P["_work"], "taps"), per=6, height=max(t.height for t in tiles)), sep="\n  ")


if __name__ == "__main__":
    main()
