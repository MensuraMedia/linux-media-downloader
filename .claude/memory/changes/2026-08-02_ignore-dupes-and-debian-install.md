---
date: 2026-08-02
type: feature
files_changed:
  - modules/download/dedupe.py (new)
  - modules/download/media.py
  - modules/routes/api.py
  - templates/index.html
  - install.sh (new)
  - README.md / DOCUMENTATION.md / ROADMAP.md / changelog.md
  - tests/test_app.py
---
## Change: Ignore Duplicates feature + one-command Debian installer

### Ignore Duplicates (implemented from concept)
- `modules/download/dedupe.py`: manifest of ORIGINAL titles + video ids
  (`data/download_manifest.json`, git-ignored). `record_download()` runs in the progress
  `finished` hook (before rename) for EVERY download, so the manifest always builds.
- Matching: exact video id → dup; else normalized token-set equality or ≥0.80 similarity
  (Sørensen–Dice + difflib fallback). Normalization drops FILLER_WORDS + STOPWORDS + years,
  order-independent. Fuzzy (non-exact) matches require ≥2 tokens each side (false-positive guard).
- `download_media` gained `ignore_dupes`; combined with skip_long into one yt-dlp
  `match_filter`; skips counted in `current_download['skipped_duplicates']`.
- Home: "Ignore Duplicates" checkbox in the playlist-only group (grayed until playlist).
- Verified live: same-id skip, `Beach_Original_music`≈`Original Beach Music` skip, distinct kept.

### One-command Debian install
- `install.sh` (repo root): `curl -fsSL …/install.sh | bash` — installs apt deps (python3,
  venv, ffmpeg, webkit2 GTK backend w/ 4.1→4.0 fallback), clones to
  `~/.local/share/linux-media-downloader`, creates venv + pip install, runs
  `packaging/install-menu.sh` for the program-menu entry. Re-runnable (updates); `--uninstall`.
- Added as the FIRST thing in the README ("⚡ Install … one command").

### Verification
- 71/71 pytest (added dedupe: concept examples, distinct-not-matched, by-id, fuzzy, persist).
  pyflakes/py_compile clean. install.sh + install-menu.sh pass `bash -n`; .desktop validates.
