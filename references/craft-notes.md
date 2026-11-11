# Craft notes: what widely watched app tutorials do

Read this before writing a script or choosing a look. It records what a study of popular videos showed, and which of their habits a training video should keep.

## What was studied
Eleven YouTube videos, found by sorting YouTube search by view count (November 2026):
- Eight app walkthroughs with 2.7 to 11.6 million views each. Hindi: two PhonePe account set-ups, Instagram basics, DigiLocker, the Zoom phone app. Bengali: creating a Telegram account. English, desktop: Zoom and Google Meet.
- Three scripted explainers from the channel Apple Explained (0.3 to 5.6 million views), studied for script writing: why the iPhone has two call screens, how AirTags work, and the top features of iOS 16.

Each video was analysed in full, picture and sound, by an AI model that reported timestamps, spoken lines and tap moments. Frames from five of the videos were also looked at directly, and they agreed with the reports. No person has checked the reports line by line. A view count shows reach and demand for the topic, not teaching quality: treat these as patterns, not proof.

## What the walkthroughs have in common
| Pattern | How consistent |
|---|---|
| **The voice names the control as it is touched.** In almost every tap sampled, the label is spoken during the tap or in the second before it. | 8 of 8 |
| **Labels are read exactly as written on screen**, in English, even inside a Hindi or Bengali sentence ("Sign In par click karenge"). | 8 of 8 |
| **Something moves to the control**: a real finger on a filmed phone (4), a mouse pointer (2), a drawn red circle (1), a green box (1). | 8 of 8 |
| **The result stays readable for 1 to 2 seconds after the tap** before the next action. | 8 of 8 |
| **Typing, installs, loading and OTP waits are cut.** | 8 of 8 |
| **The opening says what you will be able to do and what you need first** (a SIM in this phone, a number linked to the bank, an ID number). | 7 of 8 |
| **At least one thing that goes wrong is shown and fixed**: "already registered", "username not available", a forgotten PIN, a wrong number, "press Allow, not Block". | 8 of 8 |
| **Limits are said where they bite** ("uploaded documents are not treated as originals"; "without a debit card you can receive money but not send it"). | 4 of 8 |
| **The ending shows the finished result**, then a one-line recap. | 6 of 8 |
| No captions and no step titles. | 8 of 8 |

Intros before the first real step ranged from 8 seconds (the 2.5-minute Telegram video) to 52 seconds. The presenters speak at a medium, steady pace. On phones, the Hindi and Bengali presenters say "click", not "tap".

Where the analysis judged these videos hard to follow, the causes repeat: a screen skipped or only described, a jump to a different account with no explanation, several screens crossed quickly without a pause, a step shown without saying why the app asks for it, and long stretches where the screen does not change (11 seconds on a blank loading screen; 26 seconds of talk over a still).

## What the scripted explainers add
- **Start inside the viewer's experience.** The first sentence describes something the viewer has seen ("When receiving a call, you may see a screen with two buttons...") and the question arrives by second 11. No greeting first.
- **Feature, how, benefit, in one sentence.** "Requests now appear in Messages, so it's easy to approve or decline."
- **Give the reason.** "The reason is to prevent accidental answers in a pocket." A rule with a reason is remembered.
- **Limits and comfort have fixed shapes.** "Unfortunately X, but Y." "You don't have to worry, since Z."
- **Requirements are said at the step that needs them**, not in a list at the start.
- **The picture changes with every sentence**, every 3 to 8 seconds, and short labels of two or three words sit beside the thing they name ("Locked", "Double-press to decline").
- About 140 words a minute, no filler words, a one-sentence recap at the end. Taps are drawn as a white fingertip pulse.

## What to keep, and how this skill does it
1. **Name the control at the touch.** One `hN` line per tap; the engine freezes the tap for the length of its line. The touch dot (`"touch": true`, default) presses the control as the freeze ends; `"tap_sound": true` adds a soft click.
2. **Let the result be seen.** After each tap the engine plays `timing.dwell` seconds (default 1.5) at normal speed before squeezing typing and loading.
3. **Say what the viewer needs** in a card after the welcome, when something must be in hand. Say other requirements at the step that needs them.
4. **Cover what goes wrong.** Ask the user for the two or three mistakes new users make. For each, one `sN` line at that step: what they will see and what to do. If the recording shows an error or a permission prompt, keep it and narrate it; do not cut it.
5. **Say the limit and the reason** at the step, in the fixed shapes above.
6. **Never skip a screen.** Every screen the viewer will pass through appears, even if only for a moment. If the recording jumps (a different account, a pre-filled form), a line says so.
7. **One task per video.** Steps are the sections; each gets a title, shown when the step starts. For chat sharing aim for 2 to 3 minutes and offer to split a long process into parts by outcome.
8. **Blur what is private** with `redact`.
9. **End on the result**, name it, then say what to do next.
10. **Give the picture to the app**: the `native` layout. Captions and step titles stay, because trainees often watch with the sound off, which the YouTube videos do not allow for.

## What not to copy
These serve the platform, not the learner:
- Greetings, channel names, requests to subscribe, "watch till the end". The first words should be about the task. Keep the opening under 10 seconds.
- Filler and repetition ("so guys", "simply", saying the goal three times).
- Touring every feature. Teach the one task.
- A small phone on a decorated background.
- Talking over a screen that does not change for more than about 8 seconds.

## Rules for lines
- Start with the action: "Tap Save".
- One word for one action throughout. In English, "tap" on phones and "click" with a mouse. In other languages use the word people there say; in Hindi and Bengali tutorials that word is "click".
- Name the control every time, exactly as written on screen. No "tap it".
- Speak about what is on screen now.
- One sentence per line; give the reason when a step seems odd.
- A natural regional voice at a medium pace.

These agree with well-known findings on learning from video: signal where to look, split the task into segments, keep words and picture together in time, and remove what does not serve the task.
