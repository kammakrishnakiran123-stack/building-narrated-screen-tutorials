"""Suggest tap moments: instants where a still screen suddenly changes.

usage: python3 find_taps.py PROJECT.json [START END]
Needs only "source" (and "crop") in the project. Writes work/tap_candidates.json
  [{"t": seconds (last still frame = the frame to freeze on), "strength": share of pixels that changed,
    "rect": [x1,y1,x2,y2] guess in source pixels, or null when the whole screen changed}]
and contact sheets work/tap_candidates_NN.png: for each candidate the frame before (with the guessed box in
red) and the frame half a second after. These are suggestions. Page loads, typing and animations show up too,
and a guessed box is only where pixels changed first. Look at the sheets, keep the real taps, and set each
rect to the whole control. Recording with the phone's "show touches" option on makes the taps obvious.
"""
import json, os, sys
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common

FPS, SW = 15, 180
CHANGED, QUIET, STILL_FRAMES = 0.0015, 0.0005, 5     # pixel shares; frames of stillness required before


def main():
    P = common.load(sys.argv[1])
    t0, t1 = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (0.0, P["_info"]["dur"])
    x, y, w, h = P["crop"]
    sh = max(2, round(h * SW / w) // 2 * 2)
    p = common.decoder(P, scale=(SW, sh), fps=FPS, gray=True)
    prev, hist, cands, i, pending = None, deque(maxlen=STILL_FRAMES), [], 0, None
    while True:
        b = p.stdout.read(SW * sh)
        if len(b) < SW * sh:
            break
        cur = np.frombuffer(b, np.uint8).reshape(sh, SW).astype(np.int16)
        if pending is not None:                      # one frame after the onset: where did pixels change?
            before, frac, ti = pending
            ys, xs = np.nonzero(np.abs(cur - before) > 18)
            rect = None
            if len(xs) and (xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1) < 0.35 * SW * sh:
                k = w / SW
                rect = [int(x + max(xs.min() - 3, 0) * k), int(y + max(ys.min() - 3, 0) * k),
                        int(x + min(xs.max() + 4, SW) * k), int(y + min(ys.max() + 4, sh) * k)]
            cands.append({"t": round(ti, 2), "strength": round(frac, 4), "rect": rect})
            pending = None
        if prev is not None:
            frac = float((np.abs(cur - prev) > 18).mean())
            if frac > CHANGED and len(hist) == STILL_FRAMES and max(hist) < QUIET and t0 <= (i - 1) / FPS <= t1:
                pending = (prev, frac, (i - 1) / FPS)
            hist.append(frac)
        prev, i = cur, i + 1
    p.kill()
    out = os.path.join(P["_work"], "tap_candidates.json")
    json.dump(cands, open(out, "w"), indent=1)
    print(f"{len(cands)} candidates -> {out}")
    for c in cands:
        print(f"  t={c['t']:7.2f}  changed={c['strength']:.3f}  rect={c['rect']}")
    if cands:
        from PIL import ImageDraw
        tw = 300
        th = round(h * tw / w)
        shots = common.frames_at(P, [c["t"] for c in cands] + [c["t"] + 0.5 for c in cands], scale=(tw, th))
        tiles = []
        for c in cands:
            a = shots[c["t"]].copy()
            d = ImageDraw.Draw(a)
            if c["rect"]:
                k = tw / w
                r = c["rect"]
                d.rectangle([(r[0] - x) * k, (r[1] - y) * k, (r[2] - x) * k, (r[3] - y) * k], outline=(255, 0, 0), width=3)
            d.rectangle([0, 0, tw, 18], fill=(0, 0, 0))
            d.text((4, 3), f"t={c['t']}  before", fill=(255, 255, 0))
            tiles += [a, shots[c["t"] + 0.5]]
        print("sheets:", *common.sheet(tiles, os.path.join(P["_work"], "tap_candidates"), per=8, height=th), sep="\n  ")


if __name__ == "__main__":
    main()
