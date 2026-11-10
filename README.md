# building-narrated-screen-tutorials

A Claude Code skill that turns a screen recording of any app into a narrated tutorial: every tap highlighted and named, captions and subtitles, voice-over in one language or many (Indic scripts included). The agent works as a director with a crew of specialist sub-agents, builds the primary language first, and asks for approval at each stage.

## Install
```bash
git clone https://github.com/kammakrishnakiran123-stack/building-narrated-screen-tutorials ~/.claude/skills/building-narrated-screen-tutorials
```
Claude Code loads it automatically. Then ask, for example: "Make a tutorial video from this screen recording."

Requires ffmpeg, Python 3 with numpy and Pillow, and `python3 -m pip install edge-tts`. macOS gives the best text rendering (Xcode command-line tools).

## Try the engine without a recording
```bash
cd examples/demo
python3 make_demo_clip.py
python3 ../../scripts/build.py project.json look
python3 ../../scripts/build.py project.json lang en
```

## What is inside
| Path | Purpose |
|---|---|
| `SKILL.md` | The director's playbook: crew, approval gates, commands |
| `agents/` | One brief per specialist: colourist, tap spotter, frame designer, screenwriter, voice director, editor, translator, quality inspector, delivery |
| `scripts/` | The engine: build, tap finder, tap sheet, checks, delivery, review spreadsheet |
| `references/` | `project.json` format, how the engine works and why |
| `examples/demo/` | A made-up app recording and its project file |

## Layouts
`native` gives the whole frame to the app, `portrait` is a strict 1080x1920, `landscape` is 1920x1080 with a text panel for laptops and projectors.
