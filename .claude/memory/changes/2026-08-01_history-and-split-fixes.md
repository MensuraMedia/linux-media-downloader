---
date: 2026-08-01
type: bugfix
files_changed:
  - templates/backups.html
  - modules/routes/ui.py
  - modules/routes/api.py
  - modules/config/settings.py
  - modules/download/media.py
  - modules/download/chapters.py
  - tests/test_app.py
---
## Change: History page fixes + Split status/guard fixes

### History (/backups)
- **Folder links dead:** the folder icon called `onclick="openDirectory(...)"` but no such
  function existed (JS defined a `.open-folder` handler instead). Rewired the icon to
  `class="open-folder" data-path=...` with delegated click → `/api/open-folder`; shows the
  path + clearer failure alert.
- **Not updating / order:** route now reads `settings.download_history` fresh (was a stale
  by-value import) and sorts **descending by download time**. Added `timestamp` to history
  entries (media.py + api cancel path). `save/load_download_history` now mutate in place
  (`list[:]=`) so no module holds a stale list. Legacy entries (no timestamp) fall back to
  reverse-append order via a stable index tiebreaker.

### Split (Multi-Chapter)
- **Missed on playlist/radio URLs:** split was gated on `playlist_mode != 'playlist'`, so a
  `list=RD...` radio URL downloaded in playlist mode skipped splitting. "Split Multi-Chapter
  video" is a single-video op → now forces `playlist_mode='single'` so the primary video is
  downloaded and split. (Verified: the reported video has 37 embedded chapters + a
  `0:00:00 | Title` description tracklist; both parse to 37 segments.)
- **Premature "Backups Completed" / no progress bar:** the download's finished hook set
  status 'completed', so the UI declared done and stopped polling while ffmpeg was still
  cutting. Now `DownloadProgress(split_pending=True)` defers 'completed' (sets 'processing'),
  the alternative-method guard uses a new `done` flag instead of the status string, and
  `_split_into_tracks` reports per-track progress (status 'processing', completed/total, current
  track) then sets 'completed' only when the split finishes. `split_file` gained an
  `on_progress` callback. History records the real download outcome, not the deferred state.

### Verification
- 65/65 pytest (added deferred-completion, on_progress, plus prior). Live: split status flow
  on real audio ended 'completed' 3/3 with tracks incl. unlabeled→NN_summary; History renders
  newest-first with working folder links.
