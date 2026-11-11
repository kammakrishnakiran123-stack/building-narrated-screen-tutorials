# project.json

One file describes one tutorial. Paths are relative to the file. `build.py NEW.json init RECORDING` writes a starter. A runnable example is in `examples/demo/`.

```json
{
 "title": "Field Notes: add a note",
 "source": "recording.mp4",
 "crop": [112, 142, 730, 1672],
 "layout": "native",
 "primary": "en",
 "approved": [],
 "brand": {"accent": "#F58220", "ink": "#0F1729", "text": "#FFFFFF"},
 "output": {"dir": "output/v1", "name": "Field_Notes_Add_Note"},
 "languages": {
  "en": {"name": "English", "voice": "en-IN-NeerjaNeural"},
  "hi": {"name": "Hindi", "voice": "hi-IN-SwaraNeural", "rate": "-5%", "tap_word": "टैप", "say": {"PIN": "P I N"}}
 },
 "steps": [
  {"id": "signin",
   "title": {"en": "Sign in", "hi": "साइन इन"},
   "src": [0.0, 4.6],
   "taps": [{"t": 3.9, "rect": [60, 700, 480, 780], "label": "Sign in"}],
   "beats": [
    {"at": "s0", "en": "Welcome. You will learn to add a note.", "hi": "..."},
    {"at": "h0", "en": "Tap Sign in.", "hi": "..."}
   ]}
 ]
}
```

## Top level
| Key | Meaning | Default |
|---|---|---|
| `source` | The recording. | required |
| `crop` | `[x, y, w, h]` of the app screen inside the recording. | whole frame |
| `layout` | `native`, `portrait` (1080x1920) or `landscape` (1920x1080). | `native` |
| `primary` | Language built and approved first. | `en` |
| `approved` | Languages the user has approved. Written by `build.py approve`; do not edit by hand. | `[]` |
| `brand` | `accent` (highlight, chip, header), `ink` (caption strip, panel), `text`. | orange, navy, white |
| `highlight` | `box` or `spotlight` (dims the rest of the screen). | `box` |
| `palette` | Colour per step: `none` (one colour, `brand.ink`), `vivid`, `calm`, `brand` (grown from `brand.accent`), or your own list of hex colours. Caption strip, panels and cards take the step's colour; the tap highlight keeps `brand.accent`. | `none` |
| `cards`, `card_seconds` | Open each step with a full-colour card: screen preview, step number, title, progress dots. | `false`, `1.8` |
| `touch` | Fingertip dot that presses the control as each freeze ends. | `true` |
| `tap_sound` | Soft click at each tap. | `false` |
| `redact` | Regions to blur: `[{"from": 0, "to": 4.2, "rect": [x1, y1, x2, y2]}]`, in recording seconds and pixels. | none |
| `max_zoom` | Largest zoom on a tap. Small controls zoom most. | `1.3` |
| `tap_word` | Chip prefix: "TAP", "CLICK", or "" for the label alone. Per language too. | `TAP` |
| `hdr`, `white_nits` | `auto`, `pq`, `hlg`, `off`; UI white level for PQ. | `auto`, `100` |
| `timing` | `hold_pre`, `hold_min`, `pad`, `quiet`, `dwell`, `max_speed`, `end_tail`. | see `scripts/common.py` |
| `fps`, `crf` | Output frame rate and x264 quality. | `30`, `17` |
| `music`, `music_db` | Optional background track and its level. | none, `-26` |
| `font` | Font file for the non-macOS text fallback. | system |
| `tts_python` | Python that has `edge-tts`, if not the current one. | auto-detected |
| `output` | `dir` (use a new folder per version) and `name` (file name stem). | `output/v1`, `Tutorial` |

## Languages
`name` is used in file names. `voice` is an edge-tts voice. `rate` such as `"-8%"`. `say` maps text to how the voice should speak it; captions are untouched. `iso` sets the three-letter subtitle language tag when the code is not a common one.

## Steps
- `src`: `[start, end]` seconds of the recording this step covers. Steps normally run back to back. A step with `start == end` is a still card (for an intro line).
- `taps`, in time order. `t` is the last frame before the tap takes effect. `rect` is `[x1, y1, x2, y2]` in recording pixels, or `["c", cx, cy, r]`. `label` is the control's visible text. Optional `zoom` and `chip`.
- `beats`: narration lines. `at` is the anchor:
  - `hN`: spoken while tap N is frozen and highlighted. The freeze lasts as long as the line.
  - `sN`: spoken over the stretch before tap N (`s0` is the start of the step; `s<number of taps>` is after the last tap). If the line needs more time than the stretch has, the stretch plays and then its last frame holds.
  - Each anchor is used at most once per step. Each beat holds one text per language code.

Every language shares the same beats, so structure cannot drift between languages. A language is buildable when every beat has its text; `build.py check` shows the count.

## What the engine writes
`work/` holds caches (voices, text images, LUT, plans, sheets) and can be deleted. `output.dir` holds, per language, `<name>_<Language>.mp4` with a subtitle track, `.srt`, `_chapters.txt`, and after delivery `_small.mp4` and `.jpg`.
