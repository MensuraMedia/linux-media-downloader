# Linux Media Downloader — Technical Documentation

Complete developer and user reference for the application as it currently stands.
For a quick overview and install/run steps, see [README.md](README.md).

---

## Table of Contents

1. [What It Is](#1-what-it-is)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Entry Points](#4-entry-points)
5. [Runtime State](#5-runtime-state)
6. [HTTP Reference](#6-http-reference)
7. [Feature Guide](#7-feature-guide)
8. [Configuration](#8-configuration)
9. [Data & Persistence](#9-data--persistence)
10. [Development & Testing](#10-development--testing)
11. [Packaging](#11-packaging)
12. [Security Notes](#12-security-notes)
13. [Known Limitations & Roadmap](#13-known-limitations--roadmap)
14. [Change History](#14-change-history)

---

## 1. What It Is

Linux Media Downloader is a localhost desktop application for archiving YouTube media
(audio or video, single tracks or whole playlists) for personal, non-commercial use. A
small Flask backend serves a web UI that runs either in a native PyWebView window or an
ordinary browser. All downloading is delegated to [`yt-dlp`](https://github.com/yt-dlp/yt-dlp);
audio extraction and muxing use `ffmpeg`.

| Property | Value |
|----------|-------|
| Language | Python 3.8+ |
| Web framework | Flask (blueprints) |
| Native shell | PyWebView |
| Download engine | yt-dlp |
| Media processing | ffmpeg / ffprobe |
| Frontend | Server-rendered Jinja2 + Bootstrap 5 + jQuery, inline page scripts |
| Persistence | JSON files under `data/` |
| Network exposure | localhost only (`127.0.0.1`) |

---

## 2. Architecture

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| Native shell | PyWebView (`app.py`) | Hosts the UI in a desktop window |
| Browser fallback | Flask dev server (`browser_app.py`) | Same UI at `http://127.0.0.1:5000` |
| Web server | Flask blueprints (`ui_routes`, `api_routes`) | Serves pages and a JSON API |
| Download worker | `modules/download/media.py` | Runs yt-dlp on a background thread |
| Shared state | `modules/config/settings.py` | Config + in-memory singletons + persistence |
| File tooling | `modules/utils/file_utils.py`, `modules/playlists.py` | Sanitization, folder ops, playlist management |

### Request / download flow

```
Browser / WebView  ──HTTP──▶  Flask (api.py, ui.py)
                                  │  POST /api/download
                                  ▼
                      start_download_thread()  ──▶  worker thread (media.py)
                                  │                       │
                                  ▼                       ▼
                          current_download  ◀────  yt-dlp + progress_hook
                          (dict, polled via                │
                           /api/download-status)           ▼
                                                     files on disk + history JSON
```

The UI starts a download, then **polls** `/api/download-status` every 500 ms and repaints
the progress circle, the current-file bar, and the per-track table from the returned dict.

---

## 3. Project Structure

```
linux-media-downloader/
├── app.py                     # Entry point: native PyWebView window
├── browser_app.py             # Entry point: browser fallback (Flask :5000)
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Dev/test dependencies (pytest, pyflakes)
├── modules/
│   ├── config/settings.py     # Config, shared state, history + links persistence, cancel helpers
│   ├── download/media.py       # yt-dlp orchestration, progress hook, worker thread
│   ├── playlists.py            # Playlist discovery + file operations (rename/clean/delete)
│   ├── routes/api.py           # JSON API blueprint (/api/*)
│   ├── routes/ui.py            # Page-rendering blueprint
│   └── utils/file_utils.py     # Filename sanitization, open-folder
├── templates/                  # base, index, backups (History), playlists, links, about, information
├── static/css, static/js       # Styles + shared JS
├── data/                        # Runtime JSON (git-ignored)
├── tests/test_app.py           # Offline test suite (29 tests)
└── AppDir/                      # AppImage packaging staging tree (mirror of the app)
```

### Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `config/settings.py` | `SECRET_KEY`, default download path, `current_download` dict, `download_history`, `links_history`, cancel flag + accessors, JSON load/save |
| `download/media.py` | `get_video_info`, `download_media`, `DownloadProgress.progress_hook`, `start_download_thread`, filename post-processor |
| `playlists.py` | `list_playlists`, `list_playlist_files`, `rename_playlist`, `apply_operation`, path-safety guard |
| `routes/api.py` | All `/api/*` endpoints |
| `routes/ui.py` | Page routes (`/`, `/backups`, `/playlists`, `/links`, `/about`, `/information`) |
| `utils/file_utils.py` | `sanitize_filename`, `open_folder` |

---

## 4. Entry Points

| Entry point | Command | Server | Needs GUI? | Use case |
|-------------|---------|--------|------------|----------|
| `app.py` | `python3 app.py` | Ephemeral port + PyWebView window | Yes (display + WebKit) | Normal desktop use |
| `browser_app.py` | `python3 browser_app.py` | `127.0.0.1:5000` | No | Servers / headless / debugging |

Both register the same two blueprints, so behaviour is identical apart from the window.

---

## 5. Runtime State

Shared state lives as module-level singletons in `settings.py`. Mutable containers are
imported by reference so cross-module mutation is visible; scalar flags are only accessed
through functions.

| Name | Type | Purpose |
|------|------|---------|
| `current_download` | dict | Live status/progress of the active download (polled by the UI) |
| `download_history` | list | Completed downloads (last 100), persisted to `data/download_history.json` |
| `links_history` | list | Every submitted link (last 500), persisted to `data/links_history.json` |
| `cancel_requested` | bool | Cancellation flag — **only** via `request_cancel()` / `reset_cancel()` / `is_cancel_requested()` |
| `default_download_path` | str | Resolved from XDG → `~/Downloads` → `./downloads` |

> **Convention:** never `from settings import cancel_requested` and reassign it — a scalar
> imported by value does not propagate across modules. Use the accessor functions.

Key fields in `current_download`:

| Field | Meaning |
|-------|---------|
| `status` | `starting` / `downloading` / `processing` / `completed` / `completed_with_errors` / `cancelled` / `error` |
| `progress` | Current file % (byte → estimate → fragment fallback) |
| `downloaded_bytes`, `total_bytes`, `speed`, `eta` | Live transfer stats |
| `duration` | Current track length in seconds (from yt-dlp `info_dict`) |
| `current_file`, `total_files`, `completed_files` | Playlist counters |
| `is_playlist`, `playlist_title` | Playlist context |

---

## 6. HTTP Reference

### Pages

| Path | Template | Description |
|------|----------|-------------|
| `/` | `index.html` | Home — submit a link, pick options, watch progress |
| `/backups` | `backups.html` | **History** of completed downloads |
| `/playlists` | `playlists.html` | Playlists manager |
| `/links` | `links.html` | Links history (submitted URLs) |
| `/information`, `/about` | — | Static info pages |

### JSON API

| Method | Endpoint | Request body | Response |
|--------|----------|--------------|----------|
| `POST` | `/api/check-url` | `{url}` | Playlist/video info (`is_playlist`, `entries`, `title`) |
| `GET`  | `/api/get-default-path` | — | `{path}` |
| `POST` | `/api/download` | `{url, output_dir, download_type, playlist_mode, skip_long}` | `{status:"started"}` |
| `POST` | `/api/cancel-download` | — | `{status:"cancelled"}` |
| `GET`  | `/api/download-status` | — | `current_download` dict |
| `GET`  | `/api/links-history` | — | Links list, newest first |
| `POST` | `/api/clear-links-history` | — | `{status:"cleared"}` |
| `GET`  | `/api/playlists` | — | `[{name, path, file_count, total_size}]` |
| `POST` | `/api/playlist-files` | `{path}` | `{path, files:[{filename, size, duration}]}` |
| `POST` | `/api/rename-playlist` | `{path, new_name}` | `{status, path, name}` |
| `POST` | `/api/playlist-operation` | `{path, operation}` — operation ∈ delete_long, clean, remove_special, replace_spaces, remove_filler, truncate, standard_font, number_prefix, lower_case, upper_case, title_case, camel_case | `{status, renamed \| deleted, can_undo, can_redo}` |
| `POST` | `/api/playlist-undo` | — | Reverse the last operation `{status, changed, can_undo, can_redo}` |
| `POST` | `/api/playlist-redo` | — | Replay the last undone operation |
| `POST` | `/api/open-folder` | `{path}` | `{status}` |

**Download parameters**

| Param | Values | Default |
|-------|--------|---------|
| `download_type` | `audio` (MP3 192 kbps) / `video` (MP4) | `audio` |
| `playlist_mode` | `single` / `playlist` | `single` |
| `skip_long` | `true` / `false` (skip tracks > 6 min) | `false` |

---

## 7. Feature Guide

### 7.1 Downloading

`download_media()` resolves the URL with `get_video_info()`, sets up yt-dlp options per
`download_type`, and downloads on a daemon thread. Audio uses `bestaudio` +
`FFmpegExtractAudio` (MP3); video uses `bestvideo+bestaudio` merged to MP4. Output
filenames are sanitized both by a custom post-processor and a final directory sweep. For
`playlist` mode a `<name>_playlist` folder is created.

### 7.2 Skip long files

When a playlist is detected the Home page shows a **Skip long files (over 6 min)** checkbox.
If enabled, `download_media` installs a yt-dlp `match_filter` that returns a skip message for
any entry whose `duration` exceeds 360 s, so long tracks are never downloaded.

### 7.3 Progress reporting

Per-file progress is computed server-side with graceful fallbacks:

| Priority | Source | Formula |
|----------|--------|---------|
| 1 | `total_bytes` (or `total_bytes_estimate`) | `downloaded / total × 100` |
| 2 | `fragment_index` / `fragment_count` | `index / count × 100` |
| 3 | none available | `0` |

The UI shows the current track's title in the active-sidebar blue with a centered bar below
it (determinate while downloading, animated while processing), and the overall circle folds
in the current file's fraction so it advances smoothly. The download table's first column
reports each track's **Length** (duration).

### 7.4 Cancellation

`POST /api/cancel-download` calls `request_cancel()`. The progress hook checks
`is_cancel_requested()` and raises `yt_dlp.utils.DownloadCancelled`, which `download_media`
catches and reports as `cancelled` (skipping the alternative-method retry).

### 7.5 History & Links

| Feature | Store | Page | Notes |
|---------|-------|------|-------|
| Download History | `download_history` (100) | `/backups` (History) | Completed downloads |
| Links History | `links_history` (500) | `/links` | Every submitted URL, enriched with resolved title + final status; YouTube-style cards with thumbnails, search, open/copy/re-use |

The Links "Re-use" action opens Home with `?url=…` pre-filled.

### 7.6 Playlists manager

**Discovery.** `list_playlists()` scans a set of *download roots* and returns any subfolder
containing **more than one** media file:

| Root source | Rule |
|-------------|------|
| `default_download_path` | Always scanned |
| History entry ending in `_playlist` | Its **parent** is scanned |
| Other history entry | The entry path itself is scanned |
| `./downloads` | Always scanned |

> Parents are only taken for real `*_playlist` folders — otherwise a single-mode playlist
> download would cause the entire home directory to be scanned.

**Detail view.** A sortable table (click headers) with three columns:

| Column | Source |
|--------|--------|
| Length | `ffprobe` duration per file |
| Filename | On-disk name |
| Size | File size |

**Operations** (`POST /api/playlist-operation`):

| `operation` | Effect |
|-------------|--------|
| `delete_long` | Delete files longer than 6 minutes |
| `clean` | Full clean: strip specials, collapse spaces/dashes to underscores |
| `remove_special` | Remove special characters |
| `replace_spaces` | Replace spaces with underscores |
| `remove_filler` | Drop clutter words — music, mix, remaster, live, 4k, hd, official, video, remix, cover, months, years, … — **even when glued together in camelCase** (`SongOfficialVideo` → `Song`) |
| `truncate` | Truncate names to 35 characters |
| `standard_font` | Normalize fancy / accented / full-width characters to standard ASCII |
| `number_prefix` | Add a zero-padded `NN_` prefix (re-numbers) |
| `lower_case` / `upper_case` / `title_case` / `camel_case` | Change filename casing |

All rename operations preserve uniqueness: if two files would collide (e.g. after
truncation), a deterministic **4-character salt** is inserted before the extension rather
than skipping the file. Renaming a playlist (`/api/rename-playlist`) renames the folder on
disk.

**Undo / Redo.** Every operation is reversible. Rename operations record their `(src, dst)`
moves; `delete_long` moves files into a `.trash` subfolder instead of erasing them. The
detail view's **Undo**/**Redo** buttons (`/api/playlist-undo`, `/api/playlist-redo`) reverse
or replay the last operation. The undo/redo state is in memory and resets on restart.

The playlist **list** view numbers each entry with a large `001`, `002`, … sequence badge.

### 7.7 Filename sanitization

`sanitize_filename()` (used on downloads and the `clean` operation):

| Step | Rule |
|------|------|
| 1 | Trim whitespace; preserve extension |
| 2 | Remove all but alphanumerics, spaces, dashes |
| 3 | Spaces & dashes → underscores |
| 4 | Trim leading/trailing underscores |
| 5 | Collapse repeated underscores |

---

## 8. Configuration

| Setting | How | Default |
|---------|-----|---------|
| Flask secret key | `SECRET_KEY` env var | random per run (`os.urandom`) |
| Download folder | UI field / `output_dir` | XDG Downloads → `~/Downloads` → `./downloads` |
| Audio codec/quality | `media.py` | MP3 @ 192 kbps |
| "Long" threshold | `LONG_SECONDS` in `playlists.py` / filter in `media.py` | 360 s (6 min) |
| History cap | `save_download_history` | 100 entries |
| Links cap | `save_links_history` | 500 entries |

---

## 9. Data & Persistence

| File | Contents | Tracked in git? |
|------|----------|-----------------|
| `data/download_history.json` | Completed downloads (≤100) | No (runtime) |
| `data/links_history.json` | Submitted links (≤500) | No (runtime) |
| `downloads/`, `backups/` | Created at startup as fallbacks | No |

Runtime JSON is git-ignored (`**/data/*.json`) and regenerated on demand.

---

## 10. Development & Testing

```bash
pip install -r requirements-dev.txt
pytest -q                 # 29 offline tests, no network
pyflakes modules tests    # lint
```

The suite is fully offline (never performs a real download). Coverage:

| Area | Tests |
|------|-------|
| Filename sanitization | parametrized cases + extension preservation |
| Cancellation | cross-module flag, hook raises, HTTP cancel end-to-end |
| Progress | fragment-count fallback |
| API routes | default path, URL required, status, error paths |
| Links history | add/update, API order, clear, page render |
| Playlists | discovery (multi-file only), rename, **path-traversal rejection**, each rename op, delete-long, no parent-walk, API + page render |

> When changing runtime code, keep the `AppDir/usr/bin/` copy in sync — it is what an
> AppImage build ships.

---

## 11. Packaging

`AppDir/` stages the app for a portable **AppImage** (Debian/Ubuntu/Mint, etc.). It mirrors
the top-level sources under `AppDir/usr/bin/`. Recommended install location for a built
AppImage: `~/Applications`.

---

## 12. Security Notes

- **Localhost only.** Flask binds to `127.0.0.1`; nothing is exposed on the network.
- **Path-traversal guard.** Every destructive playlist operation (rename, delete, bulk
  rename) is gated by `_is_safe_path()`, which requires the target to resolve inside a known
  download root. Requests targeting arbitrary paths (e.g. `/etc`) are refused.
- **Secret key.** Not hardcoded — taken from `SECRET_KEY` or a per-run random value.
- **Destructive operations are irreversible.** `delete_long` permanently removes files; the
  UI confirms before running it.

---

## 13. Known Limitations & Roadmap

| Item | Status |
|------|--------|
| YouTube bot-check on some hosts/IPs | External; may require cookies (`--cookies-from-browser`) |
| `RD…` "Mix"/radio playlists are huge/dynamic | Expected yt-dlp behaviour |
| Per-file `ffprobe` on playlist open | Slow for very large folders (could be cached) |
| cwd-relative data/download paths | Anchor to a fixed app-data dir (planned) |
| Native window (`app.py`) needs a display | Use `browser_app.py` when headless |
| Integration test with a real download + CI | Planned |

---

## 14. Change History

See [`changelog.md`](changelog.md) for the append-only, dated log, and
`.claude/memory/changes/` for detailed per-change manifests (root cause, files, impact).
