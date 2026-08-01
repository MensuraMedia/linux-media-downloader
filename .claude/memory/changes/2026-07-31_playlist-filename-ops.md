---
date: 2026-07-31
type: feature
files_changed:
  - modules/playlists.py
  - templates/playlists.html
  - tests/test_app.py
  - README.md / DOCUMENTATION.md / changelog.md
---
## Change: More playlist filename operations + collision salt + UI gap

### New bulk operations (modules/playlists.py `apply_operation`)
- `remove_filler` — drop clutter words (music, mix, remaster(ed), live, 4k/8k, hd/uhd,
  official, remix, cover, video, audio, months, 19xx/20xx years, …) and bracket noise.
- `truncate` — cut names to 35 characters (`TRUNCATE_LEN`).
- `standard_font` — normalize fancy/accented/full-width characters to ASCII (NFKD).
- `lower_case` / `upper_case` / `title_case` / `camel_case` — casing transforms.

### Collision handling
`_rename_within` no longer skips on collision; `_unique_name` inserts a deterministic
4-character md5 salt before the extension (important for truncate, where many names
collapse to the same 35-char prefix). Empty mapper output falls back to the original base.

### UI (templates/playlists.html)
- Operations grouped under **Cleanup** and **Case** labels.
- Added a divider (`.pl-divider`) + spacing between the operations and the file table.

### Verification
- 34/34 pytest passing (added truncate, remove_filler, salt-on-collision, standard_font,
  camel_case). pyflakes clean, py_compile clean, AppDir synced, buttons verified live.
