---
date: 2026-08-01
type: feature + fix
files_changed:
  - modules/playlists.py
  - modules/routes/api.py
  - modules/routes/ui.py
  - templates/base.html
  - templates/player.html (new)
  - templates/index.html
  - tests/test_app.py
---
## Change: Player / curation page + First-N table fix

### Player (new)
- `/player` page + **Player** sidebar tab. Lists every downloaded media file
  (`list_all_media` → `/api/all-media`), grouped by folder, searchable.
- Playback via native `<audio>`/`<video controls>` streamed from `/api/media?path=…`
  using `send_file(conditional=True)` (HTTP range → seeking/fast-forward works). Plus
  skip ±10s, prev/next, auto-next.
- Curation: `delete_media_file` (→ `.trash`, `/api/delete-media`) and `add_to_folder`
  (copies into a named folder under the download root, `/api/add-to-folder`) so a user can
  build a curated playlist while listening. All media endpoints guard paths via
  `is_safe_path`.

### Fix: First-N progress table
The Home progress table built a row per `data.entries` (whole playlist) even for
"First 10/20/30". Now capped to `min(entries, getScope().limit)`. The backend already
limited the actual download (`playlistend` + `total_files` cap), so only the top-N is queued.

### Verification
- 50/50 pytest passing (list_all_media, delete→trash, add_to_folder copy, path-reject,
  /player render, /api/media 404 on outside path).
- Live: 536+ files listed, `/api/media` returns 206 Partial Content with Accept-Ranges,
  `/etc/hosts` → 404. Player screenshot confirms transport + curation controls.
