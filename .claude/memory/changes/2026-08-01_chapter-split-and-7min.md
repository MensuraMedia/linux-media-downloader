---
date: 2026-08-01
type: feature
files_changed:
  - modules/download/chapters.py (new)
  - modules/download/media.py
  - modules/routes/api.py
  - modules/playlists.py
  - templates/index.html, playlists.html, file-manager.html
  - tests/test_app.py
  - docs/concept-chapter-split.md (implemented)
---
## Change: Chapter/Tracklist Split implemented + 7-minute "long" threshold

### Chapter split (Approach B)
- New `modules/download/chapters.py`:
  - `parse_description()` — tolerant timestamped-tracklist parser (≥2, monotonic), fills ends.
  - `chapter_segments()` — prefers embedded `info_dict['chapters']`, falls back to description.
  - `segment_filename()` — track title if present, else **NN_<video-title-summary>** (the
    unlabeled fallback the user specified).
  - `split_file()` — `ffmpeg -ss/-t -c copy` per segment (optional re-encode for mp3).
- `DownloadProgress` now stores the richest `info_dict` (`self.info`); `download_media`
  gained `split_chapters` and, for a single video, splits the finished file into a
  `<title>_playlist` folder (auto-listed by Playlists + File Manager) and removes the source.
- `/api/download` accepts `split_chapters`. Home: **"Split Multi-Chapter video"** checkbox,
  placed under "Skip long files" (per user), always enabled (applies to single videos).
- Live-verified on real audio: a 4-entry tracklist (one unlabeled) produced
  `Never_Gonna_Give_You_Up.mp3`, `Together_Forever.mp3`, `03_80s_Hits_Compilation.mp3`
  (unlabeled → summary+seq), `Whenever_You_Need_Somebody.mp3`. Graceful "no tracklist" msg
  when none found.

### 7-minute threshold
Changed "long file" from 6→7 min (420s) everywhere: skip-long `match_filter` in media.py,
`LONG_SECONDS` in playlists.py (delete_long), all labels/confirm dialogs, README + DOCS.

### Verification
- 63/63 pytest (added parse/segment/filename + real ffmpeg split integration). pyflakes/compile clean.
