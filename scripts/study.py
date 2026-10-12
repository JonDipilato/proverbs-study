#!/usr/bin/env python3
"""Daily Proverbs study tool.

  python3 scripts/study.py coverage CH       verses of chapter CH already covered, verses still free,
                                             and every focus word already used
  python3 scripts/study.py verse CH:V[-V]    the exact KJV text and the Hebrew words (with Strong's)
                                             of a passage — copy from this, never from memory
  python3 scripts/study.py check             validate every study in _posts/
  python3 scripts/study.py check --new FILE  also hold FILE to the strict rules for a new study:
                                             dated today (Eastern), KJV text exact, every Hebrew row
                                             a real word of the passage with its real Strong's number,
                                             no repeated verse or focus word
  python3 scripts/study.py audit             run the strict text checks over every study (report only)

Exits non-zero with a plain list of problems. Nothing is auto-fixed.
Text sources: scripts/data/ (KJV, public domain; Open Scriptures Hebrew Bible / WLC). See build_data.py.
"""
import datetime
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
DATA = Path(__file__).resolve().parent / "data"
KJV = json.loads((DATA / "kjv.json").read_text(encoding="utf-8"))
HEB = json.loads((DATA / "hebrew.json").read_text(encoding="utf-8"))
VERSE_COUNT = {c: max(int(k.split(":")[1]) for k in KJV if int(k.split(":")[0]) == c) for c in range(1, 32)}

NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-proverbs-(\d{1,2})-(\d{1,3})(?:-(\d{1,3}))?\.md$")
HEBREW_LETTER = re.compile(r"[א-ת]")
REQUIRED = ["title", "reference", "chapter", "verses", "kjv", "words", "actions", "prayer"]
# Some imported Drive studies have no hook or word note; every NEW study must have both.
REQUIRED_NEW = ["hook", "word_note"]
ALLOWED_KEYS = set(REQUIRED + REQUIRED_NEW + ["keep", "source"])


def today_eastern():
    # STUDY_TODAY exists only so a supervised test run can stand in for a given day.
    return os.environ.get("STUDY_TODAY") or datetime.datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def bare(s):
    """Hebrew without cantillation, meteg, punctuation, morpheme slashes or direction marks."""
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[֑-ֽ֯׀׃׆‎‏/]", "", s)
    return unicodedata.normalize("NFC", s).strip()


def quotes(s):
    """Curly and straight apostrophes count as the same character."""
    return str(s).replace("\u2019", "'").replace("\u2018", "'")


def load(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("file must start with a --- front matter line")
    _, fm, body = text.split("---\n", 2)
    data = yaml.safe_load(fm)
    if not isinstance(data, dict):
        raise ValueError("front matter is not a YAML mapping")
    return data, body.strip()


def verse_range(verses):
    m = re.fullmatch(r"(\d{1,3})(?:-(\d{1,3}))?", str(verses))
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return list(range(a, b + 1)) if a <= b else None


def all_strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from all_strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from all_strings(v)


def validate(path):
    """Rules every study (imported or new) must meet."""
    errors = []
    m = NAME.match(path.name)
    if not m:
        return None, [f"{path.name}: name must be YYYY-MM-DD-proverbs-CH-V.md or YYYY-MM-DD-proverbs-CH-V-V.md"]
    try:
        datetime.date.fromisoformat(m.group(1))
        d, body = load(path)
    except Exception as e:  # report every parse failure by file
        return None, [f"{path.name}: {e}"]

    for k in REQUIRED:
        if d.get(k) in (None, "", []):
            errors.append(f"missing or empty '{k}'")
    if errors:
        return None, [f"{path.name}: {e}" for e in errors]
    for k in sorted(set(d) - ALLOWED_KEYS):
        errors.append(f"unexpected front matter key '{k}' (it could move or hide the page)")
    for s in list(all_strings(d)) + [body]:
        if "{{" in s or "{%" in s:
            errors.append("contains '{{' or '{%', which breaks the site build")
            break

    ch, v1, v2 = int(m.group(2)), m.group(3), m.group(4)
    file_verses = f"{v1}-{v2}" if v2 else v1
    vs = verse_range(d["verses"])
    if not 1 <= ch <= 31:
        errors.append(f"chapter {ch} is outside 1-31")
    if d["chapter"] != ch:
        errors.append(f"chapter {d['chapter']!r} does not match file name chapter {ch}")
    if str(d["verses"]) != file_verses:
        errors.append(f"verses {d['verses']!r} do not match file name verses {file_verses!r}")
    if not vs:
        errors.append(f"verses {d['verses']!r} must look like 25 or 19-20 (low to high)")
    elif 1 <= ch <= 31 and vs[-1] > VERSE_COUNT[ch]:
        errors.append(f"Proverbs {ch} has only {VERSE_COUNT[ch]} verses")
    if d["reference"] != f"Proverbs {ch}:{d['verses']}":
        errors.append(f"reference {d['reference']!r} must be 'Proverbs {ch}:{d['verses']}'")

    for i, v in enumerate(d["kjv"], 1):
        if not isinstance(v, dict) or not v.get("ref") or not v.get("text"):
            errors.append(f"kjv item {i} needs ref and text")
            continue
        rm = re.fullmatch(r"(\d{1,2}):(\d{1,3})", str(v["ref"]))
        if not rm or int(rm.group(1)) != ch or (vs and int(rm.group(2)) not in vs):
            errors.append(f"kjv item {i} ref {v['ref']!r} is not a verse inside {d['reference']}")

    words = d["words"]
    if not 1 <= len(words) <= 8:
        errors.append(f"words has {len(words)} entries; keep it 1-8")
    focus = 0
    for i, w in enumerate(words, 1):
        for k in ("hebrew", "strongs", "translit", "meaning"):
            if not w.get(k):
                errors.append(f"word {i} missing '{k}'")
        if w.get("hebrew") and not HEBREW_LETTER.search(w["hebrew"]):
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
        "verses": set(vs or []),
        "reference": d["reference"],
        "focus": {w["strongs"]: w.get("translit", "") for w in words if w.get("focus") is True and w.get("strongs")},
    }
    return info, [f"{path.name}: {e}" for e in errors]


def strict_text(path):
    """KJV wording and Hebrew rows checked against the vendored texts."""
    d, _ = load(path)
    ch, vs = d["chapter"], verse_range(d["verses"]) or []
    errors = []
    refs = [str(v.get("ref")) for v in d["kjv"]]
    want = [f"{ch}:{v}" for v in vs]
    if refs != want:
        errors.append(f"kjv must list each verse once, in order: {want} (found {refs})")
    for v in d["kjv"]:
        ref = str(v.get("ref"))
        if ref in KJV and quotes(v.get("text")) != quotes(KJV[ref]):
            errors.append(f"kjv {ref} wording differs from the KJV. KJV reads: {KJV[ref]!r}")
    passage = [w for v in vs for w in HEB.get(f"{ch}:{v}", [])]
    for i, w in enumerate(d["words"], 1):
        he = str(w.get("hebrew", ""))
        if re.search(r"[\s/‎‏]", he):
            errors.append(f"word {i} hebrew {he!r} must be ONE word: no spaces, slashes, or direction marks")
            continue
        target = bare(he)
        hits = [pw for pw in passage if target in {bare(pw["text"])} | {bare(p) for p in pw["text"].split("/")}]
        if not hits:
            forms = ", ".join(f"{bare(pw['text'])} ({'/'.join(pw['strongs'])})" for pw in passage)
            errors.append(f"word {i} hebrew {he!r} is not a word in {d['reference']}. The passage's words: {forms}")
        elif not any(w.get("strongs") in pw["strongs"] for pw in hits):
            errors.append(f"word {i} {he!r} is Strong's {'/'.join(hits[0]['strongs'])} in this verse, not {w.get('strongs')}")
    return [f"{path.name}: {e}" for e in errors]


def all_posts():
    return sorted(POSTS.glob("*.md"))


def gather():
    infos, problems = {}, []
    for p in all_posts():
        info, errs = validate(p)
        problems += errs
        if info:
            infos[p.name] = info
    dates = {}
    for name, i in infos.items():
        dates.setdefault(i["date"], []).append(name)
    for day, names in sorted(dates.items()):
        if len(names) > 1:
            problems.append(f"{day} has more than one study: {', '.join(names)}")
    return infos, problems


def cmd_check(new):
    infos, problems = gather()
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
            if me["date"] != today_eastern():
                problems.append(f"{np.name}: dated {me['date']} but today in Eastern time is {today_eastern()}")
            if int(me["date"][8:]) != me["chapter"]:
                problems.append(f"{np.name}: chapter {me['chapter']} does not match day of month {int(me['date'][8:])}")
            if not 1 <= len(me["verses"]) <= 4:
                problems.append(f"{np.name}: pick 1-4 verses (found {len(me['verses'])})")
            problems += strict_text(np)
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


def cmd_audit():
    infos, problems = gather()
    for name in sorted(infos):
        problems += strict_text(POSTS / name)
    print("\n".join(f" - {p}" for p in problems) or "AUDIT CLEAN")
    sys.exit(1 if problems else 0)


def cmd_coverage(ch):
    infos, problems = gather()
    if problems:
        print("CHECK FAILED — fix these before writing a new study:")
        for e in problems:
            print(" -", e)
        sys.exit(1)
    covered, used, focus = [], set(), {}
    for i in sorted(infos.values(), key=lambda i: i["date"]):
        if i["chapter"] == ch:
            covered.append(f"{i['reference']}  ({i['date']})")
            used |= i["verses"]
        for s, t in i["focus"].items():
            focus.setdefault(s, (t, i["reference"]))
    free = [v for v in range(1, VERSE_COUNT[ch] + 1) if v not in used]
    print(f"Chapter {ch} ({VERSE_COUNT[ch]} verses) — verse ranges already covered:")
    print("\n".join(f"  {c}" for c in covered) or "  (none yet)")
    print(f"\nVerses still free: {', '.join(map(str, free)) if free else 'NONE — chapter is fully covered; STOP and report.'}")
    print("\nFocus words already used (never make these the focus again):")
    for s in sorted(focus, key=lambda x: int(x[1:])):
        print(f"  {s}  {focus[s][0]}  — {focus[s][1]}")
    if not free:
        sys.exit(3)


def cmd_verse(ref):
    m = re.fullmatch(r"(\d{1,2}):(\d{1,3})(?:-(\d{1,3}))?", ref)
    if not m:
        print("use CH:V or CH:V-V, like 13:4 or 10:19-20")
        sys.exit(2)
    ch, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(2))
    for v in range(a, b + 1):
        key = f"{ch}:{v}"
        if key not in KJV:
            print(f"Proverbs {key} does not exist")
            sys.exit(1)
        print(f"Proverbs {key} (KJV): {KJV[key]}")
        print("  Hebrew words (copy the 'hebrew' value exactly; Strong's from the same line):")
        for w in HEB[key]:
            parts = [p for p in w["text"].split("/") if p]
            print(f"    hebrew: {bare(w['text'])}    strongs: {', '.join(w['strongs']) or '-'}"
                  + (f"    parts: {' + '.join(bare(p) for p in parts)}" if len(parts) > 1 else ""))
        print()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["coverage"] and len(args) == 2 and args[1].isdigit() and 1 <= int(args[1]) <= 31:
        cmd_coverage(int(args[1]))
    elif args[:1] == ["verse"] and len(args) == 2:
        cmd_verse(args[1])
    elif args[:1] == ["check"] and (len(args) == 1 or (len(args) == 3 and args[1] == "--new")):
        cmd_check(args[2] if len(args) == 3 else None)
    elif args == ["audit"]:
        cmd_audit()
    else:
        print(__doc__)
        sys.exit(2)
