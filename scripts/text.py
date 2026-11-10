"""Text blocks (captions, chips) as transparent PNGs, caption chunking, SRT helpers.

Text is drawn by render_text.swift (CoreText) on macOS so Indic and other complex scripts shape correctly.
Elsewhere it falls back to Pillow, which only shapes complex scripts when built with raqm.
"""
import hashlib, json, os, re, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, features

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf",
         "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/noto/NotoSans-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/arial.ttf"]


def hexrgb(s):
    s = s.lstrip("#")
    return [int(s[i:i + 2], 16) for i in (0, 2, 4)]


def _swift(work):
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    exe, src = os.path.join(work, "render_text"), os.path.join(HERE, "render_text.swift")
    if not os.path.exists(exe) or os.path.getmtime(exe) < os.path.getmtime(src):
        subprocess.run(["swiftc", "-O", src, "-o", exe], check=True)
    return exe


def _pil(P, j):
    font_path = P.get("font") or next((f for f in FONTS if os.path.exists(f)), None)
    if not font_path:
        sys.exit('ERROR: no usable font found; set "font": "/path/to/font.ttf" in project.json')
    if not features.check("raqm") and re.search(r"[^\u0000-\u024F\u2000-\u206F]", j.get("header", "") + j.get("body", "")):
        print("WARNING: Pillow has no raqm; complex scripts may render wrongly. Build on macOS or install libraqm.",
              file=sys.stderr)
    im = Image.new("RGBA", (j["w"], j["h"]), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def wrap(text, font):
        lines, cur = [], ""
        for w in text.split():
            if cur and d.textlength(cur + " " + w, font=font) > j["w"]:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        return lines + [cur] if cur else lines

    y = 0
    for key, px_key in (("header", "header_px"), ("body", "body_px")):
        text = j.get(key, "")
        if not text:
            continue
        px = j[px_key]
        while True:
            font = ImageFont.truetype(font_path, px)
            lines = wrap(text, font)
            if key == "header" or y + len(lines) * px * 1.3 <= j["h"] or px <= j.get("min_px", 18):
                break
            px -= 2
        for ln in lines:
            x = 0 if j.get("align") == "left" else (j["w"] - d.textlength(ln, font=font)) / 2
            d.text((x, y), ln, font=font, fill=tuple(j[key + "_rgb"]) + (255,))
            y += int(px * 1.3)
        y += int(j["body_px"] * 0.3)
    im.save(j["out"])


def blocks(P, specs):
    """specs: dicts with header, body, w, h, header_px, body_px, min_px, header_rgb, body_rgb, align.
    Returns a PNG path per spec (transparent background, text top-aligned). Results are cached by content."""
    tdir = os.path.join(P["_work"], "text")
    os.makedirs(tdir, exist_ok=True)
    paths, jobs = [], {}
    for s in specs:
        p = os.path.join(tdir, hashlib.sha1(json.dumps(s, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16] + ".png")
        paths.append(p)
        if not os.path.exists(p):
            jobs[p] = {**s, "out": p}
    if jobs:
        exe = _swift(P["_work"])
        if exe:
            jp = os.path.join(tdir, "jobs.json")
            json.dump(list(jobs.values()), open(jp, "w", encoding="utf-8"), ensure_ascii=False)
            subprocess.run([exe, jp], check=True, stdout=subprocess.DEVNULL)
        else:
            for j in jobs.values():
                _pil(P, j)
    return paths


def trim(path, both=False):
    """Open a text block and crop the empty space: vertical only, or both axes (chips)."""
    im = Image.open(path).convert("RGBA")
    bb = im.getchannel("A").getbbox()
    if not bb:
        return im.crop((0, 0, im.width, 1))
    return im.crop(bb if both else (0, bb[1], im.width, bb[3]))


def chunks(text, maxlen):
    """Split a narration line into caption-sized pieces at sentence ends, then at commas."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?।;:])\s+", text) if s.strip()]
    out = []
    for s in sents:
        while len(s) > maxlen:
            cut = [m.end() for m in re.finditer(r",\s", s)]
            cut = [c for c in cut if 20 < c < len(s) - 12]
            if not cut:
                break
            c = min(cut, key=lambda c: abs(c - len(s) / 2) if len(s) < 2 * maxlen else abs(c - maxlen * 0.8))
            out.append(s[:c].strip())
            s = s[c:].strip()
        out.append(s)
    return out or [text]


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path, cues):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, c) in enumerate(cues, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{c}\n\n")
