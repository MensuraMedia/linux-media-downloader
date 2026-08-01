---
date: 2026-07-31
type: feature
files_changed:
  - modules/playlists.py (new)
  - modules/download/media.py
  - modules/routes/api.py
  - modules/routes/ui.py
  - templates/base.html
  - templates/index.html
  - templates/playlists.html (new)
  - tests/test_app.py
  - README.md / changelog.md
---
## Change: Skip-long filter, History rename, and Playlists manager

### Skip long files
- Home shows a "Skip long files (over 6 min)" checkbox when a playlist is detected.
- `/api/download` accepts `skip_long`; `download_media` installs a yt-dlp `match_filter`
  that skips any track with duration > 360s.

### Sidebar
- Renamed **Backups** → **History** (label; route stays `/backups`).
- Added **Playlists** tab (`/playlists`).

### Playlists manager (`modules/playlists.py` + `templates/playlists.html`)
- `list_playlists()` scans the download roots (default path + history output dirs) for
  folders containing more than one media file.
- Detail view: sortable table of Length / Filename / Size (durations via `ffprobe`).
- Rename a playlist folder on disk.
- Bulk operations: `delete_long` (>6 min), `clean`, `remove_special`, `replace_spaces`,
  `number_prefix`.
- **Security:** every destructive op is guarded by `_is_safe_path`, which requires the
  target to resolve inside a known download root — blocks path traversal (e.g. `/etc`).

### Verification
- 28/28 pytest passing (playlist listing excludes single-file folders; rename; path-traversal
  rejection; each rename operation; delete_long via monkeypatched duration; API + page render).
- pyflakes clean, py_compile clean, AppDir synced.

### Notes / follow-ups
- File durations use one `ffprobe` call per file when opening a playlist — slow for very
  large folders. Could be cached or made lazy later.
- `ffprobe` (ffmpeg) is required for the Length column and delete_long on existing files.
