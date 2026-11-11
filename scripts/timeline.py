"""Per-language output timeline: every tap freezes for as long as its line takes; the rest speeds up to fit.

plan = {
  "frames": [src_frame_idx, step, tap_idx (-1 = none), t_in_hold, hold_len]  one per output frame,
  "steps":  [{"id", "start", "end"}]      output seconds (chapters),
  "audio":  [[t_out, step, beat]]         where each narration clip starts,
  "cues":   [[t_out, dur, step, beat]]    caption / SRT timing,
}
Beat anchors ("at"): "hN" = spoken while tap N is frozen and highlighted; "sN" = spoken over the stretch of
video before tap N (s<number of taps> = after the last tap); if the line is longer than the stretch, the
stretch plays and then its last frame holds until the line ends.
"""


def validate(P):
    """Structural problems in steps/taps/beats, as a list of strings."""
    errs = []
    dur = P["_info"]["dur"]
    for si, st in enumerate(P["steps"]):
        sid = st.get("id", f"#{si}")
        a, b = st.get("src", [0, 0])
        if not (0 <= a <= b <= dur + 0.5):
            errs.append(f"step {sid}: src {a}-{b} outside the recording (0-{dur:.1f})")
        taps = st.get("taps", [])
        ts = [t["t"] for t in taps]
        if ts != sorted(ts):
            errs.append(f"step {sid}: taps must be listed in time order")
        for t in taps:
            if not (a <= t["t"] <= b):
                errs.append(f"step {sid}: tap '{t.get('label')}' at {t['t']} is outside src {a}-{b}")
        seen = set()
        for k, bt in enumerate(st.get("beats", [])):
            at = bt.get("at", "")
            ok = len(at) > 1 and at[0] in "hs" and at[1:].isdigit()
            if not ok or (at[0] == "h" and int(at[1:]) >= len(taps)) or (at[0] == "s" and int(at[1:]) > len(taps)):
                errs.append(f"step {sid} beat {k}: bad anchor '{at}' ({len(taps)} taps)")
            if at in seen:
                errs.append(f"step {sid}: two beats share anchor '{at}'")
            seen.add(at)
    return errs


def make_plan(P, durs):
    """durs[step][beat] = seconds of speech for the language being built."""
    T = P["timing"]
    FPS = P["fps"]
    frames, audio, cues, steps = [], [], [], []
    now = lambda: len(frames) / FPS
    si = 0

    def play(a, b, v):
        n = int(round((b - a) / v * FPS))
        for k in range(n):
            frames.append([int(round((a + (b - a) * k / n) * FPS)), si, -1, 0.0, 0.0])

    def freeze(a, L):
        for _ in range(int(round(L * FPS))):
            frames.append([int(round(a * FPS)), si, -1, 0.0, 0.0])

    for si, st in enumerate(P["steps"]):
        s0, s1 = st["src"]
        taps = st.get("taps", [])
        lines = {b["at"]: (k, durs[si][k]) for k, b in enumerate(st.get("beats", []))}
        bounds = [s0] + [t["t"] for t in taps] + [s1]
        start = len(frames)
        for seg in range(len(taps) + 1):
            a, b = bounds[seg], bounds[seg + 1]
            D = max(b - a, 0.0)
            ln = lines.get(f"s{seg}")
            if ln:
                k, d = ln
                need = d + T["pad"]
                v = min(T["max_speed"], max(1.0, D / need)) if D > 0 else 1.0
                audio.append([now() + 0.1, si, k])
                cues.append([now() + 0.1, d, si, k])
                if D > 0:
                    play(a, b, v)
                if D / v < need:                 # line outlasts the footage: hold the settled last frame
                    freeze(b, need - D / v)
            elif D > 0:                          # silent: show the result of the last tap at normal speed first,
                d0 = min(D, T["dwell"])          # then squeeze the rest (typing, loading) into what is left
                play(a, a + d0, 1.0)
                if D > d0:
                    play(a + d0, b, min(T["max_speed"], max(1.0, (D - d0) / max(T["quiet"] - d0, 0.5))))
            if seg < len(taps):
                ln = lines.get(f"h{seg}")
                d = ln[1] if ln else 0.0
                hl = max(T["hold_min"], T["hold_pre"] + d + T["pad"])
                if ln:
                    audio.append([now() + T["hold_pre"], si, ln[0]])
                    cues.append([now() + T["hold_pre"], d, si, ln[0]])
                for f in range(int(round(hl * FPS))):
                    frames.append([int(round(b * FPS)), si, seg, f / FPS, hl])
        steps.append({"id": st["id"], "start": start / FPS, "end": len(frames) / FPS})
    si = len(P["steps"]) - 1
    freeze(P["steps"][-1]["src"][1], T["end_tail"])
    steps[-1]["end"] = len(frames) / FPS
    return {"frames": frames, "steps": steps, "audio": audio, "cues": cues}


def hold_starts(plan):
    """{(step, tap): (first_output_frame, hold_len_seconds)}"""
    out = {}
    for i, (_, si, hi, _, hl) in enumerate(plan["frames"]):
        if hi >= 0 and (si, hi) not in out:
            out[(si, hi)] = (i, hl)
    return out
