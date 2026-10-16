#!/usr/bin/env python3
"""Turn a Daily Proverbs study into a narrated MP3.

  python3 scripts/audio.py script  _posts/FILE.md          print the narration text
  python3 scripts/audio.py build   _posts/FILE.md OUT.mp3  narrate it (needs PIPER_BIN, PIPER_MODEL, ffmpeg)
  python3 scripts/audio.py pending                         posts with no entry in _data/audio.yml, newest first
  python3 scripts/audio.py record  _posts/FILE.md OUT.mp3 URL   add the episode to _data/audio.yml

Hebrew words are spoken from each word row's `say` spelling, then scripts/data/say.json,
then a plain-letter fallback. Spellings are lowercase on purpose: the voice spells out
words written in capitals letter by letter.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
DATA_FILE = ROOT / "_data" / "audio.yml"
SAY = json.loads((Path(__file__).resolve().parent / "data" / "say.json").read_text(encoding="utf-8"))
COVER = ROOT / "assets" / "img" / "podcast-cover-600.jpg"

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
COUNT_ORD = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth"]


def words(n):
    n = int(n)
    if n < 20:
        return ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return TENS[t] + ("-" + ONES[o] if o else "")
    h, r = divmod(n, 100)
    return ONES[h] + " hundred" + (" " + words(r) if r else "")


def ordinal(n):
    w = words(n)
    head, _, last = w.rpartition("-")
    if last in ORD:
        last = ORD[last]
    elif last.endswith("y"):
        last = last[:-1] + "ieth"
    else:
        last += "th"
    return (head + "-" if head else "") + last


def year_words(y):
    return words(y // 100) + " " + words(y % 100)


def verse_span(v1, v2=None):
    """'1', '3' -> 'one through three'; '1', '2' -> 'one and two'."""
    if not v2:
        return words(v1)
    joiner = "and" if int(v2) - int(v1) == 1 else "through"
    return f"{words(v1)} {joiner} {words(v2)}"


def spoken_ref(ref):
    """'Proverbs 15:1-2' or '15:1' -> 'Proverbs fifteen, one and two'."""
    m = re.search(r"(\d+):(\d+)(?:-(\d+))?", str(ref))
    return f"Proverbs {words(m.group(1))}, {verse_span(m.group(2), m.group(3))}"


def norm(s):
    return re.sub(r"[‘’ʼ`]", "'", s).strip().lower()


def auto_say(translit):
    t = re.sub(r"\(.*?\)", "", translit).split("/")[0]
    return re.sub(r"['‘’ʼ]", "", t).strip().lower()


class Speaker:
    """Knows how to say every Hebrew word in one study."""

    def __init__(self, rows):
        self.map = {norm(k): v for k, v in SAY.items()}
        for k, v in SAY.items():  # "ganab / ganavti" also answers to "ganab"
            for part in re.split(r"\s*/\s*|\s*\(.*?\)\s*", k):
                self.map.setdefault(norm(part), v.split(",")[0])
        for r in rows:
            spoken = (r.get("say") or self.map.get(norm(r["translit"])) or auto_say(r["translit"])).lower()
            r["_say"] = spoken
            self.map[norm(r["translit"])] = spoken

    def italic(self, inner):
        key = norm(inner)
        if key in self.map:
            return self.map[key]
        toks = key.split()
        if toks and all(t in self.map for t in toks):
            return " ".join(self.map[t] for t in toks)
        return inner  # ordinary English emphasis


def clean(text, speaker):
    s = str(text)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)  # links
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", lambda m: speaker.italic(m.group(1)), s)
    s = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", lambda m: speaker.italic(m.group(1)), s)
    s = re.sub(r"Proverbs\s+(\d+:\d+(?:-\d+)?)", lambda m: spoken_ref(m.group(1)), s)
    s = re.sub(r"\b(\d+):(\d+)(?:-(\d+))?\b", lambda m: spoken_ref(m.group(0)).replace("Proverbs ", ""), s)
    s = re.sub(r"\bvv?\.\s*(?=\d)", "verse ", s)  # (v.19)
    s = re.sub(r"\b(\d+)[-–](\d+)\b", lambda m: verse_span(m.group(1), m.group(2)), s)  # verses 15-16
    s = re.sub(r"\s*[—–]\s*|\s+-\s+", ". ", s)  # dashes become a beat
    s = re.sub(r"[“”\"]", "", s)
    s = s.replace("&", " and ")
    s = re.sub(r"\b[A-Z]{2,}\b", lambda m: m.group(0).capitalize(), s)  # LORD -> Lord; caps get spelled out
    s = re.sub(r"\.\s*\.", ".", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"([.!?:]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), s)
    s = s[:1].upper() + s[1:]
    if s and s[-1] not in ".!?":
        s += "."
    return s


def load(path):
    raw = Path(path).read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    return yaml.safe_load(fm), body.strip()


def post_date(path):
    return datetime.date.fromisoformat(Path(path).name[:10])


def narration(path):
    """The study as a list of spoken sections, in reading order."""
    d, body = load(path)
    rows = [dict(w) for w in d["words"]]
    sp = Speaker(rows)
    c = lambda t: clean(t, sp)
    day = post_date(path)
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", str(d["verses"]))
    many = bool(m.group(2))
    kjv = d["kjv"]

    out = [
        f"Daily Proverbs. {day:%A}, {day:%B} {ordinal(day.day)}, {year_words(day.year)}. "
        f"Proverbs chapter {words(d['chapter'])}, {'verses' if many else 'verse'} {verse_span(m.group(1), m.group(2))}."
    ]
    out.append(c(d["title"]) + (" " + c(d["hook"]) if d.get("hook") else ""))

    if len(kjv) > 1:
        verses = " ".join(f"Verse {words(str(v['ref']).split(':')[1])}. {c(v['text'])}" for v in kjv)
        out.append(f"Here are the verses. {verses} {spoken_ref(d['reference'])}.")
    else:
        out.append(f"Here is the verse. {c(kjv[0]['text'])} {spoken_ref(d['reference'])}.")

    n = len(rows)
    lines = [f"Part one. The Hebrew, opened up. {words(n).capitalize()} {'word carries' if n == 1 else 'words carry'} {'these verses' if many else 'this verse'}."]
    for i, r in enumerate(rows):
        lead = COUNT_ORD[i]
        if n > 1 and i == n - 1:
            lead = "And " + lead.lower()
        lines.append(f"{lead}, {r['_say']}. {c(r['meaning'])}")
    out.append(" ".join(lines))
    if d.get("word_note"):
        out.append("Put them together. " + c(d["word_note"]))

    out.append("Part two. What this actually means. " + c(body))
    acts = " ".join(f"Number {words(i)}. {c(a)}" for i, a in enumerate(d["actions"], 1))
    out.append("Part three. Obey it today. " + acts)

    prayer = c(d["prayer"])
    if not re.search(r"\bamen\W*$", prayer, re.I):
        prayer += " Amen."
    out.append("Let's pray. " + prayer)

    keep = d.get("keep") or kjv[0]["text"]
    keep_ref = d["reference"] if d.get("keep") else kjv[0]["ref"]
    out.append(f"Keep this in your chest. {c(keep)} {spoken_ref(keep_ref)}.")
    return d, out


def build(path, mp3):
    piper, model = os.environ.get("PIPER_BIN"), os.environ.get("PIPER_MODEL")
    if not piper or not model:
        sys.exit("PIPER_BIN and PIPER_MODEL must point at the piper binary and voice model")
    d, sections = narration(path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rate = json.loads(Path(model + ".json").read_text())["audio"]["sample_rate"]
        gap = tmp / "gap.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"anullsrc=r={rate}:cl=mono",
                        "-t", "1.3", "-c:a", "pcm_s16le", str(gap)], check=True)
        listing = []
        for i, text in enumerate(sections):
            wav = tmp / f"s{i:02d}.wav"
            subprocess.run([piper, "-m", model, "--length_scale", "1.08", "--sentence_silence", "0.45", "-f", str(wav)],
                           input=text.encode(), check=True, stderr=subprocess.DEVNULL)
            if wav.stat().st_size < 10000:
                sys.exit(f"section {i} came out empty: {text[:60]}")
            listing += [f"file '{wav}'", f"file '{gap}'"]
        (tmp / "list.txt").write_text("\n".join(listing) + "\n")
        title = f"{d['reference']} - {d['title']}"
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt")]
        if COVER.exists():
            cmd += ["-i", str(COVER), "-map", "0:a", "-map", "1:v", "-c:v", "copy", "-disposition:v", "attached_pic",
                    "-metadata:s:v", "title=Cover", "-id3v2_version", "3"]
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "64k",
                "-metadata", f"title={title}", "-metadata", "artist=Jon DiPilato", "-metadata", "album=Daily Proverbs",
                "-metadata", f"date={post_date(path).year}", "-metadata", "genre=Christianity", str(mp3)]
        subprocess.run(cmd, check=True)
    print(f"built {mp3} ({duration(mp3)}s)")


def duration(mp3):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                         capture_output=True, text=True, check=True).stdout
    return round(float(out))


def read_data():
    if DATA_FILE.exists():
        return yaml.safe_load(DATA_FILE.read_text(encoding="utf-8")) or {}
    return {}


def write_data(data):
    DATA_FILE.parent.mkdir(exist_ok=True)
    lines = ["# Written by scripts/audio.py from .github/workflows/audio.yml. One entry per narrated study."]
    for key in sorted(data, reverse=True):
        e = data[key]
        lines.append(f'"{key}":')
        lines += [f"  url: \"{e['url']}\"", f"  bytes: {e['bytes']}", f"  seconds: {e['seconds']}"]
    DATA_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "script":
        print("\n\n".join(narration(args[0])[1]))
    elif cmd == "build":
        build(args[0], args[1])
    elif cmd == "pending":
        have = read_data()
        today = datetime.datetime.now(ZoneInfo("America/New_York")).date()
        for p in sorted(POSTS.glob("*.md"), reverse=True):
            if p.stem not in have and post_date(p) <= today:
                print(p.relative_to(ROOT))
    elif cmd == "record":
        path, mp3, url = args
        data = read_data()
        data[Path(path).stem] = {"url": url, "bytes": Path(mp3).stat().st_size, "seconds": duration(mp3)}
        write_data(data)
        print(f"recorded {Path(path).stem}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
