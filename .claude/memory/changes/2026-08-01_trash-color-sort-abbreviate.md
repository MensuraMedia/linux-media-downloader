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
## Change: Empty-trash, newest-first sort, per-playlist colors, abbreviate-dupes, subtle hover

- **Empty trash** — `empty_trash(path)` / `/api/playlist-empty-trash` purges a playlist's
  `.trash` (permanent). `/api/playlist-files` now returns `trash_count`; the button shows
  the count and disables when empty.
- **Newest-first sort** — `list_playlists()` sorts by folder mtime descending, so the
  `001` badge lands on the most recent playlist.
- **Per-playlist badge colors** — clicking a sequence badge opens a colour picker;
  `set_playlist_color` persists to `data/playlist_colors.json` (keyed by realpath, migrated
  on rename). `list_playlists` returns each `color`; hex validated server-side.
- **Abbreviate duplicates** — `abbreviate_duplicate_strings` shortens tokens recurring in
  2+ files (len > 4) to their first 4 chars; unique per-track parts kept. Verified live:
  `Predator_Soundtrack_Track0N` → `Pred_Soun_Track0N`.
- **Subtle hover** — all Playlists-page buttons hover to a muted `#555` (like the Back
  button) instead of each outline colour's vivid fill.

### Verification
- 41/41 pytest passing (abbreviate, color set/list/invalid-default, newest-first sort,
  empty-trash). pyflakes clean, py_compile clean.
- Live end-to-end: abbreviate + colour set + sort order confirmed via the running server.
