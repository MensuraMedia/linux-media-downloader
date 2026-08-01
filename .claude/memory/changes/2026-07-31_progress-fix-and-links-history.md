---
date: 2026-07-31
type: bugfix + feature
files_changed:
  - modules/config/settings.py
  - modules/download/media.py
  - modules/routes/api.py
  - modules/routes/ui.py
  - templates/base.html
  - templates/index.html
  - templates/links.html
  - tests/test_app.py
  - .gitignore
  - README.md / changelog.md
---
## Change: Accurate per-file progress + Links History feature

### Progress fix (root cause)
The per-file % was stuck at 0. The backend already provided a correct `progress`
(with a `total_bytes_estimate` fallback), but the frontend `updateProgressUI` **recomputed**
`downloaded_bytes / total_bytes` and showed 0 whenever `total_bytes` was momentarily
absent (common for DASH audio). Fixes:
- Frontend now uses the server-computed `data.progress`.
- Backend hook adds a **fragment-count fallback** (`fragment_index/fragment_count`) when no
  byte total is available, and exposes the fragment fields.
- New live readout `#current-file-detail`: "file — X/Y MB (NN%) at Z MB/s".
- Overall playlist circle folds in the current file's fraction (smooth, not step-per-file).
- Status polling 1000ms → 500ms for finer updates.

### Links History feature
- `settings.py`: persisted `links_history` (data/links_history.json, 500 max) with
  `add_link_history` / `update_last_link_history` / save / load.
- `api.py`: records each submitted link on `/api/download`; new `GET /api/links-history`
  (newest first) and `POST /api/clear-links-history`.
- `media.py`: enriches the latest link entry with the resolved title, and its final status.
- `ui.py`: new `/links` route; `base.html`: new **Links** sidebar tab.
- `templates/links.html`: scrollable YouTube-style cards (thumbnail from video id, title,
  Audio/Video + Single/Playlist + status pills, timestamp, Open/Copy/Re-use, search, clear).
- `index.html`: reads `?url=` to pre-fill the box (the "Re-use" action).

### Housekeeping
- Stopped tracking runtime `data/*.json` (regenerated at runtime); tests redirect history
  writes to tmp so they never touch repo data.

### Verification
- 19/19 pytest passing (added fragment-fallback, links add/update, links API newest-first +
  clear, `/links` renders). pyflakes clean. py_compile clean. Not yet visually confirmed in
  a running server (requires a restart that would interrupt the active download).
