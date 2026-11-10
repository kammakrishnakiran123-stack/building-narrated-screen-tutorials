"""Shared helpers: project file, source probe, HDR-aware frame decoding."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULTS = {
    "fps": 30, "layout": "native", "primary": "en", "hdr": "auto", "white_nits": 100,
    "highlight": "box", "touch": True, "tap_sound": False, "crop": None, "approved": [], "max_zoom": 1.3,
    "brand": {"accent": "#F58220", "ink": "#0F1729", "text": "#FFFFFF"},
    "timing": {"hold_pre": 0.35, "hold_min": 1.6, "pad": 0.45, "quiet": 4.0, "max_speed": 8.0, "end_tail": 1.6},
}
LAYOUTS = ("native", "portrait", "landscape")


def die(msg):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        die(f"{cmd[0]} failed:\n{r.stderr[-1500:]}")
    return r


def probe(src):
    if not os.path.exists(src):
        die(f"source not found: {src}")
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate,pix_fmt,color_transfer,color_primaries:stream_side_data=rotation:"
             "format=duration", "-of", "json", src])
    j = json.loads(r.stdout)
    s = j["streams"][0]
    rot = 0
    for sd in s.get("side_data_list", []):
        rot = int(sd.get("rotation", 0)) or rot
    w, h = s["width"], s["height"]
    if abs(rot) % 180 == 90:
        w, h = h, w
    n, d = s["r_frame_rate"].split("/")
    return dict(w=w, h=h, fps=float(n) / float(d), pix_fmt=s.get("pix_fmt", ""), trc=s.get("color_transfer", ""),
                prim=s.get("color_primaries", ""), dur=float(j["format"]["duration"]))


def load(path):
    """Read project.json, fill defaults, resolve paths. Keys starting with _ are derived, never saved."""
    P = json.load(open(path, encoding="utf-8"))
    for k, v in DEFAULTS.items():
        P[k] = {**v, **P.get(k, {})} if isinstance(v, dict) else P.get(k, v)
    P["_path"] = os.path.abspath(path)
    root = P["_root"] = os.path.dirname(P["_path"])
    P["_src"] = os.path.join(root, P["source"])
    P["_work"] = os.path.join(root, "work")
    os.makedirs(P["_work"], exist_ok=True)
    out = P.get("output", {})
    P["_out"] = os.path.join(root, out.get("dir", "output/v1"))
    P["_name"] = out.get("name", "Tutorial")
    P["_info"] = info = probe(P["_src"])
    if not P["crop"]:
        P["crop"] = [0, 0, info["w"], info["h"]]
    x, y, w, h = P["crop"]
    P["crop"] = [x, y, w // 2 * 2, h // 2 * 2]
    if P["layout"] not in LAYOUTS:
        die(f"layout must be one of {LAYOUTS}")
    return P


def edit(path, fn):
    """Apply fn(raw_dict) to the project file on disk (keeps the user's own keys only)."""
    raw = json.load(open(path, encoding="utf-8"))
    fn(raw)
    json.dump(raw, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def hdr_kind(P):
    if P["hdr"] in ("pq", "hlg"):
        return P["hdr"]
    if P["hdr"] == "off":
        return None
    return {"smpte2084": "pq", "arib-std-b67": "hlg"}.get(P["_info"]["trc"])


def decode_vf(P, scale=None, fps=None):
    """ffmpeg filter chain: constant fps -> crop -> (HDR to SDR via LUT) -> optional scale. Run with cwd=work."""
    x, y, w, h = P["crop"]
    vf = [f"fps={fps or P['fps']}", f"crop={w}:{h}:{x}:{y}"]
    kind = hdr_kind(P)
    if kind:
        import hdr_lut
        lut = os.path.join(P["_work"], f"{kind}{int(P['white_nits'])}.cube")
        if not os.path.exists(lut):
            hdr_lut.write(lut, kind, P["white_nits"])
        vf += ["scale=in_color_matrix=bt2020:in_range=tv", "format=rgb48le",
               f"lut3d=file={os.path.basename(lut)}:interp=tetrahedral"]
    if scale:
        vf.append(f"scale={scale[0]}:{scale[1]}:flags=area")
    return ",".join(vf)


def decoder(P, scale=None, fps=None, gray=False):
    """Popen that streams raw frames (rgb24 or gray) of the cropped, colour-corrected source."""
    fmt = "gray" if gray else "rgb24"
    return subprocess.Popen(["ffmpeg", "-v", "error", "-i", P["_src"], "-vf", decode_vf(P, scale, fps) + f",format={fmt}",
                             "-pix_fmt", fmt, "-f", "rawvideo", "-"], stdout=subprocess.PIPE, bufsize=10**8, cwd=P["_work"])


def frames_at(P, times, scale=None):
    """{time: PIL.Image} for source times (seconds), decoded sequentially so indices match the build."""
    from PIL import Image
    w, h = scale or P["crop"][2:]
    want = {}
    for t in times:
        want.setdefault(int(round(t * P["fps"])), []).append(t)
    out, i, n, p = {}, 0, w * h * 3, decoder(P, scale)
    last = max(want) if want else -1
    buf = None
    while i <= last:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        buf = b
        for t in want.get(i, []):
            out[t] = Image.frombuffer("RGB", (w, h), buf, "raw", "RGB", 0, 1).copy()
        i += 1
    p.kill()
    if buf is not None:
        for idx, ts in want.items():      # times past the end get the last frame
            for t in ts:
                out.setdefault(t, Image.frombuffer("RGB", (w, h), buf, "raw", "RGB", 0, 1).copy())
    return out


def sheet(images, prefix, per=6, height=640):
    """Save PIL images side by side as contact sheets <prefix>_00.png, _01.png ...; returns the paths."""
    import glob
    from PIL import Image
    for old in glob.glob(f"{prefix}_[0-9][0-9].png"):
        os.remove(old)
    paths = []
    for k in range(0, len(images), per):
        g = [im.convert("RGB").resize((max(1, round(im.width * height / im.height)), height)) for im in images[k:k + per]]
        sh = Image.new("RGB", (sum(i.width for i in g) + 8 * (len(g) - 1), height), "white")
        x = 0
        for im in g:
            sh.paste(im, (x, 0))
            x += im.width + 8
        paths.append(f"{prefix}_{k // per:02d}.png")
        sh.save(paths[-1])
    return paths


def rect_of(r):
    """rect [x1,y1,x2,y2] or circle ["c",cx,cy,r] -> ((x1,y1,x2,y2), is_circle), source pixels."""
    if r[0] == "c":
        _, cx, cy, rr = r
        return (cx - rr, cy - rr, cx + rr, cy + rr), True
    return tuple(r), False


def title_of(P, si, lang):
    t = P["steps"][si].get("title", P["steps"][si]["id"])
    if isinstance(t, dict):
        return t.get(lang) or t.get(P["primary"]) or P["steps"][si]["id"]
    return t


def lang_name(P, lang):
    return P["languages"][lang].get("name", lang)


def out_base(P, lang):
    return os.path.join(P["_out"], f"{P['_name']}_{lang_name(P, lang)}")
