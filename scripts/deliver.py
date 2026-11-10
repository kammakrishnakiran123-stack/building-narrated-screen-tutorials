"""Share-ready extras for one built edition: a small copy under a size limit, and a thumbnail.

usage: python3 deliver.py PROJECT.json LANG [MAX_MB=28]
Writes <name>_<Language>_small.mp4 (long side at most 1280, mono voice, subtitles kept) and <name>_<Language>.jpg
next to the full edition. 28 MB keeps a comfortable margin under common chat-app limits.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, timeline

BT709 = "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0"


def main():
    P = common.load(sys.argv[1])
    lang = sys.argv[2]
    mb = float(sys.argv[3]) if len(sys.argv) > 3 else 28.0
    base = common.out_base(P, lang)
    src = base + ".mp4"
    if not os.path.exists(src):
        common.die(f"build the edition first: {src}")
    dur = float(common.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]).stdout)
    small = base + "_small.mp4"
    full_mb = os.path.getsize(src) / 1e6
    if full_mb <= mb:
        if os.path.exists(small):
            os.remove(small)
        print(f"the full edition is already {full_mb:.1f} MB, under the {mb:g} MB limit: share it as it is (no small copy made)")
    kbps = min(2500, int(mb * 8000 * 0.96 / dur - 72))
    if full_mb > mb and kbps < 150:
        common.die(f"{mb} MB is too small for {dur:.0f} s of video; raise the limit or split the tutorial")
    for attempt in range(4 if full_mb > mb else 0):
        common.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v", "-map", "0:a", "-map", "0:s?",
                    "-vf", "scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))'",
                    "-c:v", "libx264", "-preset", "slow", "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k",
                    "-bufsize", f"{kbps * 3}k", "-bsf:v", BT709, "-c:a", "aac", "-b:a", "64k", "-ac", "1",
                    "-c:s", "copy", "-movflags", "+faststart", small])
        size = os.path.getsize(small) / 1e6
        if size <= mb:
            break
        kbps = int(kbps * 0.88)
    if full_mb > mb:
        print(f"wrote {small}  {size:.1f} MB at {kbps} kb/s" + ("" if size <= mb else "  (STILL OVER THE LIMIT)"))
    plan_p = os.path.join(P["_work"], f"plan_{lang}.json")
    t = dur * 0.1
    if os.path.exists(plan_p):
        holds = sorted(timeline.hold_starts(json.load(open(plan_p))).values())
        if holds:
            t = (holds[0][0] + holds[0][1] * P["fps"] * 0.6) / P["fps"]
    common.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-q:v", "2", base + ".jpg"])
    print("wrote", base + ".jpg")


if __name__ == "__main__":
    main()
