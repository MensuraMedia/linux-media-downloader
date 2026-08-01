---
date: 2026-08-01
type: feature + docs
files_changed:
  - modules/playlists.py
  - tests/test_app.py
  - docs/concept-file-manager.md (new)
  - README.md / DOCUMENTATION.md / changelog.md
---
## Change: 'animated' filler, Title Case fix, File Manager concept doc

- **Filler:** added `animated`, `animation`, `anime` to FILLER_WORDS.
- **Title Case fix:** `_title_case` now capitalizes the first letter of EVERY word,
  including across `_ - .` and digits (`brad_fiedel_the_terminator` →
  `Brad_Fiedel_The_Terminator`). Previously only the very first letter changed because `_`
  is a word char, so `\b\w` didn't fire between words.
- **Concept doc:** `docs/concept-file-manager.md` specifies a future **File Manager** tab —
  dense 3+-column filename grid of app-recorded files only; stats (total / duplicate names /
  same-size); global text ops (reusing playlists helpers + undo); inline mini-player with
  keyboard control (→ +5s, ← −2s, ↑/↓ volume, Delete = stop + delete → muted state); per-file
  trash icon. Linked from DOCUMENTATION roadmap. Not implemented yet.

### Verification
- 52/52 pytest passing (added title-case-all-words, remove_filler animated; updated the
  media-terms test since 'anime' is now filler). pyflakes/py_compile clean.
