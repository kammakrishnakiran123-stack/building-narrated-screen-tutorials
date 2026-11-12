"""Written guide and click-through page from the same project, for one language.

usage: python3 guide.py PROJECT.json LANG
Writes, next to the video:
  <name>_<Language>_guide.html        every tap as a numbered screenshot with its instruction; prints cleanly
  <name>_<Language>_guide.pdf         the same as A4 pages
  <name>_<Language>_interactive.html  a click-through: the viewer taps the highlighted control to move on
The web pages are single files with the pictures inside them, and the voice too if the edition has been voiced.
Lines missing in LANG fall back to the primary language, so a guide can be drafted before translation.
"""
import base64, html, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import common, render, text, theme

UI = {"hint": "Tap the highlighted control", "next": "Next", "back": "Back", "again": "Start again", "sound": "Sound"}


def collect(P, lang):
    """Ordered items, one per tap plus one for each closing line: dicts with si, kind, t, v, rect, lines.
    lines = [(beat index or None, text)]; for a tap the last line is the instruction, earlier ones are context."""
    pri, items = P["primary"], []
    for si, st in enumerate(P["steps"]):
        taps = st.get("taps", [])
        by = {b["at"]: (k, b.get(lang) or b.get(pri) or "") for k, b in enumerate(st.get("beats", []))}
        v = common.view(P, si)
        for hi, tap in enumerate(taps):
            lines = [by[a] for a in (f"s{hi}", f"h{hi}") if a in by]
            if f"h{hi}" not in by:
                lines.append((None, tap["label"]))
            items.append(dict(si=si, kind="tap", t=tap["t"], v=v, rect=tap["rect"], lines=lines))
        tail = by.get(f"s{len(taps)}")
        if tail:
            items.append(dict(si=si, kind="info", t=max(st["src"][0], st["src"][1] - 0.05), v=v, rect=None, lines=[tail]))
    if items and items[-1]["kind"] == "tap":                 # always finish on the result, not on a button
        st = P["steps"][-1]
        items.append(dict(si=len(P["steps"]) - 1, kind="info", t=max(st["src"][0], st["src"][1] - 0.05),
                          v=common.view(P, len(P["steps"]) - 1), rect=None, lines=[]))
    groups = {}
    for it in items:
        groups.setdefault(it["v"]["key"], []).append(it)
    for group in groups.values():
        v = group[0]["v"]
        shots = common.frames_at(P, [it["t"] for it in group], v=v)
        for it in group:
            im = shots[it["t"]]
            it["img"] = render.redact(P, im.copy(), it["t"], v) if P.get("redact") else im
            if it["rect"]:
                (x1, y1, x2, y2), it["circ"] = common.rect_of(it["rect"])
                X0, Y0 = v["crop"][:2]
                it["box"] = (x1 - X0, y1 - Y0, x2 - X0, y2 - Y0)
    return items


def jpeg_uri(im, width, q=80):
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), im.size


def marked(P, it, width, n=None):
    """The screenshot at a width, with the tap box (and its number) drawn on it."""
    im = it["img"].resize((width, round(it["img"].height * width / it["img"].width)), Image.LANCZOS)
    if it["rect"]:
        k = width / it["img"].width
        acc = tuple(text.hexrgb(P["brand"]["accent"]))
        x1, y1, x2, y2 = (c * k for c in it["box"])
        pad, d = 6, ImageDraw.Draw(im)
        box = [max(2, x1 - pad), max(2, y1 - pad), min(im.width - 3, x2 + pad), min(im.height - 3, y2 + pad)]
        (d.ellipse if it["circ"] else lambda b, **kw: d.rounded_rectangle(b, radius=10, **kw))(box, outline=acc, width=5)
        if n is not None:
            r = max(15, width // 26)
            cx, cy = max(r + 2, box[0]), max(r + 2, box[1])
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=acc, outline=(255, 255, 255), width=2)
            try:
                d.text((cx, cy), str(n), fill=(255, 255, 255), anchor="mm", font=ImageFont.load_default(int(r * 1.2)))
            except Exception:
                pass
    return im


def step_colour(P, si):
    return "#%02x%02x%02x" % theme.pairs(P)[si][0]


def write_html(P, lang, items, path):
    e = html.escape
    out = [f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           f"<title>{e(P.get('title') or P['_name'])}</title><style>",
           'body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif;max-width:860px;margin:0 auto;'
           'padding:24px;color:#1c2028;line-height:1.45}h1{font-size:28px;margin:0 0 4px}.sub{color:#667;margin:0 0 20px}',
           'h2{color:#fff;padding:10px 16px;border-radius:10px;font-size:20px;margin:30px 0 6px;break-after:avoid}',
           '.item{display:flex;gap:26px;align-items:flex-start;margin:20px 0;break-inside:avoid}',
           '.item img{width:250px;flex:none;border:1px solid #d5d9e0;border-radius:14px}.wide img{width:420px}',
           f".n{{display:inline-block;min-width:34px;height:34px;line-height:34px;text-align:center;border-radius:17px;"
           f"background:{P['brand']['accent']};color:#fff;font-weight:700;margin-bottom:8px}}",
           '.do{font-size:19px;font-weight:600;margin:0 0 8px}.ctx{color:#4a5160;margin:0 0 8px}',
           '@media(max-width:620px){.item{flex-direction:column}.item img,.wide img{width:100%}}',
           '@media print{body{padding:0}h2{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style></head><body>',
           f"<h1>{e(P.get('title') or P['_name'])}</h1><p class=sub>{e(common.lang_name(P, lang))}</p>"]
    n, last = 0, None
    for it in items:
        if it["si"] != last:
            last = it["si"]
            out.append(f'<h2 style="background:{step_colour(P, last)}">{last + 1}. {e(common.title_of(P, last, lang))}</h2>')
        wide = it["img"].width > it["img"].height
        if it["kind"] == "tap":
            n += 1
        uri, _ = jpeg_uri(marked(P, it, 840 if wide else 500, n if it["kind"] == "tap" else None), 840 if wide else 500)
        body = "".join(f'<p class="{"do" if (j == len(it["lines"]) - 1 and it["kind"] == "tap") else "ctx"}">{e(t)}</p>'
                       for j, (_, t) in enumerate(it["lines"]))
        badge = f'<span class=n>{n}</span>' if it["kind"] == "tap" else ""
        out.append(f'<div class="item{" wide" if wide else ""}"><img src="{uri}" alt=""><div>{badge}{body}</div></div>')
    out.append("</body></html>")
    open(path, "w", encoding="utf-8").write("\n".join(out))


def write_pdf(P, lang, items, path):
    PW, PH, M = 1240, 1754, 90                    # A4 at 150 dpi
    acc, dark, grey = text.hexrgb(P["brand"]["accent"]), [28, 32, 40], [74, 81, 96]
    tb = lambda **kw: dict(header="", body="", w=PW - 2 * M, h=700, header_px=30, body_px=30, min_px=22,
                           header_rgb=acc, body_rgb=dark, align="left", **kw)
    specs = [{**tb(), "body": P.get("title") or P["_name"], "body_px": 52, "min_px": 36},
             {**tb(), "body": common.lang_name(P, lang), "body_rgb": grey}]
    steps = sorted({it["si"] for it in items})
    specs += [{**tb(), "body": f"{si + 1}.  {common.title_of(P, si, lang)}", "body_rgb": [255, 255, 255], "body_px": 34,
               "w": PW - 2 * M - 48} for si in steps]
    rows, n = [], 0
    for it in items:
        wide = it["img"].width > it["img"].height
        iw = 560 if wide else round(600 * it["img"].width / it["img"].height)
        if it["kind"] == "tap":
            n += 1
        ctx = "\n\n".join(t for _, t in it["lines"][:-1]) if it["kind"] == "tap" else ""
        main = it["lines"][-1][1] if it["lines"] else ""
        rows.append((it, iw, n if it["kind"] == "tap" else None, len(specs)))
        specs.append({**tb(), "w": PW - 2 * M - iw - 44, "header": str(n) if it["kind"] == "tap" else "",
                      "header_px": 40, "body": (ctx + "\n\n" if ctx else "") + main})
    blocks = [text.trim(p) for p in text.blocks(P, specs)]
    pages, y = [Image.new("RGB", (PW, PH), "white")], M

    def page_for(h):
        """The page with room for h more pixels (a new one if the current page is full)."""
        nonlocal y
        if y + h > PH - M:
            pages.append(Image.new("RGB", (PW, PH), "white"))
            y = M
        return pages[-1]
    for b in blocks[:2]:
        page_for(b.height).paste(b, (M, y), b)
        y += b.height + 14
    y += 20
    last = None
    for it, iw, num, bi in rows:
        img = marked(P, it, iw, num)
        tblock = blocks[bi]
        rh = max(img.height, tblock.height)
        if it["si"] != last:
            last = it["si"]
            hb = blocks[2 + steps.index(last)]
            bh = hb.height + 30
            pg = page_for(bh + 30 + rh)                      # keep a heading with its first row
            ImageDraw.Draw(pg).rounded_rectangle([M, y, PW - M, y + bh], radius=16, fill=theme.pairs(P)[last][0])
            pg.paste(hb, (M + 24, y + 15), hb)
            y += bh + 30
        pg = page_for(rh)
        pg.paste(img, (M, y))
        ImageDraw.Draw(pg).rectangle([M, y, M + img.width - 1, y + img.height - 1], outline=(213, 217, 224), width=2)
        pg.paste(tblock, (M + iw + 44, y + 6), tblock)
        y += rh + 44
    pages[0].save(path, save_all=True, append_images=pages[1:], resolution=150)
    return len(pages)


PAGE = r"""<!doctype html><html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#0b0f18;color:#fff;
font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif}
#app{height:100%;display:flex;flex-direction:column;align-items:center;--accent:__ACCENT__}
#top{width:100%;max-width:560px;padding:12px 16px 4px}
#bar{display:flex;gap:4px}#bar i{flex:1;height:5px;border-radius:3px;background:#ffffff38}
#bar i.done{background:#ffffffb0}#bar i.on{background:var(--accent)}
#title{font-size:14px;opacity:.85;margin-top:8px}
#stage{flex:1;min-height:0;width:100%;display:flex;align-items:center;justify-content:center;padding:8px 16px}
#shot{position:relative;display:inline-block;line-height:0;border-radius:14px;overflow:hidden;box-shadow:0 8px 30px #0009}
#shot img{display:block;max-width:100%;max-height:calc(100vh - 250px)}
#hot{position:absolute;border:4px solid var(--accent);border-radius:12px;cursor:pointer;animation:pulse 1.3s infinite}
#hot.circ{border-radius:50%}
@keyframes pulse{0%{box-shadow:0 0 0 0 var(--accent)}70%{box-shadow:0 0 0 16px #0000}100%{box-shadow:0 0 0 0 #0000}}
#hot.miss{animation:shake .35s}
@keyframes shake{25%{transform:translateX(-7px)}75%{transform:translateX(7px)}}
#cap{width:100%;max-width:560px;padding:10px 16px 16px;min-height:150px}
#cap p{margin:0 0 6px;font-size:18px;line-height:1.35}#cap p.ctx{opacity:.72;font-size:16px}
#hint{font-size:13px;opacity:.65;min-height:18px}
#nav{display:flex;gap:10px;align-items:center;margin-top:10px}#nav span{flex:1}
button{font:inherit;border:0;border-radius:999px;padding:10px 20px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
button.quiet{background:#ffffff24}button:disabled{opacity:.35}
</style></head><body><div id="app">
<div id="top"><div id="bar"></div><div id="title"></div></div>
<div id="stage"><div id="shot"><img id="img" alt=""><div id="hot"></div></div></div>
<div id="cap"><div id="lines"></div><div id="hint"></div>
<div id="nav"><button id="back" class="quiet"></button><button id="snd" class="quiet"></button><span></span><button id="next"></button></div></div>
</div><script>
const D=__DATA__;let i=0,sound=true,started=false,q=[];const A=new Audio(),$=id=>document.getElementById(id);
D.steps.forEach(()=>$('bar').appendChild(document.createElement('i')));
A.onended=()=>{if(q.length){A.src=q.shift();A.play().catch(()=>{})}};
function say(list){A.pause();q=list.slice();if(q.length&&sound&&started){A.src=q.shift();A.play().catch(()=>{})}}
function show(){const it=D.items[i];$('img').src=it.img;
 [...$('bar').children].forEach((b,k)=>b.className=k<it.si?'done':k==it.si?'on':'');
 $('title').textContent=(it.si+1)+' / '+D.steps.length+'  ·  '+D.steps[it.si];
 $('lines').innerHTML='';it.lines.forEach((t,k)=>{const p=document.createElement('p');p.textContent=t;
  if(it.box&&k<it.lines.length-1)p.className='ctx';$('lines').appendChild(p)});
 const h=$('hot');if(it.box){h.style.display='block';h.className=it.circ?'circ':'';
  h.style.left=it.box[0]+'%';h.style.top=it.box[1]+'%';h.style.width=it.box[2]+'%';h.style.height=it.box[3]+'%';
  $('next').style.display='none';$('hint').textContent=D.ui.hint}
 else{h.style.display='none';$('next').style.display='';$('next').textContent=i==D.items.length-1?D.ui.again:D.ui.next;$('hint').textContent=''}
 $('back').disabled=i==0;say(it.audio)}
function go(d){started=true;i=i+d>=D.items.length?0:Math.max(0,i+d);show()}
$('hot').onclick=e=>{e.stopPropagation();go(1)};
$('shot').onclick=()=>{started=true;if(D.items[i].box){const h=$('hot');h.classList.remove('miss');void h.offsetWidth;h.classList.add('miss')}};
$('next').onclick=()=>go(1);$('back').onclick=()=>go(-1);$('back').textContent=D.ui.back;
$('snd').textContent='🔊 '+D.ui.sound;$('snd').style.display=D.voiced?'':'none';
$('snd').onclick=()=>{sound=!sound;started=true;$('snd').textContent=(sound?'🔊 ':'🔇 ')+D.ui.sound;if(sound)say(D.items[i].audio);else A.pause()};
document.onkeydown=e=>{if(e.key=='ArrowRight')go(1);if(e.key=='ArrowLeft')go(-1)};show();
</script></body></html>"""


def write_interactive(P, lang, items, path):
    idx_p = os.path.join(P["_work"], "tts", lang, "index.json")
    files = json.load(open(idx_p))["files"] if os.path.exists(idx_p) else None
    data = {"steps": [common.title_of(P, si, lang) for si in range(len(P["steps"]))], "items": [],
            "ui": {**UI, **P["languages"].get(lang, {}).get("ui", {})}, "voiced": False}
    for it in items:
        wide = it["img"].width > it["img"].height
        uri, (w, h) = jpeg_uri(it["img"], 960 if wide else 640, 78)
        box = None
        if it["rect"]:
            W0, H0 = it["img"].size
            x1, y1, x2, y2 = it["box"]
            pad = 0.012 * W0
            x1, y1, x2, y2 = max(0, x1 - pad), max(0, y1 - pad), min(W0, x2 + pad), min(H0, y2 + pad)
            box = [round(100 * x1 / W0, 2), round(100 * y1 / H0, 2), round(100 * (x2 - x1) / W0, 2), round(100 * (y2 - y1) / H0, 2)]
        audio = []
        if files:
            for k, _ in it["lines"]:
                f = files[it["si"]][k] if k is not None and it["si"] < len(files) and k < len(files[it["si"]]) else None
                if f and os.path.exists(f):
                    audio.append("data:audio/mpeg;base64," + base64.b64encode(open(f, "rb").read()).decode())
                    data["voiced"] = True
        data["items"].append({"si": it["si"], "img": uri, "box": box, "circ": bool(it.get("circ")),
                              "lines": [t for _, t in it["lines"]], "audio": audio})
    page = (PAGE.replace("__LANG__", lang).replace("__TITLE__", html.escape(P.get("title") or P["_name"]))
            .replace("__ACCENT__", P["brand"]["accent"]).replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    open(path, "w", encoding="utf-8").write(page)
    return data["voiced"]


def run(P, lang):
    if lang not in P["languages"]:
        common.die(f"language '{lang}' is not in languages")
    items = collect(P, lang)
    if not items:
        common.die("the project has no taps or lines yet")
    os.makedirs(P["_out"], exist_ok=True)
    base = common.out_base(P, lang)
    write_html(P, lang, items, base + "_guide.html")
    pages = write_pdf(P, lang, items, base + "_guide.pdf")
    voiced = write_interactive(P, lang, items, base + "_interactive.html")
    taps = sum(1 for it in items if it["kind"] == "tap")
    for suffix, note in (("_guide.html", f"{taps} taps"), ("_guide.pdf", f"{pages} pages"),
                         ("_interactive.html", "with voice" if voiced else "no voice yet: build the video first to add it")):
        print(f"wrote {base + suffix}  ({os.path.getsize(base + suffix) / 1e6:.1f} MB, {note})")


if __name__ == "__main__":
    run(common.load(sys.argv[1]), sys.argv[2])
