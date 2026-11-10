"""One-command tutorial builder.

  python3 build.py PROJECT.json init RECORDING   write a starter project file for a recording
  python3 build.py PROJECT.json check            validate the project, show what is ready
  python3 build.py PROJECT.json look [LANG]      sample frames of the look (no voices needed) -> work/look_*.png
  python3 build.py PROJECT.json preview LANG     one still per tap with real timing -> work/preview_LANG_*.png
  python3 build.py PROJECT.json lang LANG        voice, render, mix, mux and verify ONE language
  python3 build.py PROJECT.json approve LANG     record that the user approved this edition
  python3 build.py PROJECT.json status

Rules the builder enforces:
  - one language per run; the primary language (default "en") must be approved before any other is built;
  - an approved edition is never overwritten: change output.dir to a new version folder first.
"""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, timeline

HERE = os.path.dirname(os.path.abspath(__file__))
ISO3 = dict(en="eng", hi="hin", te="tel", ta="tam", kn="kan", ml="mal", mr="mar", bn="ben", gu="guj", pa="pan",
            ur="urd", es="spa", fr="fra", de="deu", pt="por", ar="ara", id="ind", zh="zho", ja="jpn")
BT709 = "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0"


def missing(P, lang):
    out = []
    for st in P["steps"]:
        for k, b in enumerate(st.get("beats", [])):
            if not (b.get(lang) or "").strip():
                out.append(f"{st['id']}[{k}]")
    return out


def report(P):
    info, G = P["_info"], None
    import render
    G = render.Geo(P)
    taps = sum(len(s.get("taps", [])) for s in P["steps"])
    beats = sum(len(s.get("beats", [])) for s in P["steps"])
    print(f"source   {info['w']}x{info['h']} {info['dur']:.1f}s  hdr={common.hdr_kind(P) or 'no'}  crop={P['crop']}")
    print(f"output   layout={P['layout']} {G.W}x{G.H}  screen={G.scr[2]}x{G.scr[3]}  -> {P['_out']}")
    print(f"content  {len(P['steps'])} steps, {taps} taps, {beats} beats")
    for l in P["languages"]:
        m = missing(P, l)
        state = "approved" if l in P["approved"] else ("built" if os.path.exists(common.out_base(P, l) + ".mp4") else "-")
        print(f"  {l:<3} {common.lang_name(P, l):<12} lines {beats - len(m)}/{beats}  {state}" + ("  (primary)" if l == P["primary"] else ""))
    for st in P["steps"]:
        spoken = {b["at"] for b in st.get("beats", [])}
        for hi, t in enumerate(st.get("taps", [])):
            if f"h{hi}" not in spoken:
                print(f"  note: tap '{t['label']}' in step {st['id']} has no narration line (anchor h{hi})")


def check(P, lang=None):
    errs = timeline.validate(P)
    if P["primary"] not in P["languages"]:
        errs.append(f"primary language '{P['primary']}' is not in languages")
    if lang:
        if lang not in P["languages"]:
            errs.append(f"language '{lang}' is not in languages")
        elif missing(P, lang):
            m = missing(P, lang)
            errs.append(f"{len(m)} beats have no '{lang}' text: {', '.join(m[:8])}{' ...' if len(m) > 8 else ''}")
    if errs:
        common.die("project problems:\n  - " + "\n  - ".join(errs))


def tts_python(P):
    cands = [P.get("tts_python"), sys.executable, os.path.join(P["_root"], ".venv/bin/python"),
             os.path.join(P["_root"], "../.venv/bin/python"), shutil.which("python3")]
    for c in cands:
        if c and os.path.exists(c) and subprocess.run([c, "-c", "import edge_tts"], capture_output=True).returncode == 0:
            return c
    common.die('no Python with edge-tts found. Run: python3 -m pip install edge-tts   (or set "tts_python" in project.json)')


def voices(P, lang):
    r = subprocess.run([tts_python(P), os.path.join(HERE, "tts.py"), P["_path"], lang])
    if r.returncode:
        common.die("voice generation failed")
    return json.load(open(os.path.join(P["_work"], "tts", lang, "index.json")))


def rough_durs(P, lang):
    """Speech lengths guessed from text length, for look-and-feel stills before any voice exists."""
    return [[max(1.0, len(b.get(lang) or b.get(P["primary"]) or "") / 14) for b in st.get("beats", [])] for st in P["steps"]]


def stills(P, lang, plan, tag, limit=None):
    import render
    G = render.Geo(P)
    for st in P["steps"]:                                   # look may run before the lines are translated
        for b in st.get("beats", []):
            b.setdefault(lang, b.get(P["primary"], ""))
    per, _ = render.captions(P, G, lang, plan)
    holds = timeline.hold_starts(plan)
    picks = [i + int(hl * P["fps"] * 0.6) for i, hl in holds.values()]
    for t0, d, si, k in plan["cues"]:                       # and one frame for every line spoken between taps
        if P["steps"][si]["beats"][k]["at"][0] == "s":
            picks.append(int((t0 + d * 0.5) * P["fps"]))
    picks = sorted(set(picks)) or [len(plan["frames"]) // 2]
    if limit and len(picks) > limit:
        picks = [picks[round(k * (len(picks) - 1) / (limit - 1))] for k in range(limit)]
    d = os.path.join(P["_work"], f"{tag}_{lang}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    want = {f: os.path.join(d, f"f{f:06d}.png") for f in picks}
    render.render(P, G, lang, plan, per, stills=want)
    from PIL import Image
    sheets = common.sheet([Image.open(want[f]) for f in sorted(want)], os.path.join(P["_work"], f"{tag}_{lang}"), per=6, height=900)
    print("wrote", *sheets, sep="\n  ")


def mix(P, lang, plan, idx, total):
    ins, flt = [], []
    n = len(plan["audio"])
    if not n:
        common.die("there is no narration to mix")
    for i, (t, si, k) in enumerate(plan["audio"]):
        ins += ["-i", idx["files"][si][k]]
        ms = int(round(t * 1000))
        flt.append(f"[{i}:a]aresample=48000,adelay={ms}|{ms}[a{i}]")
    voice = "".join(f"[a{i}]" for i in range(n)) + (f"amix=inputs={n}:normalize=0:dropout_transition=0," if n > 1 else "") + \
        f"apad,atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000"
    fade = f"afade=t=out:st={max(total - 1.2, 0):.3f}:d=1.2[out]"
    if P.get("music"):
        ins += ["-stream_loop", "-1", "-i", os.path.join(P["_root"], P["music"])]
        flt += [voice + "[v]", f"[{n}:a]aresample=48000,volume={P.get('music_db', -26)}dB,atrim=0:{total:.3f}[m]",
                f"[v][m]amix=inputs=2:normalize=0:duration=first,{fade}"]
    else:
        flt.append(voice + "," + fade)
    out = os.path.join(P["_work"], f"audio_{lang}.m4a")
    common.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(flt), "-map", "[out]",
                "-ar", "48000", "-c:a", "aac", "-b:a", "160k", out])
    return out


def build_lang(P, lang, force=False):
    import render, text, verify
    check(P, lang)
    if lang != P["primary"] and P["primary"] not in P["approved"]:
        common.die(f"build and get the user's approval of the primary edition ('{P['primary']}') first, "
                   f"then run: build.py {os.path.basename(P['_path'])} approve {P['primary']}")
    base = common.out_base(P, lang)
    if lang in P["approved"] and os.path.exists(base + ".mp4") and not force:
        common.die(f"{base}.mp4 is an approved edition. Set output.dir to a new version folder instead of overwriting it.")
    idx = voices(P, lang)
    plan = timeline.make_plan(P, idx["durs"])
    total = len(plan["frames"]) / P["fps"]
    json.dump(plan, open(os.path.join(P["_work"], f"plan_{lang}.json"), "w"))
    G = render.Geo(P)
    per, srt = render.captions(P, G, lang, plan)
    os.makedirs(P["_out"], exist_ok=True)
    text.write_srt(base + ".srt", srt)
    with open(base + "_chapters.txt", "w", encoding="utf-8") as f:
        for si, st in enumerate(plan["steps"]):
            s = int(st["start"])
            f.write(f"{s // 60:02d}:{s % 60:02d} {common.title_of(P, si, lang)}\n")
    audio = mix(P, lang, plan, idx, total)
    vid = os.path.join(P["_work"], f"video_{lang}.mp4")
    print(f"rendering {lang}: {total:.1f} s, {G.W}x{G.H}")
    render.render(P, G, lang, plan, per, out=vid)
    iso = P["languages"][lang].get("iso", ISO3.get(lang, "und"))
    common.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", audio, "-i", base + ".srt",
                "-map", "0:v", "-map", "1:a", "-map", "2:s", "-c:v", "copy", "-bsf:v", BT709, "-c:a", "copy",
                "-c:s", "mov_text", "-metadata:s:s:0", f"language={iso}", "-metadata:s:a:0", f"language={iso}",
                "-metadata", f"title={P.get('title', P['_name'])} ({common.lang_name(P, lang)})",
                "-t", f"{total:.3f}", "-movflags", "+faststart", base + ".mp4"])
    print("wrote", base + ".mp4")
    return verify.run(P, lang)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    path, cmd, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    if cmd == "init":
        if os.path.exists(path) or not args:
            common.die("usage: build.py NEW_PROJECT.json init RECORDING   (the project file must not exist yet)")
        root = os.path.dirname(os.path.abspath(path))
        os.makedirs(root, exist_ok=True)
        rec = os.path.abspath(args[0])
        starter = {"title": "", "source": os.path.relpath(rec, root) if rec.startswith(root) else rec, "crop": None,
                   "layout": "native", "primary": "en", "approved": [],
                   "brand": {"accent": "#F58220", "ink": "#0F1729", "text": "#FFFFFF"},
                   "output": {"dir": "output/v1", "name": "Tutorial"},
                   "languages": {"en": {"name": "English", "voice": "en-IN-NeerjaNeural"}}, "steps": []}
        json.dump(starter, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("wrote", path, "- the voice is provisional; the voice director sets it later")
        return
    P = common.load(path)
    lang = args[0] if args else None
    if cmd in ("check", "status"):
        check(P)
        report(P)
    elif cmd == "look":
        check(P)
        lang = lang or P["primary"]
        for st in P["steps"]:                               # no script yet: stand-in captions from the tap labels
            if not st.get("beats"):
                st["beats"] = [{"at": f"h{i}", lang: f"Tap {t['label']}."} for i, t in enumerate(st.get("taps", []))]
        stills(P, lang, timeline.make_plan(P, rough_durs(P, lang)), "look", limit=6)
    elif cmd == "preview":
        check(P, lang or common.die("preview needs a language code"))
        plan = timeline.make_plan(P, voices(P, lang)["durs"])
        print(f"timeline: {len(plan['frames']) / P['fps']:.1f} s from a {P['_info']['dur']:.1f} s recording")
        stills(P, lang, plan, "preview")
    elif cmd == "lang":
        if len([a for a in args if not a.startswith("--")]) != 1:
            common.die("build exactly one language per run")
        sys.exit(0 if build_lang(P, lang, "--force" in args) else 2)
    elif cmd == "approve":
        if not os.path.exists(common.out_base(P, lang or "") + ".mp4"):
            common.die(f"nothing built for '{lang}' in {P['_out']}")
        common.edit(path, lambda raw: raw.setdefault("approved", []).append(lang) if lang not in raw.get("approved", []) else None)
        print(f"recorded: '{lang}' approved")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
