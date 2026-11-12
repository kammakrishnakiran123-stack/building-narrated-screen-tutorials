"""Automatic checks on one built edition. Exit code 0 = PASS, 2 = FAIL.

usage: python3 verify.py PROJECT.json LANG
Checks: streams present, BT.709 tags, frame size, length vs plan, loudness, subtitle cues, and - on the real
encoded frames - that every tap shows its highlight box and its caption. Writes work/verify_LANG.json and
contact sheets work/verify_LANG_NN.png (one frame per tap and per line spoken between taps) for a human or the quality inspector to look at.
"""
import json, math, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, timeline


def grab(path, idxs, w, h):
    """{frame_index: PIL.Image} from an encoded file, one decode pass."""
    from PIL import Image
    idxs = sorted(set(idxs))
    if not idxs:
        return {}
    sel = "+".join(f"eq(n\\,{i})" for i in idxs)
    for sync in (["-fps_mode", "passthrough"], ["-vsync", "0"]):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select='{sel}'", *sync,
                            "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True)
        if r.returncode == 0 and len(r.stdout) >= w * h * 3:
            break
    n = w * h * 3
    return {i: Image.frombuffer("RGB", (w, h), r.stdout[k * n:(k + 1) * n], "raw", "RGB", 0, 1)
            for k, i in enumerate(idxs) if (k + 1) * n <= len(r.stdout)}


def near(px, rgb, tol):
    return sum((a - b) ** 2 for a, b in zip(px, rgb)) <= tol * tol


def outline_points(G, rect, circ):
    x1, y1, x2, y2 = rect
    ins = 3 * G.u
    if circ:
        cx, cy, rx, ry = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2 - ins, (y2 - y1) / 2 - ins
        return [(cx + rx * math.cos(a / 60 * math.pi), cy + ry * math.sin(a / 60 * math.pi)) for a in range(120)]
    r = 16 * G.u
    pts = []
    for k in range(40):
        fx, fy = x1 + r + (x2 - x1 - 2 * r) * k / 39, y1 + r + (y2 - y1 - 2 * r) * k / 39
        pts += [(fx, y1 + ins), (fx, y2 - ins), (x1 + ins, fy), (x2 - ins, fy)]
    return pts


def run(P, lang):
    import render, text, theme
    base = common.out_base(P, lang)
    mp4 = base + ".mp4"
    res, ok = [], True

    def note(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        res.append({"check": name, "pass": bool(passed), "detail": str(detail)})
        print(f"  {'PASS' if passed else 'FAIL'}  {name}  {detail}")

    print(f"verify {lang}: {mp4}")
    if not os.path.exists(mp4):
        note("file exists", False, mp4)
        return False
    plan = json.load(open(os.path.join(P["_work"], f"plan_{lang}.json")))
    G = render.Geo(P)
    total = len(plan["frames"]) / P["fps"]
    j = json.loads(common.run(["ffprobe", "-v", "error", "-show_entries",
                               "stream=codec_type,codec_name,width,height,color_space,color_transfer,color_primaries:"
                               "format=duration,size", "-of", "json", mp4]).stdout)
    kinds = {s["codec_type"]: s for s in j["streams"]}
    note("video, audio and subtitle streams", {"video", "audio", "subtitle"} <= set(kinds), sorted(kinds))
    v = kinds.get("video", {})
    tags = [v.get(k) for k in ("color_space", "color_transfer", "color_primaries")]
    note("BT.709 colour tags", tags == ["bt709"] * 3, tags)
    note("frame size", (v.get("width"), v.get("height")) == (G.W, G.H), f"{v.get('width')}x{v.get('height')} (layout {G.W}x{G.H})")
    dur = float(j["format"]["duration"])
    note("length matches the timeline", abs(dur - total) < 0.2, f"{dur:.2f}s vs {total:.2f}s")
    e = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", mp4, "-map", "0:a", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", e)
    lufs = float(m[-1]) if m else None
    lo, hi = (-21, -13) if P.get("music") else (-19, -13)
    note("loudness near -16 LUFS", lufs is not None and lo <= lufs <= hi, f"{lufs} LUFS")
    srt = open(base + ".srt", encoding="utf-8").read()
    times = re.findall(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", srt)
    sec = lambda a: int(a[0]) * 3600 + int(a[1]) * 60 + int(a[2]) + int(a[3]) / 1000
    spans = [(sec(t[:4]), sec(t[4:])) for t in times]
    good = bool(spans) and all(a < b <= total + 0.5 for a, b in spans) and all(spans[i][1] <= spans[i + 1][0] + 0.02 for i in range(len(spans) - 1))
    note("subtitle cues ordered and inside the video", good, f"{len(spans)} cues")
    ch = json.loads(common.run(["ffprobe", "-v", "error", "-show_chapters", "-of", "json", mp4]).stdout).get("chapters", [])
    want = sum(1 for s in plan["steps"] if s["end"] > s["start"])
    note("chapter markers for every step", len(ch) == want, f"{len(ch)} of {want}")

    # every tap: highlight box and caption really visible in the encoded frames
    per, _ = render.captions(P, G, lang, plan)
    holds = timeline.hold_starts(plan)
    mids = {key: i + int(hl * P["fps"] * 0.5) for key, (i, hl) in holds.items()}
    between = [int((t0 + d * 0.5) * P["fps"]) for t0, d, si, k in plan["cues"] if P["steps"][si]["beats"][k]["at"][0] == "s"]
    shots = grab(mp4, list(mids.values()) + between, G.W, G.H)
    acc, ink = text.hexrgb(P["brand"]["accent"]), text.hexrgb(P["brand"]["ink"])
    sx, sy = G.scr[:2]
    bad_box, bad_cap, silent, cache, tc = [], [], [], {}, {}
    for (si, hi), f in sorted(mids.items()):
        st = P["steps"][si]
        tap = st["taps"][hi]
        name = f"{st['id']}/{tap['label']}"
        im = shots.get(f)
        if im is None:
            bad_box.append(name + " (frame missing)")
            continue
        hl = holds[(si, hi)][1]
        _, box, circ = render.tap_view(P, G, tap, hl / 2, hl, common.view(P, si)["crop"])
        pts = [(int(x + sx), int(y + sy)) for x, y in outline_points(G, render.box_outline(G, box), circ)]
        pts = [p for p in pts if 0 <= p[0] < G.W and 0 <= p[1] < G.H]
        cap = per[f]
        if cap and cap[1] != "panel":                       # ignore outline points hidden under the caption strip
            sim, (_, y0) = render.strip_image(P, G, cap[0], cap[1], cache, theme.colours_at(P, plan, f, tc)[1])
            pts = [p for p in pts if not (y0 <= p[1] < y0 + sim.height)]
        hit = sum(near(im.getpixel(p), acc, 70) for p in pts) / max(1, len(pts))
        if hit < 0.55:
            bad_box.append(f"{name} ({hit:.0%})")
        if not any(b["at"] == f"h{hi}" for b in st.get("beats", [])):
            silent.append(name)
        elif not cap:
            bad_cap.append(name + " (no caption planned)")
        else:
            bg = theme.colours_at(P, plan, f, tc)[1]
            sim, (x0, y0) = render.strip_image(P, G, cap[0], cap[1], cache, bg)
            corners = [(x0 + 4, y0 + 4), (x0 + sim.width - 5, y0 + 4), (x0 + 4, y0 + sim.height - 5)]
            if not all(near(im.getpixel(c), bg, 60) for c in corners):
                bad_cap.append(name)
    note("every tap shows its highlight box", not bad_box, f"{len(mids) - len(bad_box)}/{len(mids)}" + (f"; missing: {bad_box[:6]}" if bad_box else ""))
    note("every narrated tap shows its caption", not bad_cap, f"missing: {bad_cap[:6]}" if bad_cap else "")
    if silent:
        print(f"  NOTE  {len(silent)} taps have no narration line: {silent[:6]}")
    long_holds = [f"{P['steps'][si]['id']}/{P['steps'][si]['taps'][hi]['label']} ({hl:.1f}s)" for (si, hi), (_, hl) in sorted(holds.items()) if hl > 8]
    if long_holds:
        print(f"  NOTE  {len(long_holds)} taps freeze the screen for more than 8 s; shorten or split the line: {long_holds[:6]}")
    sheets = common.sheet([shots[f] for f in sorted(shots)], os.path.join(P["_work"], f"verify_{lang}"), per=6, height=900)
    json.dump({"lang": lang, "pass": ok, "checks": res, "silent_taps": silent, "sheets": sheets,
               "size_mb": round(int(j["format"]["size"]) / 1e6, 1), "seconds": round(dur, 1)},
              open(os.path.join(P["_work"], f"verify_{lang}.json"), "w"), indent=1, ensure_ascii=False)
    print(f"  {'PASS' if ok else 'FAIL'} overall. Tap frames to look at: {', '.join(sheets) or '(no taps)'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run(common.load(sys.argv[1]), sys.argv[2]) else 2)
