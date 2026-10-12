#!/usr/bin/env python3
"""Daily Proverbs study tool.

  python3 scripts/study.py coverage CH       what chapter CH already covers, plus every focus word used
  python3 scripts/study.py check             validate every study in _posts/
  python3 scripts/study.py check --new FILE  also block FILE if it repeats a verse or focus word

Exits non-zero with a plain list of problems. Nothing is auto-fixed.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-proverbs-(\d{1,2})-(\d{1,3})(?:-(\d{1,3}))?\.md$")
HEBREW = re.compile(r"[֐-׿]")
REQUIRED = ["title", "reference", "chapter", "verses", "kjv", "words", "actions", "prayer"]
# Some imported Drive studies have no hook or word note; every NEW study must have both.
REQUIRED_NEW = ["hook", "word_note"]


def load(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("file must start with a --- front matter line")
    _, fm, body = text.split("---\n", 2)
    data = yaml.safe_load(fm)
    if not isinstance(data, dict):
        raise ValueError("front matter is not a YAML mapping")
    return data, body.strip()


def verse_set(verses):
    a, _, b = str(verses).partition("-")
    return set(range(int(a), int(b or a) + 1))


def validate(path):
    errors = []
    m = NAME.match(path.name)
    if not m:
        return None, [f"{path.name}: name must be YYYY-MM-DD-proverbs-CH-V.md or YYYY-MM-DD-proverbs-CH-V-V.md"]
    try:
        d, body = load(path)
    except Exception as e:  # report every parse failure by file
        return None, [f"{path.name}: {e}"]

    for k in REQUIRED:
        if d.get(k) in (None, "", []):
            errors.append(f"missing or empty '{k}'")
    if errors:
        return None, [f"{path.name}: {e}" for e in errors]

    ch, v1, v2 = int(m.group(2)), m.group(3), m.group(4)
    file_verses = f"{v1}-{v2}" if v2 else v1
    if not 1 <= ch <= 31:
        errors.append(f"chapter {ch} is outside 1-31")
    if d["chapter"] != ch:
        errors.append(f"chapter {d['chapter']!r} does not match file name chapter {ch}")
    if str(d["verses"]) != file_verses:
        errors.append(f"verses {d['verses']!r} do not match file name verses {file_verses!r}")
    if not re.fullmatch(r"\d{1,3}(-\d{1,3})?", str(d["verses"])):
        errors.append(f"verses {d['verses']!r} must look like 25 or 19-20")
    if d["reference"] != f"Proverbs {ch}:{d['verses']}":
        errors.append(f"reference {d['reference']!r} must be 'Proverbs {ch}:{d['verses']}'")

    allowed = verse_set(d["verses"]) if not errors else set()
    for i, v in enumerate(d["kjv"], 1):
        if not isinstance(v, dict) or not v.get("ref") or not v.get("text"):
            errors.append(f"kjv item {i} needs ref and text")
            continue
        rm = re.fullmatch(r"(\d{1,2}):(\d{1,3})", str(v["ref"]))
        if not rm or int(rm.group(1)) != ch or (allowed and int(rm.group(2)) not in allowed):
            errors.append(f"kjv item {i} ref {v['ref']!r} is not a verse inside {d['reference']}")

    words = d["words"]
    if not 1 <= len(words) <= 8:
        errors.append(f"words has {len(words)} entries; keep it 1-8")
    focus = 0
    for i, w in enumerate(words, 1):
        for k in ("hebrew", "strongs", "translit", "meaning"):
            if not w.get(k):
                errors.append(f"word {i} missing '{k}'")
        if w.get("hebrew") and not HEBREW.search(w["hebrew"]):
            errors.append(f"word {i} hebrew {w['hebrew']!r} has no Hebrew letters")
        if w.get("strongs") and not re.fullmatch(r"H\d{1,4}", str(w["strongs"])):
            errors.append(f"word {i} strongs {w['strongs']!r} must look like H1674")
        if w.get("focus") is True:
            focus += 1
        elif "focus" in w and w["focus"] is not True:
            errors.append(f"word {i} focus must be true or left out")
    if not 1 <= focus <= 2:
        errors.append(f"{focus} focus words; mark 1 or 2 with focus: true")

    if len(d["actions"]) != 3 or not all(isinstance(a, str) and a.strip() for a in d["actions"]):
        errors.append(f"actions must be exactly 3 non-empty lines (found {len(d['actions'])})")
    if not body:
        errors.append("body ('what this actually means') is empty")

    info = {
        "date": m.group(1),
        "chapter": ch,
        "verses": verse_set(d["verses"]) if re.fullmatch(r"\d{1,3}(-\d{1,3})?", str(d["verses"])) else set(),
        "reference": d["reference"],
        "focus": {w["strongs"]: w.get("translit", "") for w in words if w.get("focus") is True and w.get("strongs")},
    }
    return info, [f"{path.name}: {e}" for e in errors]


def all_posts():
    return sorted(p for p in POSTS.glob("*.md"))


def cmd_check(new):
    infos, problems = {}, []
    for p in all_posts():
        info, errs = validate(p)
        problems += errs
        if info:
            infos[p.name] = info

    dates = {}
    for name, i in infos.items():
        dates.setdefault(i["date"], []).append(name)
    for day, names in dates.items():
        if len(names) > 1:
            problems.append(f"{day} has more than one study: {', '.join(names)}")

    if new:
        np = Path(new).resolve()
        if np.name not in infos:
            problems.append(f"--new file {new} is missing or failed validation")
        else:
            me = infos[np.name]
            d, _ = load(np)
            for k in REQUIRED_NEW:
                if not d.get(k):
                    problems.append(f"{np.name}: missing or empty '{k}' (required for every new study)")
            for name, i in infos.items():
                if name == np.name:
                    continue
                if i["chapter"] == me["chapter"] and i["verses"] & me["verses"]:
                    problems.append(f"{np.name}: verses overlap {i['reference']} already covered in {name}")
                for s in set(i["focus"]) & set(me["focus"]):
                    problems.append(f"{np.name}: focus word {s} ({me['focus'][s]}) was already the focus in {name}")

    if problems:
        print("CHECK FAILED")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print(f"CHECK PASSED — {len(infos)} studies")


def cmd_coverage(ch):
    covered, focus = [], {}
    for p in all_posts():
        info, errs = validate(p)
        if errs:
            print("CHECK FAILED — fix these before writing a new study:")
            for e in errs:
                print(" -", e)
            sys.exit(1)
        if info["chapter"] == ch:
            covered.append(f"{info['reference']}  ({info['date']})")
        for s, t in info["focus"].items():
            focus.setdefault(s, (t, info["reference"]))
    print(f"Chapter {ch} — verse ranges already covered:")
    print("\n".join(f"  {c}" for c in covered) or "  (none yet)")
    print("\nFocus words already used (never make these the focus again):")
    for s in sorted(focus, key=lambda x: int(x[1:])):
        print(f"  {s}  {focus[s][0]}  — {focus[s][1]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["coverage"] and len(args) == 2 and args[1].isdigit():
        cmd_coverage(int(args[1]))
    elif args[:1] == ["check"] and (len(args) == 1 or (len(args) == 3 and args[1] == "--new")):
        cmd_check(args[2] if len(args) == 3 else None)
    else:
        print(__doc__)
        sys.exit(2)
