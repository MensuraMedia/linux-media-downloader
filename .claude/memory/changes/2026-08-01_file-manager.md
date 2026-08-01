---
date: 2026-08-01
type: feature
files_changed:
  - modules/playlists.py
  - modules/routes/api.py
  - modules/routes/ui.py
  - templates/base.html
  - templates/file-manager.html (new)
  - tests/test_app.py
  - docs/concept-file-manager.md (implemented)
---
## Change: File Manager (implemented from concept)

- **Scope:** `list_app_media()` returns media inside the app's playlist folders only
  (app-recorded), narrower than the Player's `list_all_media()`.
- **Stats:** `file_stats()` → total, duplicate_names (same basename), same_size groups;
  `/api/file-stats`. Stat tiles filter the grid.
- **Global text ops:** refactored `_rename_within` / `delete_long_files` /
  `abbreviate_duplicate_strings` / `apply_operation` to take `record=` and return `moves`.
  `global_operation(op)` applies an op across every app folder and records all moves as ONE
  undo entry. `/api/global-operation`; shares the existing undo/redo stack.
- **Page:** `/file-manager` + sidebar tab. Dense 3+-col grid (~1px cells) of
  `▶ play · filename · 🗑 trash`. Inline shared `<audio>` with keyboard transport
  (→ +5s, ← −2s, ↑/↓ volume, Delete = stop & delete → muted/strikethrough cell). Search.
- **Note:** 'instrumental' filler was already present; confirmed.

### Verification
- 56/56 pytest passing (list_app_media scoping, file_stats dup count, global_operation
  across folders + single undo, /file-manager render). pyflakes/py_compile clean.
- Live: /api/app-media 552 files / 11 folders (excludes loose non-app root files);
  /api/file-stats {total 552, dup 0, same_size 53}; screenshot confirms grid + stats + ops.
- global-operation NOT run on real data (destructive); covered by tests only.
