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
