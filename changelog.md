# Changelog

Local, git-independent, append-only change log. ISO 8601 datetimes. Newest at the bottom.

| Date-Time | Change Description |
|-----------|-------------------|
| 2026-07-31T00:00:00 | Onboarded existing project; applied universal standards (agents, permissions, memory, rules) into .claude/ |
| 2026-07-31T00:00:01 | Fixed broken cross-module cancellation: routed cancel flag through settings accessor functions |
| 2026-07-31T00:00:02 | Progress hook now raises yt_dlp DownloadCancelled to actually abort; download_media handles it as 'cancelled' |
| 2026-07-31T00:00:03 | Repaired unreachable dead code in /api/cancel-download (history append was after the return) |
| 2026-07-31T00:00:04 | SECRET_KEY now env-overridable with random fallback instead of hardcoded value |
| 2026-07-31T00:00:05 | Removed unused imports (os in app.py, re/time in media.py, threading in browser_app.py) |
| 2026-07-31T00:00:06 | Removed stale .py.error backup files (root + AppDir); synced corrected sources into AppDir/usr/bin |
| 2026-07-31T00:00:07 | Added CLAUDE.md, changelog.md, .claudeignore, and .claude/memory structure |
| 2026-07-31T00:00:08 | Repointed git origin to MensuraMedia/linux-media-downloader (future work); kept mikesdatawork as upstream |
| 2026-07-31T00:00:09 | Added tests/test_app.py (15 offline unit + route tests); added requirements-dev.txt (pytest, pyflakes) |
| 2026-07-31T00:00:10 | Removed unused error_code assignments in media.py; pyflakes clean across runtime modules + tests |
| 2026-07-31T00:00:11 | Rewrote README into a robust, current form (architecture, structure, API, config, dev/test, packaging); synced AppDir copy |
| 2026-07-31T00:00:12 | Fixed per-file progress: frontend now uses server-computed progress; added byte-estimate + fragment fallbacks |
| 2026-07-31T00:00:13 | Added live current-file readout (size/%/speed), smooth playlist circle, 500ms polling |
| 2026-07-31T00:00:14 | Added Links History feature: /links page, /api/links-history, persisted links_history, YouTube-style cards |
| 2026-07-31T00:00:15 | Stopped tracking runtime data/*.json (history regenerated at runtime); added tests (19 total) |
| 2026-07-31T00:00:16 | UI: current-file bar moved below the blue track title (centered, fixed); removed the 'processing' label |
| 2026-07-31T00:00:17 | UI: replaced the redundant table 'Progress' column with a 'Length' (track duration) column; backend now exposes per-track duration |
| 2026-07-31T00:00:18 | Feature: 'Skip long files' filter for playlists (yt-dlp match_filter skips tracks > 6 min) |
| 2026-07-31T00:00:19 | Sidebar: renamed 'Backups' to 'History'; added 'Playlists' tab |
| 2026-07-31T00:00:20 | Feature: Playlists manager (list, rename folder, sortable Length/Filename/Size table, bulk ops) with path-safety guards; 28 tests |
| 2026-07-31T00:00:21 | Fix: playlist scan no longer walks into the home dir (only *_playlist folders contribute a parent root); regression test (29 total) |
| 2026-07-31T00:00:22 | Docs: added DOCUMENTATION.md (full technical reference with tables); linked from README |
| 2026-07-31T00:00:23 | Playlists: added file ops — remove filler words, truncate to 35, standard-font (ASCII), lower/UPPER/Title/Camel case |
| 2026-07-31T00:00:24 | Playlists: rename collisions now get a 4-char salt (no longer skipped); grouped ops UI with a gap before the table; 34 tests |
| 2026-08-01T09:00:00 | Playlists: filler-word removal now detects words inside camelCase (e.g. SongOfficialVideo -> Song) |
| 2026-08-01T09:05:00 | Playlists: added Undo/Redo (rename ops reversible; delete_long moves to .trash); state via /api/playlist-undo,-redo |
| 2026-08-01T09:10:00 | Playlists: large sequence badge (001, 002, …) on each list entry; 36 tests, live end-to-end verified |
