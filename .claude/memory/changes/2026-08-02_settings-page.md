---
date: 2026-08-02
type: feature
files_changed:
  - modules/config/user_settings.py (new)
  - modules/playlists.py, modules/download/dedupe.py
  - modules/routes/api.py, modules/routes/ui.py
  - templates/base.html, settings.html (new), faq.html, playlists.html, file-manager.html
  - tests/test_app.py
---
## Change: Settings page (user-editable text controls) + FAQ text-ops docs

- `modules/config/user_settings.py`: persisted `data/app_settings.json` (git-ignored) with
  `filler_words` (defaults = DEFAULT_FILLER_WORDS, moved here from playlists) and
  `char_replacements` [{from,to}]. `get_filler_words()` / `get_char_replacements()`.
- playlists `_is_filler_word` now reads `user_settings.get_filler_words()`; dedupe `_tokens`
  too — so custom filler words affect both text ops AND duplicate matching. New op
  `apply_replacements` (`_apply_replacements`) applies the user's char replacements.
- API: GET/POST `/api/settings`, POST `/api/settings/reset`.
- UI: `/settings` page + sidebar button (above FAQ) — edit filler words (textarea) and
  add/remove find→replace rows. "Apply replacements" button added to Playlists (Transform)
  and File Manager op bars.
- FAQ: full text-operation table with descriptions + Pending/Settings pages documented.

### Verification
- 79/79 pytest (settings defaults/save, custom filler affects remove_filler, apply_replacements,
  settings API roundtrip, /settings renders). Live: set filler 'zeta' + '&'→'and'; a real
  playlist folder had 'zeta' stripped and '&' replaced. Path-safety guard still blocks folders
  outside download roots.
