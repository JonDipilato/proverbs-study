# Daily Proverbs

One passage of Proverbs a day: the King James text, the Hebrew opened up word by word, what it actually means, and three things to do before noon.

**Read it:** https://jondipilato.github.io/proverbs-study/

- **Today** — the newest study, on the home page.
- **Chapters** — 31 chapters, one per day of the month. Every study is filed under its chapter, so each month adds a new passage to each one.
- **Words** — every Hebrew word studied so far, by Strong's number, linked to each verse it appears in.
- **RSS** — `feed.xml`, for anyone who wants it in a reader.

## How it runs

A Claude Code cloud routine fires every morning at 10:00 UTC (6 AM Eastern in summer, 5 AM in winter). It reads `ROUTINE.md` as its instructions:

1. Chapter = day of the month. `scripts/study.py coverage CH` lists the verses and focus words already used.
2. It picks a new verse cluster, pulls the KJV wording from two live sources, and verifies each Hebrew word and Strong's number against a concordance.
3. It writes one file, `_posts/YYYY-MM-DD-proverbs-CH-V.md`.
4. `scripts/study.py check --new <file>` must pass (schema, exactly 3 actions, real Hebrew letters, Strong's format, no repeated verses or focus words).
5. It commits that one file and pushes to `main`. GitHub Pages rebuilds the site.

Studies from Aug 31 – Oct 12, 2026 were imported word for word from the earlier Google Drive version (each file's `source:` line names the original doc).

## Study file shape

Front matter holds the structured parts (reference, KJV verses, Hebrew word rows, the three actions, the prayer). The body is the "what this actually means" prose. The layout in `_includes/study.html` renders it. See any file in `_posts/` for the exact shape.

## Local check

```sh
pip install pyyaml
python3 scripts/study.py check
python3 scripts/study.py coverage 12
```
