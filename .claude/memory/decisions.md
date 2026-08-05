# Decisions

### 2026-08-05: MensuraMedia is the single canonical repository
- Reason: The project existed as two divergent GitHub repos with unrelated histories —
  `mikesdatawork/linux-media-downloader` (had a logging framework + the launch fix) and
  `MensuraMedia/linux-media-downloader` (feature-complete superset: job queue, playlists,
  chapters, dedupe, settings; the repo actually installed/published). Maintaining both
  caused drift and confusion about which version users ran.
- Decision: Consolidate onto **MensuraMedia** as canonical (it is the superset, is public,
  and is the tree the installer/menu launches). Ported the only unique assets from the
  mikesdatawork tree — the centralized logging framework and the launch-failure postmortem.
  Repointed the local dev checkout (`~/projects/linux_media_downloader`) to this remote.
  The mikesdatawork repo is read-only from here (pull-only access) and must be retired
  manually by its owner (archive + redirect notice).
- Impact: `modules/config/logging_config.py` (new), logging wiring across entrypoints/modules,
  `docs/troubleshooting/`, `install.sh`, `app.py`. Backups of the old tree: a full git
  bundle + an on-disk archive copy alongside the project.

### 2026-08-05: venv must use --system-site-packages for the PyWebView GUI backend
- Reason: The installed app showed a menu icon but no window. The installer built its venv
  without `--system-site-packages`; PyWebView's GTK backend needs system `PyGObject` (`gi`)
  + WebKit2GTK (apt-only, not pip-installable in an isolated venv), so `webview.start()`
  raised `WebViewException` and the process died in <1s. `Terminal=false` hid the traceback.
- Decision: Create the venv with `--system-site-packages` and verify the backend at install
  time; keep `WEBKIT_DISABLE_DMABUF_RENDERER=1` in `app.py` as defense-in-depth. venv and
  system Python are the same build, so exposing system packages is ABI-safe.
- Impact: `install.sh`, `app.py`. Full postmortem in `docs/troubleshooting/`.

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
