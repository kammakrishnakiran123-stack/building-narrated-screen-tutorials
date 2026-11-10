# Craft notes: what widely watched app tutorials do

Read this before writing a script or choosing a look. It records what a small study of popular tutorials showed, and which of their habits a training video should keep.

## What was studied
Seven app walkthroughs on YouTube with 2.7 to 11.6 million views each (November 2026), found by sorting YouTube search by view count: two PhonePe account set-ups, Instagram basics, DigiLocker and a Zoom app guide (Hindi), and Zoom and Google Meet (English, desktop). Frames from five were looked at directly; the content and section timings of all seven came from an AI summary of each video. Nobody listened to the narration word for word, so points about wording rest on the summaries. A view count shows reach, not teaching quality; treat these as patterns, not proof.

## What they have in common
| Pattern | Seen in |
|---|---|
| The opening says what the app is for, what you will be able to do, and **what you need before you start** (a SIM in the phone, a number linked to the bank, an ID number). | PhonePe, DigiLocker, Instagram |
| The body is a chain of named sections, 20 to 60 seconds each, one sub-task per section. | all seven |
| The tap is shown by something that moves to the control: a real finger on a hand-held phone, a mouse pointer, or a red circle with a zoom. | finger: Instagram, DigiLocker, PhonePe; circle and zoom: Zoom |
| Limits and consequences are said at the step where they bite ("uploaded documents are not treated as originals"; "without a debit card you cannot set the PIN, but you can still receive money"). | DigiLocker, PhonePe |
| Private details on screen are blurred. | PhonePe |
| The ending holds on the finished result, then says what to do next. | PhonePe (QR code), Zoom |
| The phone fills the frame only when it is filmed in the hand. In edited 16:9 videos it is often under a quarter of the picture. | PhonePe, DigiLocker |

## What to keep, and how this skill does it
1. **Say what the viewer needs before step one.** One still-card line after the welcome: "Keep your registered mobile number and your ID card ready."
2. **One task per video; sections inside it.** Each step is a section with a title. For sharing in chat apps, aim for 2 to 3 minutes: split a long process into parts by outcome ("Part 1: Sign in", "Part 2: Add a customer") and offer that to the user.
3. **Show the touch.** The box and chip say where; the touch dot (`"touch": true`, the default) presses the control as the freeze ends, like a fingertip. `"tap_sound": true` adds a soft click. Use `spotlight` on crowded screens.
4. **Say the limit at the step.** If a step can fail or looks different for some users, one `sN` line there: what they will see and what to do.
5. **Blur what is private.** `"redact": [{"from": 0, "to": 4.2, "rect": [x1, y1, x2, y2]}]` blurs a region of the recording between two source times.
6. **End on the result.** The last step's final line names what the viewer can now see on screen; a closing card says what to do next.
7. **Give the picture to the app.** The `native` layout does what the hand-held videos do.

## What not to copy
These serve the platform, not the learner:
- Long personal intros, channel branding, requests to like or subscribe.
- Padding and repetition to reach a target length.
- Touring every feature of the app. Teach the one task the viewer came for.
- A small phone on a decorated background.

## Narration rules these videos and the research agree on
- Start the line with the action: "Tap Save", not "The Save button is what you need".
- One word for one action throughout: "tap" on phones, "click" with a mouse.
- Name the control every time. No "tap it" or "press that".
- Speak about what is on screen now. The engine times each tap line to its freeze; `sN` lines must describe their own stretch.
- Leave a breath after a step that changes the screen (`timing.pad`), so the viewer can find their place.
- Use a natural regional voice at an unhurried pace.

These follow well-known findings on learning from video: signal where to look, split the task into segments, keep words and picture together in time, and remove anything that does not serve the task.
