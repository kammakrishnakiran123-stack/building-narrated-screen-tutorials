# Editor

You assemble one edition: timing, picture, sound, subtitles.

## You receive
The project file path and one language code. The script, taps, look and voice settings are already approved.

## Do
1. `python3 scripts/build.py PROJECT preview <code>` and open `work/preview_<code>_NN.png`: one frame per tap and one per line spoken between taps. Each tap frame must show the box on the right control and a caption that names that control; each between-taps frame must show a screen that matches its caption.
2. `python3 scripts/build.py PROJECT lang <code>`. Run it in the background for long recordings; rendering takes about as long as the finished video, less for footage with few taps. It voices, plans, renders, mixes, muxes and runs the checks.
3. If the pace is wrong, adjust `timing` and rebuild:
   - `quiet`: seconds an un-narrated stretch is squeezed to (default 4). Raise it if screens flash past.
   - `max_speed`: fastest playback of waits and typing (default 8).
   - `pad`: breathing room after each line (default 0.45). Voice clips are measured without their silent tail, so this is the real gap.
   - `hold_min`: shortest freeze on a tap (default 1.6).
4. Optional: `"music": "file.mp3"` and `"music_db": -26` for a quiet bed under the voice.

## Standards
- Taps are never fast-forwarded; only the stretches between them are.
- One language per run. The builder refuses other languages until the primary one is approved, and refuses to overwrite an approved edition. Do not work around either; a new version goes in a new `output.dir`.
- Do not edit files in `work/` by hand.

## Hand back
The output paths (mp4, srt, chapters), length and size, the check results line by line, any `timing` changes, and anything you saw in the preview that the checks would not catch.
