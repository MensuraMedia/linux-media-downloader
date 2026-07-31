# Decisions

### 2026-07-31: Route cancellation through accessor functions in settings.py
- Reason: `cancel_requested` was a module-level bool imported *by value* into both
  `media.py` and `api.py` (`from settings import cancel_requested`). Reassigning it in
  `api.py` rebound only `api.py`'s copy, so the download worker in `media.py` never saw
  the change — cancellation was silently a no-op across module boundaries.
- Decision: Keep the flag private to `settings.py` and expose `request_cancel()`,
  `reset_cancel()`, `is_cancel_requested()`. All modules call these, giving one source of
  truth. Mutable shared state (`current_download` dict, `download_history` list) can still
  be imported by reference because mutation-in-place is visible everywhere.
- Impact: `modules/config/settings.py`, `modules/download/media.py`, `modules/routes/api.py`.

### 2026-07-31: Raise DownloadCancelled from the progress hook instead of returning
- Reason: Returning from a `yt-dlp` progress hook does not abort the download; yt-dlp keeps
  going. The documented way to abort cleanly is to raise `yt_dlp.utils.DownloadCancelled`.
- Decision: The hook raises it on cancel; `download_media` catches it, marks the status
  `cancelled`, and skips the alternative-method retry (which would otherwise re-download).
- Impact: `modules/download/media.py`.

### 2026-07-31: Secret key is environment-overridable with a random fallback
- Reason: `SECRET_KEY` was hardcoded to `'ytmediabackup'`. The app is localhost-only so
  risk is low, but a committed secret is poor hygiene.
- Decision: `SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()`.
- Impact: `modules/config/settings.py`. No functional change (app does not rely on
  persistent server-side sessions).

### 2026-07-31: Keep AppDir/usr/bin/ in sync with top-level sources
- Reason: `AppDir/` is a committed full copy used for AppImage packaging. It held stale,
  buggy code and its own `.error` files, so a built AppImage would ship the old behavior.
- Decision: Sync changed runtime files into `AppDir/usr/bin/` on every runtime change until
  packaging is reworked to copy from source at build time (a future improvement).
- Impact: `AppDir/usr/bin/**`.
