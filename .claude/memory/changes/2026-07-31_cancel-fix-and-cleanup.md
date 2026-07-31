---
date: 2026-07-31
type: bugfix + refactor + tests
files_changed:
  - modules/config/settings.py
  - modules/download/media.py
  - modules/routes/api.py
  - app.py
  - browser_app.py
  - tests/test_app.py
  - requirements-dev.txt
  - AppDir/usr/bin/** (synced copies)
---
## Change: Fix cross-module cancellation, dead code, and cleanup; add tests

### Root causes fixed
1. **Cancellation was a no-op across modules.** `cancel_requested` (a bool) was imported
   *by value* into `media.py` and `api.py`. `api.py` rebinding its own copy never reached
   the download worker in `media.py`. Fixed by keeping the flag in `settings.py` and
   exposing `request_cancel()` / `reset_cancel()` / `is_cancel_requested()`; all modules
   call these (single source of truth).
2. **Progress hook returned instead of aborting.** Returning from a yt-dlp progress hook
   does not stop the download. Now raises `yt_dlp.utils.DownloadCancelled`, caught in
   `download_media` and reported as `cancelled` (and the alternative-method retry is
   skipped, so a cancelled job is not silently re-downloaded).
3. **Unreachable dead code** in `/api/cancel-download`: the history-append block sat after
   `return`, so cancelled downloads were never recorded. Reordered to run before the return.

### Cleanup / hardening
- `SECRET_KEY` now `os.environ.get('SECRET_KEY') or os.urandom(24).hex()` (was hardcoded).
- Removed unused imports (`os` in app.py; `re`/`time` in media.py; `threading` in
  browser_app.py) and unused `error_code` assignments.
- Removed stale `*.py.error` backup files (root + AppDir).
- Synced corrected sources into the `AppDir/usr/bin/` packaging staging tree.

### Tests (new)
- `tests/test_app.py` — 15 offline tests: filename sanitization, cancel wiring (including
  an end-to-end HTTP cancel via Flask test client), progress-hook completion/abort, secret
  key hygiene, and `/api/*` error/happy paths.

### Verification
- `pytest`: 15 passed. `pyflakes`: clean across runtime modules + tests.
- `py_compile`: passes for root and AppDir copies.

### Impact
- Cancellation now actually works. No public API/route signatures changed. No functional
  change for normal (non-cancelled) downloads.
