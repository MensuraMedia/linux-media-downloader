---
date: 2026-08-01
type: feature
files_changed:
  - modules/playlists.py
  - modules/download/media.py
  - modules/routes/api.py
  - templates/playlists.html
  - templates/index.html
  - static/css/style.css
  - tests/test_app.py
---
## Change: Fixed sequence badges, top-N download limit, 3-column Home layout

### Fixed sequence badges
Playlist badges are now **fixed to the playlist**, not positional. `data/playlist_seq.json`
stores `{next, orders{realpath: order}}`; each newly-seen playlist gets the next monotonic
`order` (new ones assigned oldest→newest by mtime, so newest gets the highest). The badge is
`order % 1000` → counts 000..999 and wraps. The list is sorted by `order` descending
(latest-added on top). Order migrates on rename (alongside color). Verified live: 001..007.

### Top-N download limit
`/api/download` accepts `limit`; `download_media` sets yt-dlp `playlistend` and caps
`total_files`. Live-verified: a Top-10 request capped `total_files` to 10.

### Home layout
Options reorganized into three minimal columns — **Format**, **Playlist**, **Amount**.
The amount is now **radio** controls (All / First 10 / First 20 / First 30) that appear once
a playlist is detected, instead of a dropdown.

### Verification
- 43/43 pytest passing (fixed/descending sequence, 999→000 wrap, plus prior suites).
- Live: sequence badges, Top-10 cap, 3-column radio layout all confirmed on the running app.
