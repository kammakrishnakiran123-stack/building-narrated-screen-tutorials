"""One edge-tts clip per narration beat, for one language.

usage: <python with edge-tts> tts.py project.json LANG
Writes work/tts/<lang>/<step>_<beat>_<hash>.mp3 and work/tts/<lang>/index.json {"files": [[..]], "durs": [[..]]}.
The hash covers the spoken text, voice and rate, so an edited line is re-voiced and untouched lines are reused.
languages.<lang>.say = {"PIN": "P I N"} replaces text for the voice only (captions keep the original).
"""
import asyncio, hashlib, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def spoken(text, say):
    for k, v in (say or {}).items():
        text = text.replace(k, v)
    return text


async def one(path, text, voice, rate, sem):
    import edge_tts
    async with sem:
        for attempt in range(5):
            try:
                await edge_tts.Communicate(text, voice, rate=rate).save(path)
                if os.path.getsize(path) > 1000:
                    return
            except Exception as e:
                print("retry", os.path.basename(path), e, file=sys.stderr)
            await asyncio.sleep(2 + attempt * 2)
        raise RuntimeError(f"tts failed: {path}")


def dur(p):
    """Seconds of actual speech: clip length minus the silent tail the voice service appends."""
    total = float(common.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).stdout)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "silencedetect=noise=-45dB:d=0.25",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", log)]
    if starts and starts[-1] > 0.2 and (len(ends) < len(starts) or ends[-1] >= total - 0.05):
        return min(total, starts[-1] + 0.1)
    return total


def main(project, lang):
    P = common.load(project)
    L = P["languages"].get(lang) or common.die(f"language '{lang}' is not in project.languages")
    voice, rate = L.get("voice") or common.die(f"languages.{lang}.voice is missing"), L.get("rate", "+0%")
    out = os.path.join(P["_work"], "tts", lang)
    os.makedirs(out, exist_ok=True)
    files, jobs = [], []
    for si, st in enumerate(P["steps"]):
        row = []
        for k, b in enumerate(st.get("beats", [])):
            text = spoken(b.get(lang) or common.die(f"step {st['id']} beat {k} has no '{lang}' text"), L.get("say"))
            h = hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:8]
            p = os.path.join(out, f"{si:02d}_{k}_{h}.mp3")
            row.append(p)
            if not (os.path.exists(p) and os.path.getsize(p) > 1000):
                jobs.append((p, text))
        files.append(row)

    async def go():
        sem = asyncio.Semaphore(6)
        await asyncio.gather(*(one(p, t, voice, rate, sem) for p, t in jobs))
    if jobs:
        asyncio.run(go())
    durs = [[round(dur(p), 3) for p in row] for row in files]
    json.dump({"files": files, "durs": durs}, open(os.path.join(out, "index.json"), "w"), indent=1)
    print(f"{lang}: {sum(map(len, files))} beats, {len(jobs)} newly voiced, {sum(map(sum, durs)):.1f} s of speech")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
