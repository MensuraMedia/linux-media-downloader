---
date: 2026-08-01
type: feature + fix
files_changed:
  - templates/index.html
  - static/css/style.css
  - modules/playlists.py
  - tests/test_app.py
---
## Change: Unified download scope, grayed-until-detected options, more filler words

### Unified scope (fixes duplicate Full Playlist + All)
Home had two separate radio groups (playlist-mode single/full, and amount all/10/20/30),
which were not mutually exclusive — Single Video could appear selected alongside an amount.
Merged into ONE group `name="playlist-scope"`: Single Video / All (N videos) / First 10 /
First 20 / First 30. The old "Full Playlist" radio is removed ("All" covers it). JS
`getScope()` maps the selection → `playlist_mode` + `limit`; the backend API is unchanged.

### Grayed-until-detected
Playlist-only options (Amount radios + Skip long) are always visible but start `disabled`
with an `.opts-disabled` (opacity .4) style. `setPlaylistOptions(enabled)` toggles them;
they enable only when `/api/check-url` reports a playlist, and re-gray after a download
(via a `playlistDetected` flag threaded through `resetForm`).

### More filler words
Added to FILLER_WORDS: ost, soundtrack, score, theme, ova, ona, amv, pv, op, ed,
instrumental, inst, nightcore, sped, slowed, reverb, 8d, bonus, deluxe, remux, bluray, bd,
dvd, hdr, 1080p/720p/480p/2160p. Caught even inside camelCase (`AnimeAMVScore` → `Anime`).

### Verification
- 44/44 pytest passing (added media-terms filler test). pyflakes/py_compile clean.
- Live: single mutually-exclusive group, 5 options disabled by default, gray styling served.
