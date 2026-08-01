---
date: 2026-08-01
type: feature + fix
files_changed:
  - templates/index.html
  - modules/routes/api.py
  - tests/test_app.py
---
## Change: Download state retention (reconnect) + concurrency guard

### Problem
Download state lives server-side in `current_download`, but the Home page only showed
progress if it had started the download in that page session. Navigating away and back lost
the view while the background thread kept running; starting another download then collided
with the running thread — the user had to restart the app for a clean session.

### Fix
- **Reconnect:** refactored the polling loop into `startStatusPolling()`. Added
  `resumeActiveDownload()`, called on Home load: it queries `/api/download-status` and, if a
  download is active (starting/downloading/processing), rebuilds the progress table (from
  `total_files`), shows the circle + current-file readout + Cancel, locks the form, shows a
  "Reconnected…" note, and resumes polling. Polling now also handles `cancelled`.
- **Concurrency guard:** `/api/download` returns `{error: 'A download is already in
  progress'}` when `current_download.status` is active, so no second thread is spawned.

### Verification
- 57/57 pytest passing (added test_download_rejected_when_already_active). pyflakes/compile clean.
- **Live:** with the user's real "80s playlist" download active (8/30), loading Home fresh in
  a headless browser reconnected — showed the 27% circle, current file, 30-row table, Cancel,
  and "Reconnected to a download already in progress…"; a second /api/download was rejected.
