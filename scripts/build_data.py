#!/usr/bin/env python3
"""Build scripts/data/kjv.json and scripts/data/hebrew.json from the vendored sources.

Sources (both in scripts/data/src/):
  kjv-proverbs-aruljohn.json  King James Version, public domain (github.com/aruljohn/Bible-kjv)
  oshb-Prov.xml               Open Scriptures Hebrew Bible, WLC text (public domain) with
                              Strong's lemmas (CC BY 4.0, github.com/openscriptures/morphhb)
Run once after changing a source: python3 scripts/build_data.py
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
SRC = DATA / "src"
NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}

kjv = {}
for ch in json.loads((SRC / "kjv-proverbs-aruljohn.json").read_text(encoding="utf-8"))["chapters"]:
    for v in ch["verses"]:
        kjv[f"{int(ch['chapter'])}:{int(v['verse'])}"] = v["text"].strip()
assert len(kjv) == 915, len(kjv)

hebrew = {}
root = ET.parse(SRC / "oshb-Prov.xml").getroot()
for verse in root.iter(f"{{{NS['o']}}}verse"):
    _, c, v = verse.get("osisID").split(".")
    words = []
    for w in verse.iter(f"{{{NS['o']}}}w"):
        lemmas = [f"H{m.group(1)}" for seg in w.get("lemma", "").split("/") if (m := re.match(r"\s*(\d+)", seg))]
        words.append({"text": w.text or "", "strongs": lemmas})
    hebrew[f"{int(c)}:{int(v)}"] = words
assert len(hebrew) == 915, len(hebrew)

(DATA / "kjv.json").write_text(json.dumps(kjv, ensure_ascii=False, indent=0), encoding="utf-8")
(DATA / "hebrew.json").write_text(json.dumps(hebrew, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("kjv verses:", len(kjv), "hebrew verses:", len(hebrew))
