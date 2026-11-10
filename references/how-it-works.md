# How the engine works, and why

Read this when something looks wrong or you need to change the engine.

## Colour (`common.py`, `hdr_lut.py`)
Phone mirrors and some screen recorders write HDR (10-bit, BT.2020, PQ or HLG) even though the interface is ordinary SDR. Played or converted as SDR it looks dull and grey; brightened with a levels filter it loses gradients.

The engine probes the source. For HDR it decodes with
`scale=in_color_matrix=bt2020:in_range=tv,format=rgb48le,lut3d=<lut>:interp=tetrahedral`
where the LUT maps PQ code values to sRGB: PQ curve to nits, divide by the interface white level (100 nits; 203 on some devices), BT.2020 to BT.709 primaries, sRGB curve. The work is done at 16 bits per channel so gradients survive. ffmpeg runs with `work/` as its directory and the LUT named without a path, so folders with spaces cannot break the filter.

## Timing (`timeline.py`)
| Element | Rule |
|---|---|
| Tap | Frozen for `max(hold_min, hold_pre + line + pad)`. Box and zoom appear `hold_pre` before the voice. |
| Narrated stretch | Plays at `clamp(length / (line + pad), 1, max_speed)`; if the line is longer still, the stretch plays and its last frame holds until the line ends. |
| Silent stretch | Plays at `clamp(length / quiet, 1, max_speed)`: typing, loading and retakes shrink to a few seconds. |
| End | `end_tail` seconds held, last second fading out. |

The plan is a list with one entry per output frame (which source frame, which step, which tap, how far into the freeze), plus where each voice clip and caption starts. Picture, sound, captions and checks all read that one plan, which is why they cannot drift apart.

## Picture (`render.py`, `text.py`)
Frames are composed in Python and piped to x264 once (CRF 17): source frame, zoom window, highlight layer, progress bar, caption strip. Zoom is 1.12 to `max_zoom`, larger for smaller controls, eased in and out. In the last half second of each freeze a fingertip-sized dot presses the control. Regions listed in `redact` are blurred on the source frame before anything else is drawn. Captions are split at sentence ends and commas to fit two lines, and each piece gets screen time in proportion to its length. The strip is drawn only while a line is spoken (the last piece lingers 0.4 s) and moves to the top when the tapped control is in the lower fifth of the frame.

Text is rendered to transparent PNGs by `render_text.swift` (CoreText), cached by content. Pillow without raqm cannot join Indic conjuncts, so the fallback warns when it meets a complex script.

## Sound and container (`build.py`)
Each beat is its own voice clip. The voice service ends every clip with about 0.9 s of silence, so `tts.py` measures the spoken length with `silencedetect` and the timeline uses that. Clips are placed with `adelay` and mixed with `amix=normalize=0` (the default divides the volume by the number of clips), then normalised to -16 LUFS. Music, if any, is mixed in after normalising so gaps between lines do not pump.

x264 does not write colour tags for a raw-pipe input, so players guess. The final mux stamps them without re-encoding:
`-bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0`
The mp4 carries a soft subtitle track; the same cues are written as `.srt`.

## Checks (`verify.py`)
Structure: streams, tags, frame size, length against the plan, loudness, subtitle order. Then it pulls the middle frame of every tap from the encoded file and tests that the accent-coloured outline is where the plan says and that the caption strip is present. It cannot judge wording, pronunciation or whether the box is on the right control; the sheets it writes are for a person or the inspector.

## Symptoms
| Symptom | Cause | Fix |
|---|---|---|
| Dull, grey picture | HDR not detected or wrong white level | `"hdr": "pq"`; try `"white_nits": 203` |
| Whites clipped, colours harsh | White level set too low | raise `white_nits` |
| Box on the wrong place | `rect` measured on a scaled frame, or `crop` changed after | rects are in recording pixels; rerun `tap_sheet.py` |
| Box shows the control already pressed | `t` too late | move `t` a few frames earlier |
| A line is cut off or overlaps the next | two beats on one anchor, or clips edited by hand | one beat per anchor; delete `work/tts/<lang>` |
| Broken letters in captions | Pillow fallback without raqm | build on macOS, or install libraqm |
| Voice reads an abbreviation as a word | TTS default | add it to `languages.<code>.say` |
| Stretch between taps flashes past | long silent stretch squeezed to `quiet` seconds | add an `sN` line there or raise `timing.quiet` |
