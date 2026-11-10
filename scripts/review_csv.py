"""Narration lines as a spreadsheet for a translator or native-speaker reviewer, and back again.

usage: python3 review_csv.py PROJECT.json export LANG [FILE.csv]
       python3 review_csv.py PROJECT.json import LANG FILE.csv
Columns: step, beat, at, label, <primary language>, <LANG>. Rows with beat "title" hold the step title.
The reviewer edits only the last column. Import writes that column back into project.json; nothing else
changes, so the beat structure stays identical across languages.
"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def main():
    path, cmd, lang = sys.argv[1:4]
    P = common.load(path)
    pri = P["primary"]
    f = sys.argv[4] if len(sys.argv) > 4 else os.path.join(P["_root"], f"lines_{lang}.csv")
    if cmd == "export":
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["step", "beat", "at", "label", pri, lang])
            for st in P["steps"]:
                t = st.get("title", "")
                t = t if isinstance(t, dict) else {pri: t}
                w.writerow([st["id"], "title", "", "", t.get(pri, ""), t.get(lang, "")])
                for k, b in enumerate(st.get("beats", [])):
                    at = b["at"]
                    label = st["taps"][int(at[1:])]["label"] if at[0] == "h" else ""
                    w.writerow([st["id"], k, at, label, b.get(pri, ""), b.get(lang, "")])
        print("wrote", f)
    elif cmd == "import":
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))

        def apply(raw):
            steps = {s["id"]: s for s in raw["steps"]}
            n = 0
            for r in rows:
                st, val = steps.get(r["step"]), (r.get(lang) or "").strip()
                if not st or not val:
                    continue
                if r["beat"] == "title":
                    if not isinstance(st.get("title"), dict):
                        st["title"] = {pri: st.get("title", st["id"])}
                    st["title"][lang] = val
                else:
                    st["beats"][int(r["beat"])][lang] = val
                n += 1
            print(f"imported {n} '{lang}' lines into {path}")
        common.edit(path, apply)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
