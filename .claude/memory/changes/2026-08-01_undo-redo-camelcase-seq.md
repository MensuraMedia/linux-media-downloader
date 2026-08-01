---
date: 2026-08-01
type: feature
files_changed:
  - modules/playlists.py
  - modules/routes/api.py
  - templates/playlists.html
  - tests/test_app.py
  - README.md / DOCUMENTATION.md / changelog.md
---
## Change: camelCase filler detection, Undo/Redo, sequence badges

### camelCase filler words
`_remove_filler` now camelCase-splits each token (`_split_camel`) so glued filler words
are caught (`SongTitleOfficialVideo` → `SongTitle`). A whole-token check runs first so
units/years like `4K`, `HD`, `2019` are still matched before splitting.

### Undo / Redo
- In-memory `_undo_stack` / `_redo_stack` of `(src, dst)` move lists.
- Rename ops record their moves; `delete_long` now MOVES files to a `.trash` subfolder
  (undoable) instead of `os.remove`. `_media_files` ignores `.trash` (a directory).
- `undo_last()` / `redo_last()` + `/api/playlist-undo`, `/api/playlist-redo`.
- `/api/playlist-files` and every op response return `can_undo` / `can_redo`; the detail
  view enables/disables the Undo/Redo buttons accordingly.

### Sequence badges
The Playlists list numbers each entry with a large `001`, `002`, … badge (frontend index).

### Verification
- 36/36 pytest passing (camelCase filler, undo/redo rename, delete→trash + undo restore).
- **Live end-to-end** on a throwaway `~/Downloads/ZZZ_e2e_test_playlist`: remove_filler
  turned `MySongOfficialVideo.mp3` → `MySong.mp3`, then undo restored it. pyflakes clean.
