"""Frame composition and encoding: layout geometry, tap zoom and highlight, caption strip, progress bar.

Layouts (project "layout"):
  native    - the video is exactly the screen's shape (long side 1920); nothing but the app is on screen.
              Captions sit on a translucent strip that appears only while someone is speaking and moves to
              the top when the tap is in the lower part of the screen. A thin progress bar runs along the top.
  portrait  - strict 1080x1920; the screen fills the height (or width) and any leftover is a dimmed blur of
              the screen itself. Captions and progress as in native.
  landscape - 1920x1080 for laptops and projectors; a portrait screen sits on the left and the step title
              and caption fill a text panel on the right. A landscape source simply fills the frame.
"""
import math, re, subprocess
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import common, text, theme

ZIN, ZOUT = 0.4, 0.35      # zoom ease in / out, seconds


def even(x):
    return max(2, int(round(x)) // 2 * 2)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Geo:
    def __init__(self, P):
        _, _, CW, CH = P["crop"]
        L = P["layout"]
        self.panel = None
        if L == "native":
            k = min(1920 / max(CW, CH), 2.0)
            self.W, self.H = even(CW * k), even(CH * k)
            self.scr = (0, 0, self.W, self.H)
        else:
            self.W, self.H = (1080, 1920) if L == "portrait" else (1920, 1080)
            k = min(self.W / CW, self.H / CH)
            sw, sh = even(CW * k), even(CH * k)
            if L == "landscape" and sw <= self.W * 0.62:
                self.scr = (0, (self.H - sh) // 2, sw, sh)
                self.panel = (sw, 0, self.W - sw, self.H)
            else:
                self.scr = ((self.W - sw) // 2, (self.H - sh) // 2, sw, sh)
        sw, sh = self.scr[2:]
        self.fill = not self.panel and (sw < self.W or sh < self.H)
        self.u = min(1.2, max(0.8, min(sw, sh) / 900))
        self.bar = even(8 * self.u)
        tw = self.panel[2] if self.panel else self.W
        self.body_px = int(min(72, max(40, tw * 0.045))) if self.panel else int(min(46, max(28, tw * 0.04)))
        self.head_px = int(self.body_px * 0.68)
        self.text_w = int(tw * 0.9)
        self.text_h = int(self.H * (0.8 if self.panel else 0.2))

    def maxlen(self, s):
        wide = len(re.findall(r"[^\x00-ɏ]", s)) > len(s) / 3      # non-Latin scripts set wider
        return int(min(110, max(48, 2 * self.text_w / (self.body_px * (0.62 if wide else 0.52)))))


# ---------------------------------------------------------------- captions
def captions(P, G, lang, plan):
    """Per-output-frame caption (png_path, position) or None, plus SRT cues [(start, end, text)]."""
    FPS, nf, N = P["fps"], len(plan["frames"]), len(P["steps"])
    acc, ink_text = text.hexrgb(P["brand"]["accent"]), text.hexrgb(P["brand"]["text"])
    head_rgb = [int(v * 0.8) for v in ink_text] if theme.themed(P) else acc     # accent can clash with a step colour
    base = dict(w=G.text_w, h=G.text_h, header_px=G.head_px, body_px=G.body_px, min_px=int(G.body_px * 0.6),
                header_rgb=head_rgb, body_rgb=ink_text, align="center")
    head = lambda si: f"{si + 1} / {N}   ·   {common.title_of(P, si, lang)}"
    specs, slots, srt = [], [], []
    for t0, d, si, k in plan["cues"]:
        st = P["steps"][si]
        b = st["beats"][k]
        pos = "panel" if G.panel else "bottom"
        if not G.panel and b["at"][0] == "h":      # keep the strip off the control being tapped
            _, box, _ = tap_view(P, G, st["taps"][int(b["at"][1:])], 1.0, 2.0)
            if G.scr[1] + box[3] + 30 * G.u > G.H * 0.8:
                pos = "top"
        cs = text.chunks(b[lang], G.maxlen(b[lang]))
        wts = [max(1, len(re.sub(r"\s", "", c))) for c in cs]
        t = t0
        for ci, c in enumerate(cs):
            dd = d * wts[ci] / sum(wts)
            specs.append({**base, "header": head(si), "body": c})
            linger = 0.4 if ci == len(cs) - 1 else 0.0
            slots.append((int(round(t * FPS)), min(nf, int(round((t + dd + linger) * FPS))), len(specs) - 1, pos))
            srt.append((t, t + dd, c))
            t += dd
    titles = len(specs)                           # a step that starts without a line shows its title for a moment
    specs += [{**base, "header": "", "body": head(si)} for si in range(N)]
    idle = len(specs)
    if G.panel:                                   # the text panel always shows the step title
        specs += [{**base, "header": head(si), "body": ""} for si in range(N)]
    paths = text.blocks(P, specs)
    per = [None] * nf
    if G.panel:
        for f, fr in enumerate(plan["frames"]):
            per[f] = (paths[idle + fr[1]], "panel")
    if not G.panel and not P.get("cards"):
        for si, st in enumerate(plan["steps"]):
            f0 = int(round(st["start"] * FPS))
            for f in range(f0, min(nf, f0 + int(1.8 * FPS), int(round(st["end"] * FPS)))):
                if plan["frames"][f][2] < 0:
                    per[f] = (paths[titles + si], "bottom")
    for f0, f1, i, pos in slots:
        for f in range(f0, f1):
            per[f] = (paths[i], pos)
    return per, srt


def strip_image(P, G, path, pos, cache, bg=None):
    ink = tuple(bg or text.hexrgb(P["brand"]["ink"]))
    key = (path, pos, ink)
    if key not in cache:
        t = text.trim(path)
        if pos == "panel":
            px, py, pw, ph = G.panel
            im = Image.new("RGBA", (pw, ph), ink + (255,))
            im.alpha_composite(t, ((pw - t.width) // 2, max(0, (ph - t.height) // 2)))
            cache[key] = (im, (px, py))
        else:
            pad = int(G.body_px * 0.5)
            h = t.height + 2 * pad
            im = Image.new("RGBA", (G.W, h), ink + (222,))
            im.alpha_composite(t, ((G.W - t.width) // 2, pad))
            cache[key] = (im, (0, G.bar if pos == "top" else G.H - h))
    return cache[key]


def progress_bar(P, G, si, bg=None):
    N = len(P["steps"])
    ink, acc, tx = (tuple(text.hexrgb(P["brand"][k])) for k in ("ink", "accent", "text"))
    if theme.themed(P):
        ink, acc = tuple(bg or ink), tx
    im = Image.new("RGBA", (G.W, G.bar), ink + (235,))
    d = ImageDraw.Draw(im)
    gap = 3 if N <= 40 else 1
    for k in range(N):
        x0, x1 = round(G.W * k / N) + gap, round(G.W * (k + 1) / N) - gap
        fill = acc + (255,) if k == si else (tx + (170,) if k < si else (128, 136, 152, 150))
        d.rectangle([x0, 1, max(x0, x1), G.bar - 2], fill=fill)
    return im


# ---------------------------------------------------------------- tap highlight
def chips(P, G, lang):
    """{(step, tap): RGBA pill} naming the control, e.g. "TAP  >  Login". Set tap "chip": "" to hide one."""
    word = P["languages"][lang].get("tap_word", P.get("tap_word", "TAP"))
    acc = text.hexrgb(P["brand"]["accent"])
    on = [20, 24, 32] if (0.299 * acc[0] + 0.587 * acc[1] + 0.114 * acc[2]) > 170 else [255, 255, 255]
    keys, specs = [], []
    px = int(34 * G.u)
    for si, st in enumerate(P["steps"]):
        for hi, tap in enumerate(st.get("taps", [])):
            label = tap.get("chip", f"{word}  ›  {tap['label']}" if word else tap["label"])
            if label:
                keys.append((si, hi))
                specs.append(dict(header="", body=label, w=int(G.scr[2] * 0.9), h=px * 4, header_px=px, body_px=px,
                                  min_px=px, header_rgb=on, body_rgb=on, align="center"))
    out = {}
    for key, p in zip(keys, text.blocks(P, specs)):
        t = text.trim(p, both=True)
        padx, pady = int(18 * G.u), int(10 * G.u)
        pill = Image.new("RGBA", (t.width + 2 * padx, t.height + 2 * pady), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([0, 0, pill.width - 1, pill.height - 1], radius=pill.height // 2,
                                               fill=tuple(acc) + (255,))
        pill.alpha_composite(t, (padx, pady))
        out[key] = pill
    return out


def tap_view(P, G, tap, ht, hl):
    """Zoomed source window (for resize box=) and the tap box in screen-local output pixels."""
    X0, Y0, CW, CH = P["crop"]
    (x1, y1, x2, y2), circ = common.rect_of(tap["rect"])
    x1, x2, y1, y2 = x1 - X0, x2 - X0, y1 - Y0, y2 - Y0
    zmax = tap.get("zoom") or min(P["max_zoom"], max(min(1.12, P["max_zoom"]), 0.92 * CW / max(x2 - x1, 1)))
    z = 1 + (zmax - 1) * min(ease(ht / ZIN), ease((hl - ht) / ZOUT))
    vw, vh = CW / z, CH / z
    vx = min(max((x1 + x2) / 2, vw / 2), CW - vw / 2) - vw / 2
    vy = min(max((y1 + y2) / 2, vh / 2), CH - vh / 2) - vh / 2
    kx, ky = G.scr[2] / vw, G.scr[3] / vh
    return (vx, vy, vx + vw, vy + vh), ((x1 - vx) * kx, (y1 - vy) * ky, (x2 - vx) * kx, (y2 - vy) * ky), circ


def box_outline(G, box):
    """The drawn outline rectangle (padded and kept on screen), screen-local pixels."""
    sw, sh = G.scr[2:]
    pad = 8 * G.u
    return (max(box[0] - pad, 4), max(box[1] - pad, 4), min(box[2] + pad, sw - 4), min(box[3] + pad, sh - 4))


def highlight(P, G, box, circ, chip, ht, hl, acc):
    sw, sh = G.scr[2:]
    appear = min(ease(ht / 0.25), ease((hl - ht) / 0.2))
    if appear <= 0.05:
        return None
    bx1, by1, bx2, by2 = box_outline(G, box)
    layer = Image.new("RGBA", (sw, sh), (0, 0, 0, int(115 * appear) if P["highlight"] == "spotlight" else 0))
    d = ImageDraw.Draw(layer)
    shape = d.ellipse if circ else (lambda xy, **kw: d.rounded_rectangle(xy, radius=int(14 * G.u), **kw))
    if P["highlight"] == "spotlight":
        shape([bx1, by1, bx2, by2], fill=(0, 0, 0, 0))
    pulse = 0.5 + 0.5 * math.sin(ht * 2 * math.pi * 1.2)
    g = (4 + 6 * pulse) * G.u
    glow = tuple(min(255, c + 70) for c in acc)
    shape([bx1 - g, by1 - g, bx2 + g, by2 + g], outline=glow + (int(200 * (1 - pulse * 0.6) * appear),), width=max(2, int(4 * G.u)))
    shape([bx1, by1, bx2, by2], outline=acc + (int(255 * appear),), width=max(1, int(7 * G.u * appear)))
    if chip:
        cw, ch = chip.size
        gap = int(14 * G.u)
        x = int(min(max((bx1 + bx2) / 2 - cw / 2, 8), sw - cw - 8))
        y = by1 - ch - gap
        if y < G.bar + 8:
            y = by2 + gap
        if y + ch > sh - 6:
            y = max(G.bar + 8, by1 - ch - gap)
        c = chip
        if appear < 1:
            c = chip.copy()
            c.putalpha(chip.getchannel("A").point(lambda v: int(v * appear)))
        layer.alpha_composite(c, (x, int(y)))
    left = hl - ht
    if P["touch"] and left < 0.55:                # a fingertip-sized dot presses the control as the freeze ends
        k = 1 - left / 0.55
        grow = math.sin(min(k / 0.5, 1) * math.pi / 2)
        fade = 1 - max(0.0, (k - 0.6) / 0.4)
        r = (20 + 18 * grow) * G.u
        cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
        dot = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, int(165 * fade)),
                                    outline=(40, 44, 52, int(210 * fade)), width=max(2, int(3 * G.u)))
        layer.alpha_composite(dot)
    return layer


def redact(P, src, t):
    """Blur the project's private regions that are active at source time t."""
    X0, Y0, CW, CH = P["crop"]
    for r in P.get("redact", []):
        if r["from"] <= t <= r["to"]:
            x1, y1, x2, y2 = r["rect"]
            box = (max(0, int(x1 - X0)), max(0, int(y1 - Y0)), min(CW, int(x2 - X0)), min(CH, int(y2 - Y0)))
            if box[2] > box[0] and box[3] > box[1]:
                reg = src.crop(box)
                tiny = reg.resize((max(1, reg.width // 16), max(1, reg.height // 16)), Image.BILINEAR)
                src.paste(tiny.resize(reg.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)), box)
    return src


# ---------------------------------------------------------------- step cards
def card_text(P, G, lang):
    """One text block per step: "2 / 5" over the step title, in the text colour."""
    N, tx, m = len(P["steps"]), text.hexrgb(P["brand"]["text"]), min(G.W, G.H)
    specs = [dict(header=f"{si + 1} / {N}", body=common.title_of(P, si, lang), w=int(G.W * 0.84), h=int(G.H * 0.3),
                  header_px=int(m * 0.045), body_px=int(m * 0.085), min_px=int(m * 0.05), header_rgb=tx, body_rgb=tx,
                  align="center") for si in range(N)]
    return [text.trim(p) for p in text.blocks(P, specs)]


def card(P, G, si, src, t, L, main, dark, txt):
    """A full-colour card: a preview of the screen, the step number and title, and dots for progress.
    It rises into place, then the preview grows until it is the screen itself."""
    W, H, u, N = G.W, G.H, G.u, len(P["steps"])
    _, _, CW, CH = P["crop"]
    sx, sy, sw, sh = G.scr
    a = ease(t / 0.45)
    k = ease((t - (L - 0.55)) / 0.55) if t > L - 0.55 else 0.0
    bg = theme.mix(main, dark, k) if (G.panel or G.fill) else main
    canvas = Image.new("RGB", (W, H), bg)
    th = H * 0.44
    tw = th * CW / CH
    if tw > W * 0.8:
        tw, th = W * 0.8, W * 0.8 * CH / CW
    x0, y0 = (W - tw) / 2, H * 0.11 + (1 - a) * 50 * u
    x, y = int(x0 + (sx - x0) * k), int(y0 + (sy - y0) * k)
    w, h = max(2, int(tw + (sw - tw) * k)), max(2, int(th + (sh - th) * k))
    r, b = int(30 * u * (1 - k)), int(6 * u * (1 - k))
    d = ImageDraw.Draw(canvas)
    if b > 0:
        d.rounded_rectangle([x - b, y - b + int(12 * u), x + w + b, y + h + b + int(12 * u)], radius=r + b,
                            fill=theme.mix(bg, (0, 0, 0), 0.22 * a))
        d.rounded_rectangle([x - b, y - b, x + w + b, y + h + b], radius=r + b, fill=theme.mix(bg, (255, 255, 255), 0.92 * a))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=int(255 * a) if k == 0 else 255)
    canvas.paste(src.resize((w, h), Image.LANCZOS), (x, y), mask)
    alpha = a * (1 - k)
    if alpha > 0.02:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.alpha_composite(txt, ((W - txt.width) // 2, int(H * 0.11 + th + H * 0.055 + (1 - a) * 28 * u)))
        ld = ImageDraw.Draw(layer)
        gap, cy = 34 * u, H * 0.94
        for j in range(N):
            cx = W / 2 + (j - (N - 1) / 2) * gap
            rr = (10 if j == si else 6) * u
            ld.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 255, 255, 255 if j == si else 105))
        if alpha < 0.99:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        canvas.paste(layer, (0, 0), layer)
    return canvas


# ---------------------------------------------------------------- frames
def render(P, G, lang, plan, per, out=None, stills=None):
    """Encode the picture to `out`, or save PNG stills {output_frame_index: path}."""
    frames = plan["frames"]
    nf, FPS = len(frames), P["fps"]
    _, _, CW, CH = P["crop"]
    sx, sy, sw, sh = G.scr
    ink, acc = (tuple(text.hexrgb(P["brand"][k])) for k in ("ink", "accent"))
    chip, bars, strips, tcache, prev = chips(P, G, lang), {}, {}, {}, None
    cards = card_text(P, G, lang) if P.get("cards") else None
    dec = common.decoder(P)
    enc = None
    if out:
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{G.W}x{G.H}", "-r", str(FPS),
             "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
             "-c:v", "libx264", "-preset", "medium", "-crf", str(P.get("crf", 17)), "-profile:v", "high",
             "-x264-params", "aq-mode=3", out], stdin=subprocess.PIPE, bufsize=10**8)
    cur_idx, cur, fsz = -1, None, CW * CH * 3
    last = max(stills) if stills else None
    for oi, (sidx, si, hi, ht, hl) in enumerate(frames):
        while cur_idx < sidx:
            b = dec.stdout.read(fsz)
            if len(b) < fsz:
                break
            cur, cur_idx = b, cur_idx + 1
        if cur is None:
            common.die("could not decode any frame from the source")
        if stills is not None:
            if oi > last:
                break
            if oi not in stills:
                continue
        src = Image.frombuffer("RGB", (CW, CH), cur, "raw", "RGB", 0, 1)
        if P.get("redact"):
            src = redact(P, src.copy(), sidx / FPS)
        main, dark = theme.colours_at(P, plan, oi, tcache)
        if hi == -2:                              # step card
            canvas = card(P, G, si, src, ht, hl, main, dark, cards[si])
            if prev is not None and ht < 0.3:
                canvas = Image.blend(prev, canvas, ease(ht / 0.3))
            tail = (nf - oi) / FPS
            if stills is not None:
                canvas.save(stills[oi])
            else:
                enc.stdin.write(canvas.tobytes())
            continue
        layer = None
        if hi >= 0:
            tap = P["steps"][si]["taps"][hi]
            view, box, circ = tap_view(P, G, tap, ht, hl)
            scr = src.resize((sw, sh), Image.LANCZOS, box=view)
            layer = highlight(P, G, box, circ, chip.get((si, hi)), ht, hl, acc)
        else:
            scr = src.resize((sw, sh), Image.LANCZOS)
        if G.fill:
            small = scr.resize((max(2, G.W // 24), max(2, G.H // 24)), Image.BILINEAR)
            canvas = ImageEnhance.Brightness(small.resize((G.W, G.H), Image.BICUBIC)).enhance(0.35)
            if theme.themed(P):                   # tint the side areas with the step's colour
                canvas = Image.blend(canvas, Image.new("RGB", (G.W, G.H), dark), 0.6)
            canvas.paste(scr, (sx, sy))
        elif (sw, sh) != (G.W, G.H):
            canvas = Image.new("RGB", (G.W, G.H), dark)
            canvas.paste(scr, (sx, sy))
        else:
            canvas = scr
        if layer:
            canvas.paste(layer, (sx, sy), layer)
        if (si, dark) not in bars:
            bars[(si, dark)] = progress_bar(P, G, si, dark)
        canvas.paste(bars[(si, dark)], (0, 0), bars[(si, dark)])
        if per and per[oi]:
            im, xy = strip_image(P, G, per[oi][0], per[oi][1], strips, dark)
            canvas.paste(im, xy, im)
        prev = canvas
        tail = (nf - oi) / FPS
        if tail < 1.0:
            canvas = Image.blend(Image.new("RGB", (G.W, G.H)), canvas, max(tail, 0.0))
        if stills is not None:
            canvas.save(stills[oi])
        else:
            enc.stdin.write(canvas.tobytes())
            if oi % 1500 == 0:
                print(f"  {lang}: frame {oi}/{nf}", flush=True)
    dec.kill()
    if enc:
        enc.stdin.close()
        if enc.wait():
            common.die("video encode failed")
