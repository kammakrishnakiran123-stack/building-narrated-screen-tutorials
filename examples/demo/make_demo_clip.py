"""Draw a made-up phone app recording (18 s, 540x1170) so the skill can be tried without a real recording.

usage: python3 make_demo_clip.py [OUT=demo.mp4]
The app is "Field Notes": sign in (tap at 4.0 s), press + (9.0 s), type a title, press Save (14.0 s).
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 540, 1170, 30, 18.0
FONTS = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "C:/Windows/Fonts/arial.ttf"]
FP = next((f for f in FONTS if os.path.exists(f)), None)
GREEN, DARK, GREY, BG = (22, 130, 92), (14, 92, 64), (120, 128, 140), (246, 247, 249)


def font(px):
    return ImageFont.truetype(FP, px) if FP else ImageFont.load_default(px)


def base(title):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 120], fill=GREEN)
    d.text((30, 62), title, font=font(34), fill="white", anchor="lm")
    return im, d


def button(d, box, label, pressed):
    d.rounded_rectangle(box, radius=16, fill=DARK if pressed else GREEN)
    d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, font=font(30), fill="white", anchor="mm")


def login(pressed):
    im, d = base("Field Notes")
    d.text((60, 420), "Mobile number", font=font(24), fill=GREY)
    d.rounded_rectangle([60, 460, 480, 540], radius=12, outline=GREY, width=2, fill="white")
    d.text((80, 500), "98765 43210", font=font(30), fill=(30, 34, 40), anchor="lm")
    button(d, [60, 700, 480, 780], "Sign in", pressed)
    return im


def home(notes, fab_pressed=False, toast=False):
    im, d = base("My notes")
    for k, n in enumerate(notes):
        y = 160 + k * 130
        d.rounded_rectangle([30, y, 510, y + 110], radius=14, fill="white", outline=(225, 228, 232))
        d.text((54, y + 38), n, font=font(28), fill=(30, 34, 40), anchor="lm")
        d.text((54, y + 78), "Today", font=font(20), fill=GREY, anchor="lm")
    d.ellipse([420, 1000, 500, 1080], fill=DARK if fab_pressed else GREEN)
    d.text((460, 1038), "+", font=font(54), fill="white", anchor="mm")
    if toast:
        d.rounded_rectangle([110, 900, 430, 960], radius=30, fill=(40, 44, 52))
        d.text((270, 930), "Note saved", font=font(24), fill="white", anchor="mm")
    return im


def form(typed, pressed):
    im, d = base("New note")
    d.text((60, 220), "Title", font=font(24), fill=GREY)
    d.rounded_rectangle([60, 260, 480, 340], radius=12, outline=GREEN, width=3, fill="white")
    d.text((80, 300), typed + ("|" if not pressed else ""), font=font(30), fill=(30, 34, 40), anchor="lm")
    button(d, [60, 900, 480, 980], "Save", pressed)
    return im


def frame(t):
    notes = ["Soil test - plot 4", "Seed order"]
    title = "Visit Ravi's farm"
    if t < 4.0:
        return login(False)
    if t < 4.2:
        return login(True)
    if t < 9.0:
        return home(notes)
    if t < 9.2:
        return home(notes, fab_pressed=True)
    if t < 14.0:
        n = int(min(max((t - 10.0) / 0.2, 0), len(title)))
        return form(title[:n], False)
    if t < 14.2:
        return form(title, True)
    return home([title] + notes, toast=t < 16.5)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        enc.stdin.write(frame(i / FPS).tobytes())
    enc.stdin.close()
    enc.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
