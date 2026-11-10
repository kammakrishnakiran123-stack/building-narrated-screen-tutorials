"""Write a 3D .cube LUT: full-range BT.2020 HDR R'G'B' (PQ or HLG) -> BT.709 / sRGB-coded R'G'B'.

usage: python3 hdr_lut.py OUT.cube [pq|hlg] [WHITE_NITS=100] [SIZE=65]

Screen recordings and phone mirrors store an SDR interface inside an HDR container. UI white sits at about
100 nits in PQ (code value ~0.51). If whites still look grey after conversion, probe a white UI area: ~0.58
means 203 nits, so set "white_nits": 203 in project.json. WHITE_NITS is ignored for HLG (white = 75% signal).
PQ:  PQ EOTF -> nits / WHITE -> BT.2020->BT.709 matrix -> clip -> sRGB OETF.
HLG: inverse HLG OETF -> / value at 75% signal -> same matrix and OETF. (HLG path is not yet proven on a
real recording; check one frame against the device.)
"""
import sys
import numpy as np

M = np.array([[1.6605, -0.5876, -0.0728],
              [-0.1246, 1.1329, -0.0083],
              [-0.0182, -0.1006, 1.1187]])   # BT.2020 -> BT.709, linear light


def pq_eotf(e):
    m1, m2 = 2610 / 16384, 2523 / 4096 * 128
    c1, c2, c3 = 3424 / 4096, 2413 / 4096 * 32, 2392 / 4096 * 32
    p = np.power(e, 1 / m2)
    return 10000 * np.power(np.maximum(p - c1, 0) / (c2 - c3 * p), 1 / m1)


def hlg_inv_oetf(e):
    a, b, c = 0.17883277, 0.28466892, 0.55991073
    return np.where(e <= 0.5, e * e / 3, (np.exp((np.maximum(e, 0.5) - c) / a) + b) / 12)


def srgb_oetf(l):
    l = np.clip(l, 0, 1)
    return np.where(l <= 0.0031308, 12.92 * l, 1.055 * np.power(l, 1 / 2.4) - 0.055)


def write(out, kind="pq", white=100.0, n=65):
    g = np.linspace(0, 1, n)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")   # .cube order: R varies fastest
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    lin = pq_eotf(rgb) / float(white) if kind == "pq" else hlg_inv_oetf(rgb) / hlg_inv_oetf(np.array(0.75))
    res = srgb_oetf(lin @ M.T)
    with open(out, "w") as f:
        f.write(f"LUT_3D_SIZE {n}\n")
        np.savetxt(f, res, fmt="%.6f")


if __name__ == "__main__":
    a = sys.argv[1:]
    write(a[0], a[1] if len(a) > 1 else "pq", float(a[2]) if len(a) > 2 else 100.0, int(a[3]) if len(a) > 3 else 65)
    print("wrote", a[0])
