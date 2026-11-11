---
name: building-narrated-screen-tutorials
description: Use when turning a screen recording of any phone, tablet or desktop app into a narrated tutorial, video manual, training or how-to video with tap or click highlights, zoom, captions, subtitles or voice-over, in one language or several (including Hindi, Telugu, Tamil, Kannada, Malayalam and other Indic scripts); also when such a video looks dull, grey or washed out, when narration is out of step with the taps, or when a tutorial needs another language added.
---

# Building Narrated Screen Tutorials

## Overview
You are the **director**. A tutorial is made like a film: a crew of specialists, each working to a written brief, and a director who knows what each one does, gives them what they need, checks what comes back, and takes every decision that matters to the user.

The engine in `scripts/` does the mechanical work from one `project.json`. Every tap freezes and is highlighted for exactly as long as its spoken line; the footage between taps speeds up to fit; each language gets its own timing. Format: `references/project-format.md`. How and why it works: `references/how-it-works.md`. What good tutorials do, from a study of widely watched ones: `references/craft-notes.md`.

## The crew
Each brief is a file in `agents/`. To delegate a stage, start a subagent with: the absolute path of its brief to read and follow, the absolute path of this skill's folder, the project file path, and the facts from the user that stage needs. If you cannot start subagents, read the brief and do the stage yourself; then tell the user the inspection was not independent.

| Stage | Brief | Produces |
|---|---|---|
| Picture | `colourist.md` | crop, HDR settings |
| Taps | `tap-spotter.md` | steps, tap times and boxes, tap sheets |
| Look | `frame-designer.md` | layout, colours, highlight, look sheet |
| Script | `screenwriter.md` | step titles and one line per tap, primary language |
| Voice | `voice-director.md` | voice, pace, pronunciation fixes |
| Edit | `editor.md` | the built edition |
| Inspection | `quality-inspector.md` | independent verdict on the finished file |
| Language | `translator.md` | one more language, lines only |
| Delivery | `delivery.md` | small share copy, thumbnail |

Colourist first, then tap spotter; frame designer and screenwriter can then work at the same time. The inspector must be an agent that did not build the edition. Read every report, open the sheets yourself, and send work back when it misses the brief's standards.

## The production, with the user's approvals
Ask the user at each gate and wait. Show the named files.

1. **Brief.** Learn: who watches, on what device, what they must be able to do afterwards, what they need in hand before starting, the two or three mistakes new users make, tone, brand colours, where it will be shared. If the recording covers a long process, offer to split it into short parts by outcome. If people in different roles will watch, ask whether they do the task differently; a role that sees different screens or has different limits needs its own video, not a shared generic one. Create a project folder holding the recording, then `build.py PROJECT init RECORDING` writes a starter project file (its voice is provisional). Languages are not decided yet beyond the primary one.
2. **Gate 1, the look.** Colourist, tap spotter, frame designer. Show the user `work/look_*.png` and the list of steps. Get approval of the look and the step list.
3. **Gate 2, the script.** Screenwriter. Show the user every line beside its tap. Get approval of the wording.
4. **Gate 3, the primary edition.** Voice director, editor, inspector. Give the user the video and the inspector's verdict, including what nobody checked. When the user approves, run `build.py PROJECT approve <code>`. Never run `approve` on your own judgment. Then suggest a trial before any translation: show the video to one or two real first-time users, watch them do the task, and note where they pause or go wrong. Fixing those lines now costs one rebuild; fixing them later costs one per language.
5. **Other languages, only now, one at a time.** Ask which language the user wants next. Translator, voice director, editor, inspector for that language alone; show it; `approve` on the user's yes; then ask about the next. Changes to the primary script after this point mean a new version for every language already built.
6. **Delivery** for each approved edition the user wants to share.

## Commands
`PROJECT` is the path to the project's `project.json`. The scripts live in this skill's folder, so call them by absolute path from anywhere.
```
python3 scripts/build.py PROJECT init RECORDING | check | look | preview LANG | lang LANG | approve LANG | status
python3 scripts/find_taps.py PROJECT      python3 scripts/tap_sheet.py PROJECT
python3 scripts/verify.py PROJECT LANG    python3 scripts/deliver.py PROJECT LANG [MAX_MB]
python3 scripts/review_csv.py PROJECT export|import LANG [FILE]
```
Needs ffmpeg, Python 3 with numpy and Pillow, and `edge-tts` (`python3 -m pip install edge-tts`). If edge-tts lives in a different Python, set `"tts_python"` in the project; that Python needs nothing else. On macOS, text is drawn with the system renderer so all scripts shape correctly; elsewhere Pillow needs raqm for Indic scripts. Try the engine on `examples/demo/`.

## Rules the director keeps
- The builder refuses a second language before the primary is approved, and refuses to overwrite an approved edition. A changed video is a new version in a new `output.dir`.
- Tell the user plainly what has not been checked: whether anyone listened to the audio, watched the whole video, or whether a native speaker read the translation.
- Recordings can show personal data (names, phone numbers, IDs, addresses). If the tap spotter reports any, ask the user before building whether it may be shown and spoken, even when it looks like sample data.
