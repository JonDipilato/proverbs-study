# Daily Proverbs

One passage of Proverbs a day: the King James text, the Hebrew opened up word by word, what it actually means, and three things to do before noon.

**Read it:** https://jondipilato.github.io/proverbs-study/

- **Today** — the newest study, on the home page.
- **Chapters** — 31 chapters, one per day of the month. Every study is filed under its chapter, so each month adds a new passage to each one.
- **Words** — every Hebrew word studied so far, by Strong's number, linked to each verse it appears in.
- **RSS** — `feed.xml`, for anyone who wants it in a reader.
- **Listen** — every study is narrated. Each page has a play button and a Download MP3 link, and `podcast.xml` is a podcast feed (subscribe page: `/listen/`).

## How it runs

A Claude Code cloud routine fires every morning at 10:00 UTC (6 AM Eastern in summer, 5 AM in winter). It reads `ROUTINE.md` as its instructions:

1. Chapter = day of the month. `scripts/study.py coverage CH` lists the verses already covered, the verses still free, and the focus words already used.
2. It picks a free verse cluster and prints the exact KJV text and Hebrew words with `scripts/study.py verse CH:V`. Word meanings are looked up against a concordance.
3. It writes one file, `_posts/YYYY-MM-DD-proverbs-CH-V.md`.
4. `scripts/study.py check --new FILE` must pass: dated today (Eastern), KJV wording exact, every Hebrew row a real word of the passage with its real Strong's number, exactly 3 actions, no repeated verse or focus word.
5. It commits that one file, pushes to `main`, and confirms the page is live.

Studies from Aug 31 – Oct 12, 2026 were imported word for word from the earlier Google Drive version (each file's `source:` line names the original doc).

## Audio

`.github/workflows/audio.yml` runs whenever a study lands on `main` (and twice each morning as a backstop). For every study with no entry in `_data/audio.yml` it:

1. Builds the narration with `scripts/audio.py`: date, title and hook, the KJV verses, each Hebrew word and its meaning, the word note, the body, the three actions, the prayer, and the keep verse.
2. Reads it with the Piper `en-us-ryan-high` voice and saves a 64 kbps mono MP3 with the cover art embedded.
3. Uploads the MP3 to the `audio` release (so the repo stays small) and records its URL, size and length in `_data/audio.yml`.
4. Commits that file and asks Pages to rebuild. The player and the podcast feed read from it.

Hebrew words are spoken from the word row's `say` spelling, then `scripts/data/say.json` (every word from the imported studies), then the transliteration as a fallback. To preview a narration: `python3 scripts/audio.py script _posts/FILE.md`. To redo an episode, delete its entry from `_data/audio.yml` and run the workflow.

Cover art: `assets/img/podcast-cover.jpg` (3000 px, for podcast directories) and `podcast-cover-600.jpg` (embedded in each MP3).

## Text sources

`scripts/data/src/` holds the vendored sources; `scripts/build_data.py` turns them into `scripts/data/kjv.json` and `scripts/data/hebrew.json`.

- King James Version text — public domain, via github.com/aruljohn/Bible-kjv.
- Hebrew — Westminster Leningrad Codex (public domain) with Strong's lemmas from the Open Scriptures Hebrew Bible, github.com/openscriptures/morphhb (CC BY 4.0).

`python3 scripts/study.py audit` runs the strict text checks over every study. Imported studies often show a word's dictionary form rather than its form in the verse; the audit lists those, and only new studies are held to the verse form.

## Study file shape

Front matter holds the structured parts (reference, KJV verses, Hebrew word rows, the three actions, the prayer). The body is the "what this actually means" prose. The layout in `_includes/study.html` renders it. See any file in `_posts/` for the exact shape.

## Local check

```sh
pip install pyyaml
python3 scripts/study.py check
python3 scripts/study.py coverage 12
python3 scripts/study.py verse 12:25
python3 scripts/study.py audit
```
